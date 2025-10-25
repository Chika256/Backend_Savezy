"""Expenses blueprint exposing CRUD endpoints for authenticated users."""

from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
# from app.auth.middleware import auth_required
from app.models import Expense
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


def _serialize_expense(expense):
    """Convert database model into a JSON-serializable dict."""
    if hasattr(expense, "to_dict"):
        return expense.to_dict()
    return {
        "id": expense.id,
        "user_id": expense.user_id,
        "title": expense.title,
        "amount": expense.amount,
        "category": expense.category,
        "date": expense.date.isoformat() if expense.date else None,
        "description": expense.description,
    }


@expenses_bp.route("/api/expenses", methods=["POST"])
# @auth_required
def create_expense():
    """Create a new expense scoped to the authenticated user."""
    payload = request.get_json(silent=True) or {}

    errors = validate_expense(payload)
    if errors:
        return _json_response("Validation failed.", {"errors": errors}, status=400)

    expense = Expense(
        user_id=request.user.id,
        title=payload.get("title"),
        amount=float(payload.get("amount")),
        category=payload.get("category"),
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
# @auth_required
def list_expenses():
    """Return paginated expenses filtered and sorted for the current user."""
    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", default=10, type=int)
    page = max(page, 1)
    limit = max(1, min(limit, 100))

    category = request.args.get("category")
    sort = request.args.get("sort", default="date").lower()
    order = request.args.get("order", default="desc").lower()

    sortable_fields = {
        "date": Expense.date,
        "amount": Expense.amount,
        "title": Expense.title,
        "category": Expense.category,
    }
    sort_column = sortable_fields.get(sort, Expense.date)
    sort_order = sort_column.desc() if order == "desc" else sort_column.asc()

    query = Expense.query.filter_by(user_id=request.user.id)
    if category:
        query = query.filter(Expense.category == category)

    query = query.order_by(sort_order)

    pagination = query.paginate(page=page, per_page=limit, error_out=False)

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
        "filters": {"category": category, "sort": sort, "order": order},
    }
    return _json_response("Expenses retrieved successfully.", data, status=200)


@expenses_bp.route("/api/expenses/<int:expense_id>", methods=["GET"])
# @auth_required
def get_expense(expense_id):
    """Return a single expense owned by the authenticated user."""
    expense = Expense.query.filter_by(
        id=expense_id, user_id=request.user.id
    ).first()

    if not expense:
        return _json_response("Expense not found.", data={}, status=404)

    return _json_response(
        "Expense retrieved successfully.", {"expense": _serialize_expense(expense)}, 200
    )


@expenses_bp.route("/api/expenses/<int:expense_id>", methods=["PUT", "PATCH"])
# @auth_required
def update_expense(expense_id):
    """Update a user's expense with partial or full payloads."""
    expense = Expense.query.filter_by(
        id=expense_id, user_id=request.user.id
    ).first()

    if not expense:
        return _json_response("Expense not found.", data={}, status=404)

    payload = request.get_json(silent=True) or {}
    merged_payload = {
        "title": payload.get("title", expense.title),
        "amount": payload.get("amount", expense.amount),
        "category": payload.get("category", expense.category),
    }
    errors = validate_expense(merged_payload)
    if errors:
        return _json_response("Validation failed.", {"errors": errors}, status=400)

    if "title" in payload:
        expense.title = payload["title"]
    if "amount" in payload:
        expense.amount = float(payload["amount"])
    if "category" in payload:
        expense.category = payload["category"]
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
# @auth_required
def delete_expense(expense_id):
    """Delete an expense that belongs to the authenticated user."""
    expense = Expense.query.filter_by(
        id=expense_id, user_id=request.user.id
    ).first()

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
