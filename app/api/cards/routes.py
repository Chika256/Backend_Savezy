"""Cards blueprint providing CRUD operations for payment cards."""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import APIKey, Card, CardType
from app.utils.jwt_helper import token_required

cards_bp = Blueprint("cards", __name__, url_prefix="/api/cards")

ALLOWED_CARD_TYPES = {card_type.value for card_type in CardType}


def _json_response(message, data=None, status=200):
    """Return a standardized JSON response."""
    payload = {"message": message, "data": data or {}}
    return jsonify(payload), status


def _extract_user_id(user_payload):
    """Extract a user id from JWT or API key payloads."""
    if isinstance(user_payload, APIKey):
        return user_payload.user_id
    if not isinstance(user_payload, dict):
        return None
    try:
        return int(user_payload.get("user_id"))
    except (TypeError, ValueError):
        return None


def _parse_decimal(value, field_name, errors):
    """Convert incoming numeric values to Decimal."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        errors.append(f"{field_name} must be a numeric value.")
        return None


def _validate_card_payload(payload, *, partial=False):
    """Validate request payload, returning (normalized_data, errors)."""
    if payload is None:
        return {}, ["Request body is required."]

    errors = []
    normalized = {}

    name = payload.get("name")
    if not partial or "name" in payload:
        if not name or not isinstance(name, str):
            errors.append("name is required and must be a string.")
        else:
            normalized["name"] = name.strip()

    card_type = payload.get("type")
    if not partial or "type" in payload:
        if not isinstance(card_type, str):
            card_type = None
        else:
            card_type = card_type.lower()
        if not card_type or card_type not in ALLOWED_CARD_TYPES:
            errors.append("type must be one of: credit, debit, prepaid.")
        else:
            normalized["type"] = card_type

    if "apple_slug" in payload:
        slug = payload.get("apple_slug")
        if slug is not None and not isinstance(slug, str):
            errors.append("apple_slug must be a string.")
        else:
            normalized["apple_slug"] = slug.strip() if isinstance(slug, str) else None

    if "brand" in payload:
        brand = payload.get("brand")
        if brand is not None and not isinstance(brand, str):
            errors.append("brand must be a string.")
        else:
            normalized["brand"] = brand.strip() if isinstance(brand, str) else None

    if "last_four" in payload:
        last_four = payload.get("last_four")
        if last_four is not None:
            if not isinstance(last_four, str):
                errors.append("last_four must be a string.")
            else:
                digits = last_four.strip()
                if len(digits) != 4 or not digits.isdigit():
                    errors.append("last_four must be a four digit string.")
                else:
                    normalized["last_four"] = digits

    # Numeric fields
    if "limit" in payload:
        normalized["limit"] = _parse_decimal(payload.get("limit"), "limit", errors)
    if "total_balance" in payload:
        normalized["total_balance"] = _parse_decimal(
            payload.get("total_balance"), "total_balance", errors
        )
    if "balance_left" in payload:
        normalized["balance_left"] = _parse_decimal(
            payload.get("balance_left"), "balance_left", errors
        )

    # Validate type-specific requirements.
    effective_type = normalized.get("type", card_type)
    if not partial and effective_type is None:
        # if earlier validation failed for empty type.
        effective_type = None

    if effective_type == "credit":
        limit_value = normalized.get("limit")
        if limit_value is None:
            errors.append("limit is required for credit cards.")
    elif effective_type == "prepaid":
        total_balance = normalized.get("total_balance")
        balance_left = normalized.get("balance_left")
        if total_balance is None:
            errors.append("total_balance is required for prepaid cards.")
        if balance_left is None:
            errors.append("balance_left is required for prepaid cards.")
        if (
            total_balance is not None
            and balance_left is not None
            and balance_left > total_balance
        ):
            errors.append("balance_left cannot exceed total_balance.")
    elif effective_type == "debit":
        # No extra fields required.
        pass

    return normalized, errors


def _serialize_card(card, *, include_brand=True):
    """Serialize a card ORM instance."""
    serialized = card.to_dict()
    if not include_brand:
        serialized.pop("brand", None)
    return serialized


@cards_bp.route("", methods=["POST"])
@token_required
def create_card(user_payload):
    """Create a new card for the authenticated user."""
    payload = request.get_json(silent=True)
    data, errors = _validate_card_payload(payload)
    if errors:
        return _json_response("Validation failed.", {"errors": errors}, status=400)

    user_id = _extract_user_id(user_payload)
    if user_id is None:
        return _json_response("Authentication required.", status=401)

    card = Card(
        user_id=user_id,
        name=data.get("name"),
        apple_slug=data.get("apple_slug"),
        type=CardType(data["type"]),
        credit_limit=data.get("limit"),
        total_balance=data.get("total_balance"),
        balance_left=data.get("balance_left"),
        brand=data.get("brand"),
        last_four=data.get("last_four"),
    )

    try:
        db.session.add(card)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return _json_response("Failed to create card due to a server error.", status=500)

    return _json_response(
        "Card created successfully.", {"card": _serialize_card(card)}, status=201
    )


@cards_bp.route("", methods=["GET"])
@token_required
def list_cards(user_payload):
    """Return paginated cards for the authenticated user."""
    user_id = _extract_user_id(user_payload)
    if user_id is None:
        return _json_response("Authentication required.", status=401)

    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("limit", default=10, type=int)
    page = max(page, 1)
    per_page = max(1, min(per_page, 100))

    type_filter = request.args.get("type")
    if type_filter:
        type_filter = type_filter.lower()
        if type_filter not in ALLOWED_CARD_TYPES:
            return _json_response(
                "Validation failed.",
                {"errors": ["type filter must be one of: credit, debit, prepaid."]},
                status=400,
            )

    sort = request.args.get("sort", default="created").lower()
    order = request.args.get("order", default="desc").lower()
    sortable_fields = {
        "created": Card.id,
        "name": Card.name,
        "type": Card.type,
        "limit": Card.credit_limit,
        "total_balance": Card.total_balance,
        "balance_left": Card.balance_left,
    }
    sort_column = sortable_fields.get(sort, Card.id)
    sort_order = sort_column.desc() if order == "desc" else sort_column.asc()

    query = Card.query.filter_by(user_id=user_id)
    if type_filter:
        query = query.filter(Card.type == CardType(type_filter))

    pagination = query.order_by(sort_order).paginate(
        page=page, per_page=per_page, error_out=False
    )

    data = {
        "items": [
            _serialize_card(card, include_brand=False) for card in pagination.items
        ],
        "pagination": {
            "page": pagination.page,
            "limit": pagination.per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        },
        "filters": {"type": type_filter, "sort": sort, "order": order},
    }
    return _json_response("Cards retrieved successfully.", data)


@cards_bp.route("/<int:card_id>", methods=["GET"])
@token_required
def get_card(user_payload, card_id):
    """Return a single card owned by the authenticated user."""
    user_id = _extract_user_id(user_payload)
    if user_id is None:
        return _json_response("Authentication required.", status=401)

    card = Card.query.filter_by(id=card_id, user_id=user_id).first()
    if not card:
        return _json_response("Card not found.", status=404)

    return _json_response("Card retrieved successfully.", {"card": _serialize_card(card)})


@cards_bp.route("/<int:card_id>", methods=["PUT", "PATCH"])
@token_required
def update_card(user_payload, card_id):
    """Update a card for the authenticated user."""
    user_id = _extract_user_id(user_payload)
    if user_id is None:
        return _json_response("Authentication required.", status=401)

    card = Card.query.filter_by(id=card_id, user_id=user_id).first()
    if not card:
        return _json_response("Card not found.", status=404)

    payload = request.get_json(silent=True)
    data, errors = _validate_card_payload(payload, partial=True)
    if errors:
        return _json_response("Validation failed.", {"errors": errors}, status=400)

    if "name" in data:
        card.name = data["name"]
    if "apple_slug" in data:
        card.apple_slug = data["apple_slug"]
    if "brand" in data:
        card.brand = data["brand"]
    if "last_four" in data:
        card.last_four = data["last_four"]
    if "type" in data:
        card.type = CardType(data["type"])
    if "limit" in data:
        card.credit_limit = data["limit"]
    if "total_balance" in data:
        card.total_balance = data["total_balance"]
    if "balance_left" in data:
        card.balance_left = data["balance_left"]

    # Ensure invariants after partial updates.
    if card.type == CardType.CREDIT:
        if card.credit_limit is None:
            return _json_response(
                "Validation failed.",
                {"errors": ["limit is required for credit cards."]},
                status=400,
            )
        card.total_balance = None
        card.balance_left = None
    elif card.type == CardType.PREPAID:
        if card.total_balance is None or card.balance_left is None:
            return _json_response(
                "Validation failed.",
                {"errors": ["total_balance and balance_left are required for prepaid cards."]},
                status=400,
            )
        if card.balance_left > card.total_balance:
            return _json_response(
                "Validation failed.",
                {"errors": ["balance_left cannot exceed total_balance."]},
                status=400,
            )
        card.credit_limit = None
    else:  # debit
        card.credit_limit = None
        card.total_balance = None
        card.balance_left = None

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return _json_response(
            "Failed to update card due to a server error.", status=500
        )

    return _json_response(
        "Card updated successfully.", {"card": _serialize_card(card)}
    )


@cards_bp.route("/<int:card_id>", methods=["DELETE"])
@token_required
def delete_card(user_payload, card_id):
    """Delete a card owned by the authenticated user."""
    user_id = _extract_user_id(user_payload)
    if user_id is None:
        return _json_response("Authentication required.", status=401)

    card = Card.query.filter_by(id=card_id, user_id=user_id).first()
    if not card:
        return _json_response("Card not found.", status=404)

    if card.expenses.count() > 0:
        return _json_response(
            "Unable to delete card with associated expenses.", status=409
        )

    try:
        db.session.delete(card)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _json_response(
            "Unable to delete card with associated expenses.", status=409
        )
    except SQLAlchemyError:
        db.session.rollback()
        return _json_response(
            "Failed to delete card due to a server error.", status=500
        )

    return _json_response("Card deleted successfully.", {"card_id": card_id})
