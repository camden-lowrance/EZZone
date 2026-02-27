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
    from .io_service import DataError
    app.register_blueprint(api_bp)

    @app.errorhandler(DataError)
    def handle_data_error(e):
        return e.to_json(), 422

    @app.errorhandler(400)
    def bad_request(e):
        return {'error': str(e.description), 'code': 'BAD_REQUEST'}, 400

    @app.errorhandler(404)
    def not_found(e):
        return {'error': 'Endpoint not found', 'code': 'NOT_FOUND'}, 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return {'error': 'Method not allowed', 'code': 'METHOD_NOT_ALLOWED'}, 405

    @app.errorhandler(500)
    def internal_error(e):
        return {'error': 'An unexpected server error occurred.', 'code': 'SERVER_ERROR'}, 500

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
