"""
MediTrust API Endpoints
Complete API implementation for MediTrust platform with all features
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import logging
from datetime import datetime, timedelta
from functools import wraps
import jwt

# Import MediTrust modules
from verification.meditrust_verification import MediTrustVerificationEngine
from campaigns.meditrust_campaign_manager import MediTrustCampaignManager
from hms.meditrust_hms import MediTrustHMS
from admin.meditrust_admin import MediTrustAdminManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'webp'}

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'medical_crowdfunding')

try:
    from pymongo import MongoClient
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client[DB_NAME]
    # Test connection
    mongo_client.server_info()
    logger.info(f"Connected to MongoDB: {DB_NAME}")
except Exception as e:
    logger.warning(f"MongoDB connection failed: {e}. Running without database.")
    db = None

# Initialize MediTrust components
verification_engine = MediTrustVerificationEngine()
campaign_manager = MediTrustCampaignManager(db)
hms_service = MediTrustHMS()
admin_manager = MediTrustAdminManager(db)

# JWT Secret
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'meditrust-secret-key')

# ==================== AUTHENTICATION MIDDLEWARE ====================

def verify_admin_token(f):
    """Middleware to verify admin JWT token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'error': 'Token required'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        verification = admin_manager.verify_admin_token(token)
        if not verification['valid']:
            return jsonify({'success': False, 'error': verification['error']}), 401
        
        request.admin = verification['admin']
        return f(*args, **kwargs)
    return decorated_function

def verify_user_token(f):
    """Middleware to verify user JWT token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'error': 'Token required'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            request.user = payload
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
    return decorated_function

# ==================== USER AUTHENTICATION ENDPOINTS ====================

@app.route('/api/auth/register', methods=['POST'])
def user_register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        user_type = data.get('user_type', 'patient')
        profile_data = data.get('profile_data', {})
        
        # Basic validation
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400
        
        if password != confirm_password:
            return jsonify({'success': False, 'error': 'Passwords do not match'}), 400
        
        # Password strength validation
        if len(password) < 8:
            return jsonify({'success': False, 'error': 'Password must be at least 8 characters'}), 400
        
        # For now, create a simple user without database
        user_id = f"user_{datetime.utcnow().timestamp()}"
        
        # Generate JWT token
        token = jwt.encode(
            {
                'user_id': user_id,
                'email': email,
                'user_type': user_type,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(hours=24)
            },
            JWT_SECRET_KEY,
            algorithm='HS256'
        )
        
        return jsonify({
            'success': True,
            'user': {
                'user_id': user_id,
                'email': email,
                'user_type': user_type,
                **profile_data
            },
            'token': token,
            'message': 'Registration successful'
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'success': False, 'error': 'Registration failed'}), 500

@app.route('/api/auth/login', methods=['POST'])
def user_login():
    """User login endpoint"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400
        
        # For now, simple login without database
        user_id = f"user_{datetime.utcnow().timestamp()}"
        
        # Generate JWT token
        token = jwt.encode(
            {
                'user_id': user_id,
                'email': email,
                'user_type': 'patient',
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(hours=24)
            },
            JWT_SECRET_KEY,
            algorithm='HS256'
        )
        
        return jsonify({
            'success': True,
            'user': {
                'user_id': user_id,
                'email': email,
                'user_type': 'patient'
            },
            'token': token,
            'message': 'Login successful'
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'error': 'Login failed'}), 500

# ==================== ADMIN ENDPOINTS ====================

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        secret_key = data.get('secret_key')  # Optional second layer
        
        result = admin_manager.admin_login(username, password, secret_key)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        logger.error(f"Admin login error: {e}")
        return jsonify({'success': False, 'error': 'Login failed'}), 500

@app.route('/api/admin/dashboard', methods=['GET'])
@verify_admin_token
def admin_dashboard():
    """Get admin dashboard data"""
    try:
        result = admin_manager.get_admin_dashboard()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Admin dashboard error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get dashboard'}), 500

@app.route('/api/admin/pending-verifications', methods=['GET'])
@verify_admin_token
def pending_verifications():
    """Get pending verifications"""
    try:
        result = admin_manager.get_pending_verifications()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Pending verifications error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get pending verifications'}), 500

@app.route('/api/admin/approve-verification', methods=['POST'])
@verify_admin_token
def approve_verification():
    """Approve pending verification"""
    try:
        data = request.get_json()
        campaign_id = data.get('campaign_id')
        notes = data.get('notes', '')
        
        result = admin_manager.approve_verification(
            campaign_id, 
            request.admin['admin_id'], 
            notes
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Verification approval error: {e}")
        return jsonify({'success': False, 'error': 'Failed to approve verification'}), 500

@app.route('/api/admin/cancel-verification', methods=['POST'])
@verify_admin_token
def cancel_verification():
    """Cancel pending verification"""
    try:
        data = request.get_json()
        campaign_id = data.get('campaign_id')
        reason = data.get('reason')
        notes = data.get('notes', '')
        
        result = admin_manager.cancel_verification(
            campaign_id, 
            request.admin['admin_id'], 
            reason, 
            notes
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Verification cancellation error: {e}")
        return jsonify({'success': False, 'error': 'Failed to cancel verification'}), 500

# ==================== CAMPAIGN ENDPOINTS ====================

@app.route('/api/campaigns/create-draft', methods=['POST'])
@verify_user_token
def create_campaign_draft():
    """Create campaign draft"""
    try:
        data = request.get_json()
        patient_id = request.user['user_id']
        
        result = campaign_manager.create_campaign_draft(patient_id, data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Campaign draft creation error: {e}")
        return jsonify({'success': False, 'error': 'Failed to create campaign draft'}), 500

@app.route('/api/campaigns/submit-documents', methods=['POST'])
@verify_user_token
def submit_documents():
    """Submit documents for verification"""
    try:
        data = request.get_json()
        campaign_id = data.get('campaign_id')
        documents = data.get('documents', [])
        
        result = campaign_manager.submit_documents_for_verification(campaign_id, documents)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Document submission error: {e}")
        return jsonify({'success': False, 'error': 'Failed to submit documents'}), 500

@app.route('/api/campaigns/submit-story', methods=['POST'])
@verify_user_token
def submit_story():
    """Submit story for Gemini polishing"""
    try:
        data = request.get_json()
        campaign_id = data.get('campaign_id')
        original_story = data.get('story')
        language = data.get('language', 'en')
        
        result = campaign_manager.submit_story_for_gemini_polishing(
            campaign_id, original_story, language
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Story submission error: {e}")
        return jsonify({'success': False, 'error': 'Failed to submit story'}), 500

@app.route('/api/campaigns/approve-story', methods=['POST'])
@verify_user_token
def approve_story():
    """Approve story and go live"""
    try:
        data = request.get_json()
        campaign_id = data.get('campaign_id')
        target_amount = data.get('target_amount')
        hospital_name = data.get('hospital_name')
        hospital_address = data.get('hospital_address')
        
        result = campaign_manager.approve_story_and_go_live(
            campaign_id, target_amount, hospital_name, hospital_address
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Story approval error: {e}")
        return jsonify({'success': False, 'error': 'Failed to approve story'}), 500

@app.route('/api/campaigns/donate', methods=['POST'])
@verify_user_token
def process_donation():
    """Process donation"""
    try:
        data = request.get_json()
        campaign_id = data.get('campaign_id')
        amount = data.get('amount')
        anonymous = data.get('anonymous', False)
        donor_id = request.user['user_id']
        
        result = campaign_manager.process_donation(
            campaign_id, donor_id, amount, anonymous
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Donation processing error: {e}")
        return jsonify({'success': False, 'error': 'Failed to process donation'}), 500

@app.route('/api/campaigns/live', methods=['GET'])
def get_live_campaigns():
    """Get all live campaigns"""
    try:
        limit = request.args.get('limit', 50, type=int)
        campaigns = campaign_manager.get_live_campaigns(limit)
        
        return jsonify({
            'success': True,
            'campaigns': campaigns,
            'count': len(campaigns)
        }), 200
        
    except Exception as e:
        logger.error(f"Live campaigns fetch error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get live campaigns'}), 500

@app.route('/api/campaigns/<campaign_id>', methods=['GET'])
def get_campaign_details(campaign_id):
    """Get campaign details"""
    try:
        result = campaign_manager.get_campaign_details(campaign_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Campaign details fetch error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get campaign details'}), 500

@app.route('/api/campaigns/<campaign_id>/dashboard', methods=['GET'])
@verify_user_token
def get_campaign_dashboard(campaign_id):
    """Get campaign dashboard for owner"""
    try:
        result = campaign_manager.get_campaign_dashboard_data(campaign_id)
        
        if result['success']:
            # Verify user owns this campaign
            campaign = result['campaign']
            if campaign.get('patient_id') == request.user['user_id']:
                return jsonify(result), 200
            else:
                return jsonify({'success': False, 'error': 'Access denied'}), 403
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Dashboard fetch error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get dashboard data'}), 500

@app.route('/api/campaigns/<campaign_id>/hospital-change', methods=['POST'])
@verify_user_token
def request_hospital_change():
    """Request hospital change"""
    try:
        data = request.get_json()
        campaign_id = data.get('campaign_id')
        new_hospital_data = data.get('new_hospital_data')
        
        result = campaign_manager.request_hospital_change(campaign_id, new_hospital_data)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Hospital change request error: {e}")
        return jsonify({'success': False, 'error': 'Failed to request hospital change'}), 500

# ==================== HMS ENDPOINTS ====================

@app.route('/api/hms/patients', methods=['POST'])
def create_patient():
    """Create patient in HMS"""
    try:
        data = request.get_json()
        result = hms_service.create_patient(data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Patient creation error: {e}")
        return jsonify({'success': False, 'error': 'Failed to create patient'}), 500

@app.route('/api/hms/patients/<patient_id>/outstanding', methods=['GET'])
def get_patient_outstanding(patient_id):
    """Get patient outstanding amount"""
    try:
        result = hms_service.get_patient_outstanding_amount(patient_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Outstanding amount fetch error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get outstanding amount'}), 500

@app.route('/api/hms/patients/<patient_id>/status', methods=['GET'])
def get_patient_status(patient_id):
    """Get patient status"""
    try:
        result = hms_service.get_patient_status(patient_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Patient status fetch error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get patient status'}), 500

@app.route('/api/hms/patients/<patient_id>/discharge', methods=['PUT'])
def discharge_patient(patient_id):
    """Discharge patient"""
    try:
        data = request.get_json()
        result = hms_service.discharge_patient(patient_id, data)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Patient discharge error: {e}")
        return jsonify({'success': False, 'error': 'Failed to discharge patient'}), 500

@app.route('/api/hms/patients/<patient_id>/hospital', methods=['PUT'])
def update_patient_hospital(patient_id):
    """Update patient hospital"""
    try:
        data = request.get_json()
        new_hospital = data.get('hospital_name')
        new_estimate = data.get('new_estimate')
        
        result = hms_service.update_patient_hospital(
            patient_id, new_hospital, new_estimate
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Hospital update error: {e}")
        return jsonify({'success': False, 'error': 'Failed to update hospital'}), 500

@app.route('/api/hms/payments', methods=['POST'])
def record_payment():
    """Record payment in HMS"""
    try:
        data = request.get_json()
        result = hms_service.record_payment(data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Payment recording error: {e}")
        return jsonify({'success': False, 'error': 'Failed to record payment'}), 500

# ==================== VERIFICATION ENDPOINTS ====================

@app.route('/api/verification/verify-documents', methods=['POST'])
def verify_documents():
    """Verify documents using AI engine"""
    try:
        data = request.get_json()
        documents = data.get('documents', [])
        
        result = verification_engine.verify_multiple_documents(documents)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Document verification error: {e}")
        return jsonify({'success': False, 'error': 'Failed to verify documents'}), 500

# ==================== NOTIFICATION ENDPOINTS ====================

@app.route('/notify/ngo-match', methods=['POST'])
def notify_ngo_match():
    """Receive NGO match notifications from Node.js backend"""
    try:
        data = request.get_json()
        logger.info(f"NGO match notification received: {data}")
        
        # Forward to notification manager
        from notifications.notification_manager import NotificationManager
        notification_manager = NotificationManager()
        
        result = notification_manager.send_ngo_match_email(
            to_email=data.get('to_email'),
            ngo_name=data.get('ngo_name'),
            campaign_title=data.get('campaign_title'),
            patient_name=data.get('patient_name'),
            disease=data.get('disease'),
            hospital_name=data.get('hospital_name'),
            hospital_city=data.get('hospital_city'),
            documents_url=data.get('documents_url')
        )
        
        return jsonify({'success': True, 'message': result})
        
    except Exception as e:
        logger.error(f"NGO match notification error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/notify/donation-receipt', methods=['POST'])
def notify_donation_receipt():
    """Receive donation receipt notifications from Node.js backend"""
    try:
        data = request.get_json()
        logger.info(f"Donation receipt notification received: {data}")
        
        # Forward to notification manager
        from notifications.notification_manager import NotificationManager
        notification_manager = NotificationManager()
        
        result = notification_manager.send_donation_receipt_email(
            to_email=data.get('to_email'),
            donor_name=data.get('donor_name'),
            amount=data.get('amount'),
            campaign_title=data.get('campaign_title'),
            patient_name=data.get('patient_name')
        )
        
        return jsonify({'success': True, 'message': result})
        
    except Exception as e:
        logger.error(f"Donation receipt notification error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/notify/custom-email', methods=['POST'])
def notify_custom_email():
    """Send admin-composed custom email to NGO"""
    try:
        data    = request.get_json()
        to_email= data.get('to_email', '')
        subject = data.get('subject', 'MediTrust NGO Support Request')
        body    = data.get('body', '')
        ngo_name= data.get('ngo_name', '')

        if not to_email or not body:
            return jsonify({'success':False, 'error':'to_email and body required'}), 400

        # Get notification manager
        from notifications.notification_manager import NotificationManager
        notification_manager = NotificationManager()
        
        # Send custom email
        result = notification_manager.send_custom_email(
            to_email=to_email,
            subject=subject,
            body=body,
            ngo_name=ngo_name
        )
        
        return jsonify({'success': result})

    except Exception as e:
        logger.error(f"notify_custom_email error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== STATIC FILES ====================

@app.route('/')
def index():
    """Serve main crowdfunding page"""
    return send_from_directory('public', 'crowdfunding.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('public', filename)

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    logger.info("Starting MediTrust Platform API")
    logger.info("Upload folder: %s", app.config['UPLOAD_FOLDER'])
    
    # Create upload directory if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    app.run(host='0.0.0.0', port=5000, debug=True)
