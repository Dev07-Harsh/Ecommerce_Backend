from flask import Flask, jsonify, request,make_response, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from common.cache import cached
import os
from config import get_config
from common.database import db
from common.cache import cache
from auth.routes import auth_bp
from auth.document_route import document_bp
from auth.country_route import country_bp
from api.users.routes import users_bp
from api.merchants.routes import merchants_bp
from auth import email_init
from models import *  # Import all models

from routes.superadmin_routes import superadmin_bp
from routes.merchant_routes import merchant_dashboard_bp
from routes.product_routes import product_bp
from routes.category_routes import category_bp
from routes.brand_routes import brand_bp
from routes.homepage_routes import homepage_bp
from routes.cart_routes import cart_bp
from routes.wishlist_routes import wishlist_bp
from routes.order_routes import order_bp
from routes.user_address_routes import user_address_bp
from routes.currency_routes import currency_bp
from routes.feature_product_routes import feature_product_bp

from routes.promo_product_routes import promo_product_bp
from auth.admin_routes import admin_bp
from routes.payment_card_routes import payment_card_bp

from flasgger import Swagger
from cryptography.fernet import Fernet

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
        response.headers['Access-Control-Allow-Origin'] = 'null'  # or omit completely if strict

    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRF-Token'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = '3600'  # Cache preflight requests for 1 hour
    return response

def create_app(config_name='default'):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(get_config())
    app.config['CARD_ENCRYPTION_KEY'] = Fernet.generate_key()  # Generate a new key

    # Configure Swagger
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs"
    }

    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "Ecommerce Backend API",
            "description": "API documentation for Ecommerce Backend",
            "version": "1.0.0",
            "contact": {
                "email": "Scalixity@gmail.com"
            }
        },
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
            }
        },
        "security": [
            {
                "Bearer": []
            }
        ]
    }

    Swagger(app, config=swagger_config, template=swagger_template)

    # Configure CORS with more specific settings
    CORS(app, 
         resources={
             r"/api/*": {
                 "origins": ALLOWED_ORIGINS,
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"]
             }
         },
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         max_age=3600)  # Cache preflight requests for 1 hour

    # Initialize extensions
    db.init_app(app)
    cache.init_app(app)
    jwt = JWTManager(app)
    email_init.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(merchants_bp, url_prefix='/api/merchants')
    app.register_blueprint(document_bp, url_prefix='/api/merchant/documents')
    app.register_blueprint(superadmin_bp, url_prefix='/api/superadmin')
    app.register_blueprint(merchant_dashboard_bp, url_prefix='/api/merchant-dashboard')
    app.register_blueprint(country_bp)
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(product_bp)
    app.register_blueprint(category_bp, url_prefix='/api/categories')
    app.register_blueprint(brand_bp, url_prefix='/api/brands')
    app.register_blueprint(homepage_bp, url_prefix='/api/homepage')
    app.register_blueprint(cart_bp, url_prefix='/api/cart')
    app.register_blueprint(wishlist_bp, url_prefix='/api/wishlist')
    app.register_blueprint(order_bp, url_prefix='/api/orders')
    app.register_blueprint(user_address_bp, url_prefix='/api/user-address')
    app.register_blueprint(currency_bp)
    app.register_blueprint(feature_product_bp, url_prefix='/api/featured-products')
    app.register_blueprint(promo_product_bp, url_prefix='/api/promo-products')
    app.register_blueprint(payment_card_bp)
    # Add custom headers to every response
    app.after_request(add_headers)

   

    # Test Redis cache endpoint
    @app.route('/api/test-cache')
    @cached(timeout=30)
    def test_cache():
        import time
        time.sleep(2)
        return jsonify({
            'message': 'This response is cached for 30 seconds',
            'timestamp': time.time()
        })

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(error):
        return {"error": "Internal server error"}, 500

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=5110)
