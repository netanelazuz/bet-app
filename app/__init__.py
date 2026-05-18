"""BET application factory"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from prometheus_flask_exporter import PrometheusMetrics

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import Config

db = SQLAlchemy()
migrate = Migrate()
metrics = PrometheusMetrics.for_app_factory()


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    migrate.init_app(app, db)

    # Expose /metrics for Prometheus scraping.
    # Automatically instruments all routes with request count and latency.
    metrics.init_app(app)

    from app.auth import auth_bp
    from app.views import main_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_current_user():
        from app.auth import get_current_user_id
        from app.models import User
        try:
            user_id = get_current_user_id()
            current_user = User.query.get(int(user_id)) if user_id else None
        except Exception:
            current_user = None
        return {"current_user": current_user}

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    return app
