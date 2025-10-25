"""Expenses blueprint exposing CRUD endpoints for authenticated users."""

from datetime import datetime
from enum import Enum

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Card, Category, Expense
from app.utils.jwt_helper import token_required
from app.utils.validators import validate_expense

# Dedicated blueprint for expense management.
expenses_bp = Blueprint("expenses", __name__)


def _json_response(message, data=None, status=200):
    """Standard success/error payload."""
    payload = {"message": message, "data": data or {}}
    return jsonify(payload), status


def _parse_date(value):
    """Parse ISO formatted date strings into datetime objects."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _normalize_expense_type(value):
    """Return the matching Category row when the slug is valid."""
    if value is None or not isinstance(value, str):
        return None

    normalized = value.strip().lower()
    if normalized not in ALLOWED_EXPENSE_TYPES:
        return None

    return Category.query.filter_by(slug=normalized).first()


def _expense_type_error():
    """Common response for invalid expense type submissions."""
    allowed = sorted(ALLOWED_EXPENSE_TYPES)
    return _json_response(
        "Invalid expense type.",
        {"errors": [f"Category must be one of: {', '.join(allowed)}."]},
        status=400,
    )


def _serialize_expense(expense):
    """Convert database model into a JSON-serializable dict."""
    if hasattr(expense, "to_dict"):
        return expense.to_dict()
    return {
        "id": expense.id,
        "user_id": expense.user_id,
        "title": expense.title,
        "amount": expense.amount,
        "category": expense.category.slug if expense.category else None,
        "category_name": expense.category.name if expense.category else None,
        "date": expense.date.isoformat() if expense.date else None,
        "description": expense.description,
        "card": expense.card.to_dict() if expense.card else None,
    }


def _extract_user_id(user_payload):
    """Get the integer user id from token payload."""
    if not isinstance(user_payload, dict):
        return None
    try:
        return int(user_payload.get("user_id"))
    except (TypeError, ValueError):
        return None


def _load_card_for_user(card_id, user_id):
    """Return the card matching the given user scope."""
    if card_id is None:
        return None
    try:
        card_id_int = int(card_id)
    except (TypeError, ValueError):
        return None
    return Card.query.filter_by(id=card_id_int, user_id=user_id).first()


def _card_not_found_response():
    """Common response when card lookup fails."""
    return _json_response(
        "Card not found.",
        {"errors": ["Provided card_id does not exist for this user."]},
        status=404,
    )


@expenses_bp.route("/api/expenses", methods=["POST"])
@token_required
def create_expense(user_payload):
    """Create a new expense scoped to the authenticated user."""
    payload = request.get_json(silent=True) or {}

    errors = validate_expense(payload)
    if errors:
        return _json_response("Validation failed.", {"errors": errors}, status=400)

    category = _normalize_expense_type(payload.get("category"))
    if not category:
        return _expense_type_error()

    user_id = _extract_user_id(user_payload)
    if user_id is None:
        return _json_response("Authentication required.", {}, status=401)

    card = _load_card_for_user(payload.get("card_id"), user_id)
    if not card:
        return _card_not_found_response()

    expense = Expense(
        user_id=user_id,
        title=payload.get("title"),
        amount=float(payload.get("amount")),
        category=category,
        card=card,
        description=payload.get("description"),
    )

    if "date" in payload and payload.get("date") is not None:
        explicit_date = _parse_date(payload.get("date"))
        if not explicit_date:
            return _json_response(
                "Invalid date format. Use ISO 8601 format.",
                {"errors": ["Invalid date"]},
                status=400,
            )
        expense.date = explicit_date

    try:
        db.session.add(expense)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return _json_response(
            "Failed to create expense due to a server error.", status=400, data={}
        )

    return _json_response(
        "Expense created successfully.", {"expense": _serialize_expense(expense)}, 201
    )


@expenses_bp.route("/api/expenses", methods=["GET"])
@token_required
def list_expenses(user_payload):
    """Return paginated expenses filtered and sorted for the current user."""
    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", default=10, type=int)
    page = max(page, 1)
    limit = max(1, min(limit, 100))

    raw_category = request.args.get("category")
    category_row = None
    category_slug = None
    if raw_category:
        category_row = _normalize_expense_type(raw_category)
        if not category_row:
            return _expense_type_error()
        category_slug = category_row.slug

    sort = request.args.get("sort", default="date").lower()
    order = request.args.get("order", default="desc").lower()

    sortable_fields = {
        "date": Expense.date,
        "amount": Expense.amount,
        "title": Expense.title,
        "category": Category.slug,
        "card": Card.name,
    }
    sort_column = sortable_fields.get(sort, Expense.date)
    sort_order = sort_column.desc() if order == "desc" else sort_column.asc()

    user_id = _extract_user_id(user_payload)
    if user_id is None:
        return _json_response("Authentication required.", {}, status=401)

    query = (
        Expense.query.outerjoin(Category)
        .outerjoin(Card)
        .filter(Expense.user_id == user_id)
    )

    if category_row:
        query = query.filter(Expense.category == category_row)

    pagination = query.order_by(sort_order).paginate(
        page=page, per_page=limit, error_out=False
    )

    data = {
        "items": [_serialize_expense(expense) for expense in pagination.items],
        "pagination": {
            "page": pagination.page,
            "limit": pagination.per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        },
        "filters": {"category": category_slug, "sort": sort, "order": order},
    }
    return _json_response("Expenses retrieved successfully.", data, status=200)


@expenses_bp.route("/api/expenses/<int:expense_id>", methods=["GET"])
@token_required
def get_expense(user_payload, expense_id):
    """Return a single expense owned by the authenticated user."""
    user_id = _extract_user_id(user_payload)
    if user_id is None:
        return _json_response("Authentication required.", {}, status=401)

    expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()

    if not expense:
        return _json_response("Expense not found.", data={}, status=404)

    return _json_response(
        "Expense retrieved successfully.", {"expense": _serialize_expense(expense)}, 200
    )


@expenses_bp.route("/api/expenses/<int:expense_id>", methods=["PUT", "PATCH"])
@token_required
def update_expense(user_payload, expense_id):
    """Update a user's expense with partial or full payloads."""
    user_id = _extract_user_id(user_payload)
    if user_id is None:
        return _json_response("Authentication required.", {}, status=401)

    expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()

    if not expense:
        return _json_response("Expense not found.", data={}, status=404)

    payload = request.get_json(silent=True) or {}

    if "category" in payload:
        category_row = _normalize_expense_type(payload.get("category"))
        if not category_row:
            return _expense_type_error()
    else:
        category_row = expense.category

    merged_payload = {
        "title": payload.get("title", expense.title),
        "amount": payload.get("amount", expense.amount),
        "category": category_row.slug if category_row else None,
    }
    errors = validate_expense(merged_payload)
    if errors:
        return _json_response("Validation failed.", {"errors": errors}, status=400)

    if "title" in payload:
        expense.title = payload["title"]
    if "amount" in payload:
        expense.amount = float(payload["amount"])
    if "category" in payload and category_row:
        expense.category = category_row
    if "card_id" in payload:
        card = _load_card_for_user(payload.get("card_id"), user_id)
        if not card:
            return _card_not_found_response()
        expense.card = card
    if "description" in payload:
        expense.description = payload["description"]

    if "date" in payload:
        explicit_date = _parse_date(payload.get("date"))
        if not explicit_date and payload.get("date") is not None:
            return _json_response(
                "Invalid date format. Use ISO 8601 format.", {"errors": ["Invalid date"]}, 400
            )
        if explicit_date:
            expense.date = explicit_date

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return _json_response(
            "Failed to update expense due to a server error.", status=400, data={}
        )

    return _json_response(
        "Expense updated successfully.", {"expense": _serialize_expense(expense)}, 200
    )


@expenses_bp.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
@token_required
def delete_expense(user_payload, expense_id):
    """Delete an expense that belongs to the authenticated user."""
    user_id = _extract_user_id(user_payload)
    if user_id is None:
        return _json_response("Authentication required.", {}, status=401)

    expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()

    if not expense:
        return _json_response("Expense not found.", data={}, status=404)

    try:
        db.session.delete(expense)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return _json_response(
            "Failed to delete expense due to a server error.", status=400, data={}
        )

    return _json_response("Expense deleted successfully.", {"expense_id": expense_id}, 200)


# Canonical expense types.
class ExpenseType(str, Enum):
    """Enumerated expense categories."""

    INVESTMENT = "investment"
    WANTS = "wants"
    NEED = "need"


ALLOWED_EXPENSE_TYPES = {expense_type.value for expense_type in ExpenseType}
