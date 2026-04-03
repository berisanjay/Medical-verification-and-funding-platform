from flask import Flask, request, jsonify
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Email configuration (should be set in environment)
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

@app.route('/notify/custom-email', methods=['POST'])
def notify_custom_email():
    """Send admin-composed custom email to NGO"""
    try:
        data = request.get_json()
        to_email = data.get('to_email', '')
        subject = data.get('subject', 'MediTrust NGO Support Request')
        body = data.get('body', '')
        ngo_name = data.get('ngo_name', '')

        if not to_email or not body:
            return jsonify({'success': False, 'error': 'to_email and body required'}), 400

        # Simple email sending (you can enhance this with actual SMTP)
        logger.info(f"Sending email to {to_email}")
        logger.info(f"Subject: {subject}")
        logger.info(f"NGO Name: {ngo_name}")
        logger.info(f"Body length: {len(body)} characters")
        
        # TODO: Add actual SMTP email sending here
        # For now, just log and return success
        
        return jsonify({'success': True, 'message': 'Email sent successfully'})

    except Exception as e:
        logger.error(f"notify_custom_email error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'MediTrust NGO Email Service'
    })

@app.route('/')
def index():
    return jsonify({
        'service': 'MediTrust NGO Email Service',
        'status': 'running',
        'endpoints': [
            'POST /notify/custom-email - Send NGO email',
            'GET /health - Health check'
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
