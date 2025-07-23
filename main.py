import os
import logging

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)

# Import the Flask app
from app import app

# Ensure the app is properly configured for production
if not app.secret_key or app.secret_key == "dev-secret-key-change-in-production":
    app.secret_key = os.environ.get("SESSION_SECRET", "fallback-secret-key")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
