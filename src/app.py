"""
Flask application factory for ezzone.

Creates and configures the Flask application for JSON API only.
"""

import os

from flask import Flask, send_from_directory


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

    # Register API blueprint
    from src.api import api_bp
    app.register_blueprint(api_bp)

    # Serve static files for Vue SPA
    @app.route('/')
    def index():
        return send_from_directory(os.path.join(app.root_path, 'static'), 'index.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        static_dir = os.path.join(app.root_path, 'static')
        file_path = os.path.join(static_dir, path)
        if os.path.isfile(file_path):
            return send_from_directory(static_dir, path)
        return send_from_directory(static_dir, 'index.html')

    return app
