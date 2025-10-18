import os

# API Keys and Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'your-gemini-api-key-here')

# Flask Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# File Upload Configuration
MAX_CONTENT_LENGTH = None  # No file size limit
ALLOWED_EXTENSIONS = {'csv'}

# Directory Configuration (will be set in app.py)
UPLOAD_FOLDER = None
STATIC_FOLDER = None
IMAGES_FOLDER = None
TEMPLATES_FOLDER = None
