from flask import Blueprint, request, jsonify, current_app
from urllib.parse import urlparse, urlencode, unquote
import os
import requests
import secrets
import hashlib
from app.utils.jwt_helper import generate_jwt

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

state_store = {}

@auth_bp.route('/google/init', methods=['GET'])
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
def google_callback():
    """
    Exchange authorization code for Google access token and return JWT

    Expected request body:
    {
        "code": "AUTH_CODE_FROM_GOOGLE",
        "redirect_uri": "myapp://auth/callback"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        auth_code = data.get('code')
        mobile_redirect_uri = data.get('redirect_uri')

        if not auth_code:
            return jsonify({'error': 'Authorization code is required'}), 400

        if not mobile_redirect_uri:
            return jsonify({'error': 'redirect_uri is required'}), 400

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

        # TODO: create or update user in database
        # For now, we'll just generate JWT with user info
        # Once User model is created, add:
        # user = User.query.filter_by(google_id=google_id).first()
        # if not user:
        #     user = User(google_id=google_id, email=email, name=name, picture=picture)
        #     db.session.add(user)
        # else:
        #     user.name = name
        #     user.picture = picture
        #     user.last_login = datetime.utcnow()
        # db.session.commit()

        # generating JWT token
        jwt_token = generate_jwt(user_id=google_id, email=email)

        # return success response with JWT and user info
        return jsonify({
            'success': True,
            'token': jwt_token,
            'user': {
                'id': google_id,
                'email': email,
                'name': name,
                'picture': picture
            }
        }), 200

    except requests.RequestException as e:
        return jsonify({'error': 'Network error occurred', 'details': str(e)}), 500
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@auth_bp.route('/token/verify', methods=['POST'])
def verify_token():
    """
    Verify JWT token validity

    Expected request body:
    {
        "token": "JWT_TOKEN_HERE"
    }
    """
    from app.utils.jwt_helper import decode_jwt

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        token = data.get('token')

        if not token:
            # Also check Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.replace('Bearer ', '')

        if not token:
            return jsonify({'error': 'Token is required'}), 400

        # Decode and verify token
        payload = decode_jwt(token)

        if not payload:
            return jsonify({
                'valid': False,
                'error': 'Token is invalid or expired'
            }), 401

        # Return token validity and payload
        return jsonify({
            'valid': True,
            'payload': {
                'user_id': payload.get('user_id'),
                'email': payload.get('email'),
                'iat': payload.get('iat'),
                'exp': payload.get('exp')
            }
        }), 200

    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500