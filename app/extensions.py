"""Flask extensions initialization - avoids circular imports."""

import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

try:  # pragma: no cover - authlib optional in tests
    from authlib.integrations.flask_client import OAuth
except ImportError:  # pragma: no cover - fallback stub for test environments
    OAuth = None

# Initialize extensions here (not bound to app yet)
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
oauth = OAuth()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)
oauth = OAuth() if OAuth else None

def init_oauth(app):
    if oauth is None:
        raise RuntimeError("Authlib is not installed; cannot configure OAuth.")

    oauth.init_app(app)

    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    return oauth
