"""
Stateless Flask application factory for ezzone.
"""

import os
from flask import Flask, send_from_directory


def create_app(test_config=None) -> Flask:
    """Create and configure the Flask application."""
    # Calculate paths relative to this file
    src_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(src_dir))
    dist_folder = os.path.join(project_root, 'dist')

    app = Flask(__name__, 
                instance_relative_config=True,
                static_folder=dist_folder,
                static_url_path='/')

    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('FLASK_SECRET_KEY', 'dev'),
        UPLOAD_FOLDER=os.path.join(app.root_path, 'static/uploads'),
        CACHE_FOLDER=os.path.join(app.instance_path, 'cache'),
        ALLOWED_EXTENSIONS={'txt', 'csv'},
    )

    if test_config: app.config.update(test_config)

    # Ensure required directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['CACHE_FOLDER'], exist_ok=True)

    # Register API blueprint
    from .api import api_bp
    app.register_blueprint(api_bp)

    # Serve static files for Vue SPA
    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        file_path = os.path.join(app.static_folder, path)
        if os.path.isfile(file_path):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    return app
