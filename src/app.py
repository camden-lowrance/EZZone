"""
Flask application factory for ezzone.

Creates and configures the Flask application.
"""

import os

from flask import Flask


def create_app(test_config=None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        test_config: Optional test configuration override.

    Returns:
        Configured Flask application.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-in-production'),
        UPLOAD_FOLDER=os.path.join(app.root_path, 'static/uploads'),
        ALLOWED_EXTENSIONS={'txt', 'csv'},
    )

    # Override with test config if provided
    if test_config is not None:
        app.config.update(test_config)

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprints
    from src.api import api_bp
    app.register_blueprint(api_bp)

    # Register main routes
    from src.api import main_bp
    app.register_blueprint(main_bp)

    return app
