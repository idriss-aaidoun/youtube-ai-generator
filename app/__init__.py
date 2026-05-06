from __future__ import annotations

from pathlib import Path

from flask import Flask

from app.api.routes import bp as main_bp
from app.config import Config
from app.extensions import db


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_object)

    output_dir = Path(app.config["OUTPUT_DIR"])
    output_dir.mkdir(parents=True, exist_ok=True)
    app.config["OUTPUT_DIR"] = output_dir

    db.init_app(app)
    app.register_blueprint(main_bp)

    with app.app_context():
        from app import models  # noqa: F401

        db.create_all()

    return app
