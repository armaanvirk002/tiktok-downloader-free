#!/usr/bin/env python3
"""
WSGI entry point for TikTok Downloader Flask application
This file is used by Gunicorn to start the application
"""

import os
import sys
import logging

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

try:
    # Import the Flask application
    from app import app as application
    
    # Ensure proper configuration
    if not application.secret_key or application.secret_key == "dev-secret-key-change-in-production":
        application.secret_key = os.environ.get("SESSION_SECRET", "fallback-secret-key")
    
    logging.info("TikTok Downloader WSGI application loaded successfully")
    
except Exception as e:
    logging.error(f"Failed to load application: {e}")
    raise

# Make sure we expose the application object
app = application

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port, debug=False)