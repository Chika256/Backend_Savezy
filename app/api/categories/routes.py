"""Categories blueprint providing CRUD operations for expense categories."""

import re

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Category, Expense
from app.utils.jwt_helper import token_required

categories_bp = Blueprint("categories", __name__, url_prefix="/api/categories")


def _json_response(message, data=None, status=200):
    payload = {"message": message, "data": data or {}}
    return jsonify(payload), status


def _slugify(value: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", value).strip().lower()
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug


def _validate_category_payload(payload, *, partial=False):
    if payload is None:
        return {}, ["Request body is required."]

    errors = []
    normalized = {}

    if not partial or "name" in payload:
        name = payload.get("name")
        if not name or not isinstance(name, str):
            errors.append("name is required and must be a string.")
        else:
            normalized["name"] = name.strip()
            normalized["slug"] = _slugify(name)

    if "description" in payload:
        description = payload.get("description")
        if description is not None and not isinstance(description, str):
            errors.append("description must be a string.")
        else:
            normalized["description"] = (
                description.strip() if isinstance(description, str) else None
            )

    return normalized, errors


def _serialize_category(category):
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
    }


@categories_bp.route("", methods=["POST"])
@token_required
def create_category(_user_payload):
    """Create a new category."""
    payload = request.get_json(silent=True)
    data, errors = _validate_category_payload(payload)
    if errors:
        return _json_response("Validation failed.", {"errors": errors}, status=400)

    slug = data["slug"]
    if Category.query.filter_by(slug=slug).first():
        return _json_response(
            "Validation failed.",
            {"errors": ["Category with this name already exists."]},
            status=400,
        )

    category = Category(
        name=data["name"],
        slug=slug,
        description=data.get("description"),
    )

    try:
        db.session.add(category)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return _json_response(
            "Failed to create category due to a server error.", status=500
        )

    return _json_response(
        "Category created successfully.",
        {"category": _serialize_category(category)},
        status=201,
    )


@categories_bp.route("", methods=["GET"])
@token_required
def list_categories(_user_payload):
    """List categories with optional search and pagination."""
    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", default=10, type=int)
    search = (request.args.get("search") or "").strip()
    sort = (request.args.get("sort") or "name").lower()
    order = (request.args.get("order") or "asc").lower()

    page = max(page, 1)
    limit = max(1, min(limit, 100))

    sortable_fields = {
        "name": Category.name,
        "slug": Category.slug,
    }
    sort_column = sortable_fields.get(sort, Category.name)
    sort_order = sort_column.asc() if order == "asc" else sort_column.desc()

    query = Category.query
    if search:
        like_pattern = f"%{search.lower()}%"
        query = query.filter(
            db.or_(
                db.func.lower(Category.name).like(like_pattern),
                db.func.lower(Category.slug).like(like_pattern),
            )
        )

    pagination = query.order_by(sort_order).paginate(
        page=page, per_page=limit, error_out=False
    )

    data = {
        "items": [_serialize_category(category) for category in pagination.items],
        "pagination": {
            "page": pagination.page,
            "limit": pagination.per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        },
        "filters": {
            "search": search or None,
            "sort": sort,
            "order": order,
        },
    }
    return _json_response("Categories retrieved successfully.", data)


@categories_bp.route("/<int:category_id>", methods=["GET"])
@token_required
def get_category(_user_payload, category_id):
    """Fetch a single category."""
    category = Category.query.get(category_id)
    if not category:
        return _json_response("Category not found.", status=404)

    return _json_response(
        "Category retrieved successfully.", {"category": _serialize_category(category)}
    )


@categories_bp.route("/<int:category_id>", methods=["PUT", "PATCH"])
@token_required
def update_category(_user_payload, category_id):
    """Update an existing category."""
    category = Category.query.get(category_id)
    if not category:
        return _json_response("Category not found.", status=404)

    payload = request.get_json(silent=True)
    data, errors = _validate_category_payload(payload, partial=True)
    if errors:
        return _json_response("Validation failed.", {"errors": errors}, status=400)

    if "name" in data:
        slug = data["slug"]
        existing = Category.query.filter(Category.slug == slug, Category.id != category.id).first()
        if existing:
            return _json_response(
                "Validation failed.",
                {"errors": ["Category with this name already exists."]},
                status=400,
            )
        category.name = data["name"]
        category.slug = slug

    if "description" in data:
        category.description = data["description"]

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return _json_response(
            "Failed to update category due to a server error.", status=500
        )

    return _json_response(
        "Category updated successfully.", {"category": _serialize_category(category)}
    )


@categories_bp.route("/<int:category_id>", methods=["DELETE"])
@token_required
def delete_category(_user_payload, category_id):
    """Delete a category if unused."""
    category = Category.query.get(category_id)
    if not category:
        return _json_response("Category not found.", status=404)

    if category.expenses.count() > 0:
        return _json_response(
            "Unable to delete category with associated expenses.", status=409
        )

    try:
        db.session.delete(category)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return _json_response(
            "Failed to delete category due to a server error.", status=500
        )

    return _json_response("Category deleted successfully.", {"category_id": category_id})
