"""
Flask application factory.
"""
import logging
from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.database import init_db


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable CORS for all routes
    CORS(app)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Initialize the database
    init_db(app)

    # Register blueprints
    from app.routes.analyze import analyze_bp
    app.register_blueprint(analyze_bp, url_prefix="/api")

    return app
