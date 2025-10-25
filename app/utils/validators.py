"""Validation helpers for incoming request payloads."""


def validate_expense(data):
    """Validate incoming expense data and return a list of error messages."""
    errors = []

    if not data.get("title"):
        errors.append("Title is required.")

    amount = data.get("amount")
    if amount is None or not isinstance(amount, (int, float)):
        errors.append("Amount must be a number.")

    if not data.get("category"):
        errors.append("Category is required.")

    return errors

