import os
import sys

# Add the parent directory to the path to import from main backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_migrate import Migrate

# Import from main backend
from config import get_config
from common.database import db
from common.cache import cache
from auth import email_init
from models import *  # Import all models
from models.live_stream import LiveStream, LiveStreamComment, LiveStreamViewer, StreamStatus

# Import live streaming specific routes
from live_streaming_server.routes.live_stream_routes import live_stream_bp
from live_streaming_server.routes.live_stream_websocket_routes import live_stream_ws_bp, init_socketio
from live_streaming_server.routes.youtube_admin_routes import youtube_admin_bp
from live_streaming_server.routes.superadmin_dashboard_routes import superadmin_dashboard_bp
import os
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://kea.mywire.org:5300",
    "https://aoin.scalixity.com"
]

def add_headers(response):
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
    else:
        response.headers['Access-Control-Allow-Origin'] = 'null'

    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRF-Token'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response

def create_live_streaming_app(config_name='default'):
    """Application factory for live streaming server."""
    app = Flask(__name__)
    app.config.from_object(get_config())
    
    # Override port for live streaming server
    app.config['LIVE_STREAMING_PORT'] = int(os.getenv('LIVE_STREAMING_PORT', 5001))
    
    # Configure CORS
    CORS(app, 
         resources={
             r"/api/live-streams/*": {
                 "origins": ALLOWED_ORIGINS,
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"]
             },
             r"/api/superadmin/*": {
                 "origins": ALLOWED_ORIGINS,
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"]
             },
             r"/ws/*": {
                 "origins": ALLOWED_ORIGINS,
                 "methods": ["GET", "POST", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"]
             }
         },
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         max_age=3600)

    # Initialize extensions
    db.init_app(app)
    cache.init_app(app)
    jwt = JWTManager(app)
    email_init.init_app(app)

    # Register blueprints
    app.register_blueprint(live_stream_bp, url_prefix='/api/live-streams')
    app.register_blueprint(live_stream_ws_bp, url_prefix='/ws')
    app.register_blueprint(youtube_admin_bp, url_prefix='/api/live-streams/admin/youtube')
    app.register_blueprint(superadmin_dashboard_bp, url_prefix='/api/superadmin')

    # Add custom headers to every response
    app.after_request(add_headers)

    # Health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'live-streaming-server',
            'database': 'connected' if db.engine.pool.checkedin() > 0 else 'disconnected'
        })

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({'error': 'Internal server error'}), 500

    # After db.init_app(app)
    migrate = Migrate(app, db)

    return app

if __name__ == '__main__':
    app = create_live_streaming_app()
    port = app.config.get('LIVE_STREAMING_PORT', 5001)
    print(f"Live Streaming Server starting on port {port}")
    socketio = init_socketio(app)
    socketio.run(app, host='0.0.0.0', port=port, debug=True) 