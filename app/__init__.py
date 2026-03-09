"""BET application factory."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import Config

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    migrate.init_app(app, db)

    from app.auth import auth_bp
    from app.views import main_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main_bp)

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    return app
