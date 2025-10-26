import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from app.models import APIKey


JWT_SECRET = os.getenv('JWT_SECRET_KEY')
JWT_ALGORITHM = 'HS256'
JWT_EXP_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))

def generate_jwt(user_id, email):
    """generating JWT token"""
    payload = {
        'user_id': user_id,
        'email': email,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXP_HOURS)
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_jwt(token):
    """decoding and verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def refresh_jwt(token):
    """Refresh an expired or expiring JWT token"""
    try:
        # Decode without verification to get payload even if expired
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"verify_exp": False})

        # Generate new token with same user info
        new_token = generate_jwt(user_id=payload['user_id'], email=payload['email'])
        return new_token
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """decorator to protect routes"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'X-Api-Key' in request.headers:
            token = request.headers['X-Api-Key']
            key = APIKey.query.filter_by(key=token).first()
            if not key:
                return jsonify({'error': 'Invalid API key'}), 401
            else:
                return f(key, *args, **kwargs)

        # getting token from header
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].replace('Bearer ', '')

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        payload = decode_jwt(token)
        if not payload:
            return jsonify({'error': 'Token is invalid or expired'}), 401

        # passing user info to route
        return f(payload, *args, **kwargs)

    return decorated