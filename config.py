import os

class Config:
    # Get SECRET_KEY from environment variable. It MUST be set.
    SECRET_KEY = os.environ.get('SECRET_KEY') 
    if not SECRET_KEY:
        raise ValueError("No SECRET_KEY set for Flask application. Please set it in your .env file or environment variables.")

    # Get MONGO_URI from environment variable. It MUST be set.
    MONGO_URI = os.environ.get('MONGO_URI')
    if not MONGO_URI:
        raise ValueError("No MONGO_URI set for MongoDB connection. Please set it in your .env file or environment variables.")

    # You can add other configurations here, like:
    # FLASK_ENV = os.environ.get('FLASK_ENV') or 'development'
    # DEBUG = True # Or False for production