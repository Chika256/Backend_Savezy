from flask import Flask
from flask_cors import CORS

from config import config
from app.extensions import db, migrate, jwt


def create_app(config_name='default'):
    # app factory
    app = Flask(__name__)

    # config load
    app.config.from_object(config[config_name])

    # extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])

    # blueprints
    from app.api.auth.routes import auth_bp
    from app.api.expenses.routes import expenses_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)

    # checking
    @app.route('/check')
    def check():
        return {'status': 'healthy', 'message': 'Savezy API is running'}, 200

    return app
