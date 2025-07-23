import os
import logging
import mimetypes
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, abort, send_from_directory
from werkzeug.utils import secure_filename
from utils.downloader import TikTokDownloader
import tempfile
import threading
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Initialize TikTok downloader
downloader = TikTokDownloader()

def cleanup_old_files():
    """Background task to cleanup old files"""
    while True:
        try:
            downloader.cleanup_old_files(max_age_hours=1)  # Clean files older than 1 hour
            time.sleep(3600)  # Run every hour
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
            time.sleep(3600)

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

@app.route('/')
def index():
    """Main page with download form"""
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_video():
    """Handle video download requests"""
    try:
        # Get URL from form
        video_url = request.form.get('video_url', '').strip()
        
        if not video_url:
            flash('Please enter a TikTok video URL', 'error')
            return redirect(url_for('index'))
        
        # Validate URL
        if not downloader.is_valid_tiktok_url(video_url):
            flash('Please enter a valid TikTok video URL', 'error')
            return redirect(url_for('index'))
        
        logger.info(f"Download request for URL: {video_url}")
        
        # Download video
        result = downloader.download_video(video_url)
        
        if not result['success']:
            flash(f"Download failed: {result['error']}", 'error')
            return redirect(url_for('index'))
        
        file_path = result['file_path']
        filename = result['filename']
        
        if not os.path.exists(file_path):
            flash('Downloaded file not found', 'error')
            return redirect(url_for('index'))
        
        # Detect MIME type for proper mobile handling
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            # Default to mp4 video type for TikTok videos
            mime_type = 'video/mp4'
        
        # Check if request is from mobile device
        user_agent = request.headers.get('User-Agent', '').lower()
        is_mobile = any(mobile in user_agent for mobile in [
            'android', 'iphone', 'ipad', 'ipod', 'blackberry', 
            'windows phone', 'mobile', 'mobi'
        ])
        
        logger.info(f"Serving file: {filename}, MIME: {mime_type}, Mobile: {is_mobile}")
        
        # Create response with proper headers for mobile downloads
        def generate_response():
            try:
                response = send_file(
                    file_path,
                    mimetype=mime_type,
                    as_attachment=True,
                    download_name=filename
                )
                
                # Essential headers for all downloads
                response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
                response.headers['Content-Type'] = mime_type
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                
                # Mobile-specific headers for better compatibility
                if is_mobile:
                    response.headers['Content-Transfer-Encoding'] = 'binary'
                    response.headers['X-Content-Type-Options'] = 'nosniff'
                    response.headers['Content-Description'] = 'File Transfer'
                    response.headers['Accept-Ranges'] = 'bytes'
                    
                    # Force download behavior on mobile browsers
                    response.headers['Content-Security-Policy'] = "default-src 'none'"
                
                # Schedule file cleanup after response
                def cleanup_file():
                    time.sleep(5)  # Wait 5 seconds before cleanup
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            logger.info(f"Cleaned up file: {filename}")
                    except Exception as e:
                        logger.error(f"Error cleaning up file {filename}: {str(e)}")
                
                cleanup_thread = threading.Thread(target=cleanup_file, daemon=True)
                cleanup_thread.start()
                
                return response
                
            except Exception as e:
                logger.error(f"Error serving file: {str(e)}")
                flash('Error serving download file', 'error')
                return redirect(url_for('index'))
        
        return generate_response()
        
    except Exception as e:
        logger.error(f"Unexpected error in download: {str(e)}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt for search engine crawlers"""
    return send_from_directory('static', 'robots.txt', mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap_xml():
    """Serve sitemap.xml for search engine indexing"""
    return send_from_directory('static', 'sitemap.xml', mimetype='application/xml')

@app.route('/health')
def health_check():
    """Health check endpoint for deployment platforms"""
    return {'status': 'healthy', 'service': 'tiktok-downloader'}, 200

@app.errorhandler(404)
def not_found(error):
    """Custom 404 page"""
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Custom 500 page"""
    logger.error(f"Internal server error: {str(error)}")
    flash('Internal server error. Please try again.', 'error')
    return render_template('index.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
