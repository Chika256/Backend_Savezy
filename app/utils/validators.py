"""Validation helpers for incoming request payloads."""


DEFAULT_EXPENSE_TYPES = {"investment", "wants", "need"}


def validate_expense(data, *, require_type=True, allowed_types=None):
    """Validate incoming expense data and return a list of error messages."""
    errors = []

    if not data.get("title"):
        errors.append("Title is required.")

    amount = data.get("amount")
    if amount is None:
        errors.append("Amount must be a number.")
    else:
        try:
            float(amount)
        except (TypeError, ValueError):
            errors.append("Amount must be a number.")

    if not data.get("category"):
        errors.append("Category is required.")

    allowed = allowed_types or DEFAULT_EXPENSE_TYPES
    expense_type = data.get("type")
    if require_type:
        if not expense_type:
            errors.append("type is required.")
        elif expense_type not in allowed:
            errors.append(
                f"type must be one of: {', '.join(sorted(allowed))}."
            )
    elif expense_type is not None and expense_type not in allowed:
        errors.append(
            f"type must be one of: {', '.join(sorted(allowed))}."
        )

    return errors
