import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration shared across environments."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key_not_for_production')
    DEBUG = False
    TESTING = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'mysql+mysqlconnector://user:password@localhost/ecommerce_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt_dev_key_not_for_production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)  # Increased from 1 hour to 7 days to reduce token expiration issues during API testing
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_DISCOVERY_URL = 'https://accounts.google.com/.well-known/openid-configuration'

    # Redis Cache
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_TYPE = 'redis'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes

    # Cloudinary
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')
    ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf', 'doc', 'docx']

    MAIL_SERVER = 'smtp.gmail.com'  # Replace with your SMTP server
    MAIL_PORT = 587  # Common ports: 587 (TLS), 465 (SSL)
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = (os.getenv('MAIL_SENDER_NAME', 'shopeasy'), os.getenv('MAIL_USERNAME'))

    FRONTEND_URL = 'http://localhost:5173'

    EXCHANGE_RATE_API_KEY = os.getenv('EXCHANGE_RATE_API_KEY', 'f60545f362ec1fdd1e5e7338')

class DevelopmentConfig(Config):
    """Configuration for development environment."""
    DEBUG = True

class ProductionConfig(Config):
    """Configuration for production environment."""
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI')
    DEBUG = False

# Environment mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Return the configuration class based on FLASK_ENV."""
    env = os.getenv('FLASK_ENV', 'default')
    return config.get(env, config['default'])
