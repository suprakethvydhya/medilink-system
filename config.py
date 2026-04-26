"""
MediLink Configuration Module
Centralized configuration management for the application.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration class."""

    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("FLASK_SECRET_KEY must be set in environment")

    # Database
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'medilink')
    DB_PORT = int(os.getenv('DB_PORT', 3306))

    # Session
    SESSION_COOKIE_NAME = 'medilink_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set True in production with HTTPS
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

    # Application
    LOW_STOCK_THRESHOLD = 10
    MAX_PAGE_SIZE = 100
    DEFAULT_PAGE_SIZE = 10
    MAX_APPOINTMENTS_PER_DAY = 3

    # File upload (if needed in future)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

    @classmethod
    def get_database_uri(cls):
        """Construct MySQL database URI."""
        return (
            f"mysql+pymysql://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    DB_NAME = 'medilink_test'


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
