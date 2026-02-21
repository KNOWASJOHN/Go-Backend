"""
Flask Application Factory
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from config import Config
import os


def create_app(config_class=Config):
    """
    Create and configure Flask application.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Flask app instance
    """
    
    app = Flask(__name__, static_folder='../static')
    app.config.from_object(config_class)
    
    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Register blueprints
    from app.routes import api_bp
    app.register_blueprint(api_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not found',
            'message': 'The requested endpoint does not exist'
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'error': 'Method not allowed',
            'message': 'The method is not allowed for the requested URL'
        }), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500
    
    # Root endpoint - serve frontend
    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')
    
    # API info endpoint
    @app.route('/api')
    def api_info():
        return jsonify({
            'service': 'Invoice Generator API',
            'version': '1.0.0',
            'endpoints': {
                'generate_invoice': '/api/generate-invoice [POST]',
                'test_parse': '/api/test-parse [POST]',
                'health': '/api/health [GET]'
            },
            'documentation': 'See README.md for usage instructions'
        })
    
    return app
