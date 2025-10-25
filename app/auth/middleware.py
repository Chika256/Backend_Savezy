"""Authentication middleware placeholder.

The real implementation should verify Google-issued ID tokens and attach the
authenticated user to `request.user`. A separate team owns that integration.
"""

from functools import wraps

from flask import jsonify


def auth_required(fn):
    """Placeholder decorator until the real authentication layer is wired."""

    @wraps(fn)
    def _wrapped(*args, **kwargs):
        return jsonify(
            {
                "message": "Authentication required.",
                "data": {
                    "error": "Google OAuth integration pending. "
                    "Implement auth middleware before enabling this endpoint."
                },
            }
        ), 401

    return _wrapped
