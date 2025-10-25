from flask import Blueprint, request, jsonify, current_app
from urllib.parse import urlparse, urlencode, unquote
import os
import secrets
import hashlib

try:  # pragma: no cover - optional dependency for tests
    import requests
except ImportError:  # pragma: no cover
    requests = None

from app.utils.jwt_helper import generate_jwt
from app.models import User
from app.extensions import db, limiter

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

state_store = {}

@auth_bp.route('/google/init', methods=['GET'])
@limiter.limit("10 per minute")
def google_init():
    mobile_redirect_uri = request.args.get('redirect_uri')

    if not mobile_redirect_uri:
        return {'error': 'redirect_uri is required'}, 400

    allowed_uris = os.getenv('ALLOWED_MOBILE_REDIRECT_URIS', '').split(',')
    if mobile_redirect_uri not in allowed_uris:
        return jsonify({'error': 'Invalid redirect_uri'}), 400

    state_token = secrets.token_urlsafe(32)

    state_store[state_token] = mobile_redirect_uri

    google_auth_base_url = 'https://accounts.google.com/o/oauth2/v2/auth'

    params = {
        'client_id': os.getenv('GOOGLE_CLIENT_ID'),
        'redirect_uri': os.getenv('GOOGLE_REDIRECT_URI'),  # backend callback
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'state': state_token
    }

    auth_url = f"{google_auth_base_url}?{urlencode(params)}"

    return jsonify({'auth_url': auth_url}), 200

@auth_bp.route('/google/callback', methods=['POST'])
@limiter.limit("5 per minute")
def google_callback():
    """
    Exchange authorization code for Google access token and return JWT

    Expected request body:
    {
        "code": "AUTH_CODE_FROM_GOOGLE",
        "state": "STATE_TOKEN_FROM_INIT",
        "redirect_uri": "myapp://auth/callback"
    }
    """
    try:
        if requests is None:
            return jsonify({'error': 'requests library not installed'}), 500
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        auth_code = data.get('code')
        state_token = data.get('state')
        mobile_redirect_uri = data.get('redirect_uri')

        if not auth_code:
            return jsonify({'error': 'Authorization code is required'}), 400

        if not state_token:
            return jsonify({'error': 'State token is required'}), 400

        if not mobile_redirect_uri:
            return jsonify({'error': 'redirect_uri is required'}), 400

        # Validate state token to prevent CSRF attacks
        if state_token not in state_store:
            return jsonify({'error': 'Invalid or expired state token'}), 400

        stored_redirect_uri = state_store.get(state_token)
        if stored_redirect_uri != mobile_redirect_uri:
            return jsonify({'error': 'redirect_uri does not match state'}), 400

        # Remove used state token (one-time use)
        del state_store[state_token]

        auth_code = unquote(auth_code)

        allowed_uris = os.getenv('ALLOWED_MOBILE_REDIRECT_URIS', '').split(',')
        if mobile_redirect_uri not in allowed_uris:
            return jsonify({'error': 'Invalid redirect_uri'}), 400

        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': auth_code,
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'redirect_uri': os.getenv('GOOGLE_REDIRECT_URI'),
            'grant_type': 'authorization_code'
        }

        token_response = requests.post(token_url, data=token_data)

        if token_response.status_code != 200:
            return jsonify({
                'error': 'Failed to exchange authorization code',
                'details': token_response.json()
            }), 400

        token_json = token_response.json()
        access_token = token_json.get('access_token')

        if not access_token:
            return jsonify({'error': 'No access token received from Google'}), 400

        # fetch user info from google
        userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_response = requests.get(userinfo_url, headers=headers)

        if userinfo_response.status_code != 200:
            return jsonify({
                'error': 'Failed to fetch user information',
                'details': userinfo_response.json()
            }), 400

        user_info = userinfo_response.json()

        # extract user details
        google_id = user_info.get('id') ##
        email = user_info.get('email')
        name = user_info.get('name')
        picture = user_info.get('picture')

        if not google_id or not email:
            return jsonify({'error': 'Invalid user information from Google'}), 400

        # Create or update user in database
        try:
            user = User.query.filter_by(email=email).first()

            if not user:
                # Create new user
                user = User(email=email, name=name)
                db.session.add(user)
                db.session.commit()
            else:
                # Update existing user info
                user.name = name
                db.session.commit()

        except Exception as db_error:
            db.session.rollback()
            return jsonify({
                'error': 'Database error occurred',
                'details': str(db_error)
            }), 500

        # Generate JWT token with database user ID
        jwt_token = generate_jwt(user_id=user.id, email=user.email)

        # return success response with JWT and user info
        return jsonify({
            'success': True,
            'token': jwt_token,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'picture': picture
            }
        }), 200

    except requests.RequestException as e:
        return jsonify({'error': 'Network error occurred', 'details': str(e)}), 500
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


# @auth_bp.route('/token/verify', methods=['POST'])
# @limiter.limit("20 per minute")
# def verify_token():
#     """
#     Verify JWT token validity
#
#     Expected request body:
#     {
#         "token": "JWT_TOKEN_HERE"
#     }
#     Or Authorization header: Bearer <token>
#     """
#     from app.utils.jwt_helper import decode_jwt
#
#     try:
#         data = request.get_json(silent=True) or {}
#
#         token = data.get('token')
#
#         if not token:
#             # Also check Authorization header
#             auth_header = request.headers.get('Authorization')
#             if auth_header and auth_header.startswith('Bearer '):
#                 token = auth_header.replace('Bearer ', '')
#
#         if not token:
#             return jsonify({'error': 'Token is required'}), 400
#
#         # Decode and verify token
#         payload = decode_jwt(token)
#
#         if not payload:
#             return jsonify({
#                 'valid': False,
#                 'error': 'Token is invalid or expired'
#             }), 401
#
#         # Return token validity and payload
#         return jsonify({
#             'valid': True,
#             'payload': {
#                 'user_id': payload.get('user_id'),
#                 'email': payload.get('email'),
#                 'iat': payload.get('iat'),
#                 'exp': payload.get('exp')
#             }
#         }), 200
#
#     except Exception as e:
#         return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
#

@auth_bp.route('/google/verify', methods=['POST'])
@limiter.limit("10 per minute")
def google_verify():
    """
    Verify Google ID token (for Flutter/Mobile direct sign-in) and return JWT

    This endpoint is for mobile apps using Google Sign-In SDK directly.
    The mobile app gets an ID token from Google and sends it here to exchange for JWT.

    Request Body:
        {
            "id_token": "google_id_token_from_flutter"
        }

    Response:
        {
            "success": true,
            "token": "your_jwt_token",
            "user": {
                "id": 1,
                "email": "user@example.com",
                "name": "John Doe",
                "picture": "https://..."
            }
        }
    """
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        data = request.get_json()

        if not data or 'id_token' not in data:
            return jsonify({
                'success': False,
                'error': 'id_token is required'
            }), 400

        # Verify Google ID token
        try:
            idinfo = id_token.verify_oauth2_token(
                data['id_token'],
                google_requests.Request(),
                os.getenv('GOOGLE_CLIENT_ID')
            )

            # Extract user info from ID token
            email = idinfo.get('email')
            name = idinfo.get('name')
            picture = idinfo.get('picture')
            google_id = idinfo.get('sub')

            if not email:
                return jsonify({
                    'success': False,
                    'error': 'Email not found in ID token'
                }), 400

        except ValueError as e:
            return jsonify({
                'success': False,
                'error': f'Invalid ID token: {str(e)}'
            }), 401

        # Create or update user in database
        try:
            user = User.query.filter_by(email=email).first()

            if not user:
                user = User(email=email, name=name)
                db.session.add(user)
                db.session.commit()
            else:
                user.name = name
                db.session.commit()

        except Exception as db_error:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': 'Database error occurred'
            }), 500

        # Generate JWT token
        jwt_token = generate_jwt(user_id=user.id, email=user.email)

        return jsonify({
            'success': True,
            'token': jwt_token,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'picture': picture
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error in google_verify: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@auth_bp.route('/token/verify2', methods=['POST'])
@limiter.limit("20 per minute")
def token_verify2():
    """
    Alternative JWT token verification endpoint (simpler response format)

    Request Body:
        {
            "token": "jwt_token"
        }

    Response:
        {
            "success": true,
            "valid": true,
            "user_id": 1,
            "email": "user@example.com"
        }
    """
    from app.utils.jwt_helper import decode_jwt

    try:
        data = request.get_json(silent=True) or {}

        token = data.get('token')

        if not token:
            # Check Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.replace('Bearer ', '')

        if not token:
            return jsonify({
                'success': False,
                'valid': False,
                'error': 'token is required'
            }), 400

        # Verify JWT
        payload = decode_jwt(token)

        if not payload:
            return jsonify({
                'success': False,
                'valid': False,
                'error': 'Token is invalid or expired'
            }), 401

        return jsonify({
            'success': True,
            'valid': True,
            'user_id': payload['user_id'],
            'email': payload['email']
        }), 200

    except Exception as e:
<<<<<<< Updated upstream
        current_app.logger.error(f"Error in token_verify: {str(e)}")
        return jsonify({
            'success': False,
            'valid': False,
            'error': 'Internal server error'
        }), 500


@auth_bp.route('/token/refresh2', methods=['POST'])
@limiter.limit("10 per minute")
def token_refresh2():
    """
    Alternative JWT token refresh endpoint

    Request Body:
        {
            "token": "current_jwt_token"
        }

    Response:
        {
            "success": true,
            "token": "new_jwt_token"
        }
    """
    from app.utils.jwt_helper import refresh_jwt

    try:
        data = request.get_json(silent=True) or {}

        token = data.get('token')

        if not token:
            # Check Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.replace('Bearer ', '')

        if not token:
            return jsonify({
                'success': False,
                'error': 'token is required'
            }), 400

        # Refresh the token
        new_token = refresh_jwt(token)

        if not new_token:
            return jsonify({
                'success': False,
                'error': 'Token is invalid and cannot be refreshed'
            }), 401

        return jsonify({
            'success': True,
            'token': new_token
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error in token_refresh: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
=======
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
>>>>>>> Stashed changes
