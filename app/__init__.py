from pathlib import Path

from flask import Flask, render_template_string, send_file, url_for
from flask_cors import CORS

from config import config
from app.extensions import db, migrate, jwt, limiter


BASE_DIR = Path(__file__).resolve().parent.parent
OPENAPI_PATH = BASE_DIR / "docs" / "openapi.yaml"
SWAGGER_UI_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>Savezy API Docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
    <style>
      body { margin: 0; background: #f5f5f5; }
      #swagger-ui { box-sizing: border-box; }
    </style>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.onload = () => {
        window.ui = SwaggerUIBundle({
          url: "{{ openapi_url }}",
          dom_id: '#swagger-ui',
          presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
          layout: "BaseLayout"
        });
      };
    </script>
  </body>
</html>
"""


def create_app(config_name='default'):
    # app factory
    app = Flask(__name__)

    # config load
    app.config.from_object(config[config_name])

    # extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])

    # blueprints
    from app.api.auth.routes import auth_bp
    from app.api.expenses.routes import expenses_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)

    @app.route("/openapi.yaml")
    def openapi_spec():
        """Serve the OpenAPI specification."""
        return send_file(OPENAPI_PATH, mimetype="application/yaml")

    @app.route("/docs")
    def swagger_docs():
        """Render Swagger UI backed by the OpenAPI spec."""
        return render_template_string(
            SWAGGER_UI_TEMPLATE,
            openapi_url=url_for("openapi_spec", _external=False),
        )

    # checking
    @app.route('/check')
    def check():
        return {'status': 'healthy', 'message': 'Savezy API is running'}, 200

    return app
