from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app(config_name='default'):
    # Application factory
    app = Flask(__name__)

    # config load
    app.config.from_object(config[config_name])

    # extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])

    # blueprints
    from app.routes import expenses_bp

    app.register_blueprint(expenses_bp)

    # checking
    @app.route('/check')
    def check():
        return {'status': 'healthy', 'message': 'Savezy API is running'}, 200

    return app
