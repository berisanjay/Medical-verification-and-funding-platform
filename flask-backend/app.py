"""
Medical Document Verification API
Flask backend for OCR, NLP, and fraud detection
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import logging
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import traceback

# Import custom modules
from nlp.entity_extractor import MedicalEntityExtractor
from nlp.bert_authenticator import BERTDocumentAuthenticator
from ocr.pdf_ocr import DocumentOCR
from validation.cross_document import CrossDocumentValidator
from auth.auth_manager import AuthManager
from campaigns.campaign_manager import CampaignManager
from donations.donation_manager import DonationManager
from notifications.notification_manager import NotificationManager
from automation.fulfillment_manager import CampaignFulfillmentManager
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'webp'}

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'medical_crowdfunding')

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client[DB_NAME]
    # Test connection
    mongo_client.server_info()
    logger.info(f"Connected to MongoDB: {DB_NAME}")
except Exception as e:
    logger.warning(f"MongoDB connection failed: {e}. Running without database.")
    db = None

# Initialize components
ocr_processor = DocumentOCR()
entity_extractor = MedicalEntityExtractor()
bert_authenticator = BERTDocumentAuthenticator()
validator = CrossDocumentValidator()
auth_manager = AuthManager(db)
campaign_manager = CampaignManager(db)
donation_manager = DonationManager(db)
notification_manager = NotificationManager(db)
fulfillment_manager = CampaignFulfillmentManager(campaign_manager, notification_manager)

# Initialize JWT
jwt = JWTManager(app)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def save_to_database(verification_result):
    """Save verification result to MongoDB"""
    if db is None:
        logger.warning("Database not available, skipping save")
        return None
    
    try:
        collection = db.verifications
        
        # Add metadata
        verification_result['created_at'] = datetime.utcnow()
        verification_result['updated_at'] = datetime.utcnow()
        
        # Insert document
        result = collection.insert_one(verification_result)
        logger.info(f"Saved verification to database: {result.inserted_id}")
        
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Database save error: {e}")
        return None


def get_verification_by_id(verification_id):
    """Retrieve verification result from MongoDB"""
    if db is None:
        return None
    
    try:
        collection = db.verifications
        result = collection.find_one({'_id': ObjectId(verification_id)})
        
        if result:
            # Convert ObjectId to string for JSON serialization
            result['_id'] = str(result['_id'])
            return result
        return None
    except Exception as e:
        logger.error(f"Database retrieval error: {e}")
        return None


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'ocr': 'available',
            'nlp': 'available',
            'database': 'available' if db is not None else 'unavailable'
        }
    })


@app.route('/verify', methods=['POST'])
def verify_documents():
    """
    Main verification endpoint
    Accepts multiple document files and performs complete verification
    """
    try:
        # Check if files are present
        if 'files' not in request.files:
            return jsonify({
                'error': 'No files provided',
                'message': 'Please upload at least one document'
            }), 400
        
        files = request.files.getlist('files')
        
        if not files or len(files) == 0:
            return jsonify({
                'error': 'Empty file list',
                'message': 'Please upload at least one document'
            }), 400
        
        logger.info(f"Processing {len(files)} documents")
        
        # Process each document
        processed_documents = []
        all_extracted_data = []
        
        for idx, file in enumerate(files):
            if file and allowed_file(file.filename):
                try:
                    # Save file temporarily
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_{idx}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    
                    logger.info(f"Processing document: {filename}")
                    
                    # Step 1: OCR - Extract text from document
                    extracted_text = ocr_processor.extract_text(filepath)
                    
                    if not extracted_text or len(extracted_text.strip()) < 10:
                        logger.warning(f"Insufficient text extracted from {filename}")
                        processed_documents.append({
                            'filename': filename,
                            'status': 'FAILED',
                            'error': 'Unable to extract text from document',
                            'entities': {},
                            'issues': ['No readable text found in document']
                        })
                        # Clean up
                        os.remove(filepath)
                        continue
                    
                    # Step 2: NLP - Extract medical entities
                    entities = entity_extractor.extract_entities(extracted_text)
                    
                    # Step 3: Determine document type based on content
                    document_type = determine_document_type(extracted_text, entities)
                    
                    # Step 4: Validate mandatory fields
                    issues = validate_mandatory_fields(entities)
                    
                    # Store extracted data for cross-document validation
                    doc_data = {
                        'filename': filename,
                        'document_type': document_type,
                        'entities': entities,
                        'issues': issues,
                        'raw_text': extracted_text[:500]  # Store snippet for debugging
                    }
                    
                    all_extracted_data.append(doc_data)
                    processed_documents.append(doc_data)
                    
                    # Clean up uploaded file
                    os.remove(filepath)
                    
                except Exception as e:
                    logger.error(f"Error processing {file.filename}: {str(e)}")
                    logger.error(traceback.format_exc())
                    processed_documents.append({
                        'filename': file.filename,
                        'status': 'FAILED',
                        'error': str(e),
                        'entities': {},
                        'issues': [f'Processing error: {str(e)}']
                    })
            else:
                logger.warning(f"Invalid file: {file.filename}")
                processed_documents.append({
                    'filename': file.filename,
                    'status': 'FAILED',
                    'error': 'Invalid file type',
                    'entities': {},
                    'issues': ['Only PDF, PNG, JPG, JPEG, WEBP files are allowed']
                })
        
        # Step 5: Cross-document validation
        cross_document_issues = validator.validate_documents(all_extracted_data)
        
        # Step 6: Calculate final risk score and status
        final_status, risk_score = calculate_final_status(
            processed_documents, 
            cross_document_issues
        )
        
        # Prepare final response
        verification_result = {
            'final_status': final_status,
            'risk_score': risk_score,
            'total_documents': len(files),
            'processed_documents': len(processed_documents),
            'cross_document_issues': cross_document_issues,
            'documents': processed_documents,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Save to database
        verification_id = save_to_database(verification_result.copy())
        if verification_id:
            verification_result['verification_id'] = verification_id
        
        logger.info(f"Verification complete: {final_status}")
        
        return jsonify(verification_result), 200
        
    except Exception as e:
        logger.error(f"Verification error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@app.route('/verification/<verification_id>', methods=['GET'])
def get_verification(verification_id):
    """Retrieve a past verification by ID"""
    try:
        result = get_verification_by_id(verification_id)
        
        if result:
            return jsonify(result), 200
        else:
            return jsonify({
                'error': 'Not found',
                'message': 'Verification record not found'
            }), 404
    except Exception as e:
        logger.error(f"Retrieval error: {str(e)}")
        return jsonify({
            'error': 'Invalid ID',
            'message': str(e)
        }), 400


@app.route('/verifications', methods=['GET'])
def list_verifications():
    """List all verifications with pagination"""
    if db is None:
        return jsonify({
            'error': 'Database unavailable',
            'message': 'Database is not connected'
        }), 503
    
    try:
        # Pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit
        
        collection = db.verifications
        
        # Get total count
        total = collection.count_documents({})
        
        # Get paginated results
        results = list(collection.find()
                      .sort('created_at', -1)
                      .skip(skip)
                      .limit(limit))
        
        # Convert ObjectId to string
        for result in results:
            result['_id'] = str(result['_id'])
        
        return jsonify({
            'total': total,
            'page': page,
            'limit': limit,
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"List error: {str(e)}")
        return jsonify({
            'error': 'Internal error',
            'message': str(e)
        }), 500


def determine_document_type(text, entities):
    """Determine the type of medical document"""
    text_lower = text.lower()
    
    if 'estimate' in text_lower or 'estimated' in text_lower:
        return 'ESTIMATE'
    elif 'bill' in text_lower or 'invoice' in text_lower or 'payable' in text_lower:
        return 'BILL'
    elif 'prescription' in text_lower:
        return 'PRESCRIPTION'
    elif 'discharge' in text_lower or 'summary' in text_lower:
        return 'DISCHARGE_SUMMARY'
    elif 'report' in text_lower or 'test' in text_lower:
        return 'MEDICAL_REPORT'
    else:
        return 'UNKNOWN'


def validate_mandatory_fields(entities):
    """Validate that mandatory fields are present"""
    issues = []
    
    mandatory_fields = {
        'patient_name': 'Patient name',
        'diseases': 'Disease/Diagnosis',
        'date': 'Date',
        'amount': 'Amount'
    }
    
    for field, label in mandatory_fields.items():
        if field not in entities or not entities[field]:
            issues.append(f"Missing mandatory field: {label}")
        elif field == 'diseases' and len(entities[field]) == 0:
            issues.append(f"Missing mandatory field: {label}")
    
    # At least hospital name OR pincode required
    if not entities.get('hospital_name') and not entities.get('hospital_pincode'):
        issues.append("Missing mandatory field: Hospital name or pincode")
    
    return issues


def calculate_final_status(documents, cross_document_issues):
    """
    Calculate final verification status and risk score
    
    Returns: (status, risk_score)
    Status: VERIFIED, NEEDS_CLARIFICATION, HIGH_RISK
    Risk Score: 0-100
    """
    risk_score = 0
    
    # Check for documents with issues
    docs_with_issues = sum(1 for doc in documents if len(doc.get('issues', [])) > 0)
    failed_docs = sum(1 for doc in documents if doc.get('status') == 'FAILED')
    
    # Risk scoring
    if failed_docs > 0:
        risk_score += failed_docs * 20
    
    if docs_with_issues > 0:
        risk_score += docs_with_issues * 15
    
    if len(cross_document_issues) > 0:
        risk_score += len(cross_document_issues) * 10
        
        # High severity issues
        for issue in cross_document_issues:
            if 'patient name mismatch' in issue.lower():
                risk_score += 30
            elif 'conflicting dates' in issue.lower():
                risk_score += 20
            elif 'missing hospital' in issue.lower():
                risk_score += 15
    
    # Cap at 100
    risk_score = min(risk_score, 100)
    
    # Determine status
    if risk_score >= 70:
        status = 'HIGH_RISK'
    elif risk_score >= 30:
        status = 'NEEDS_CLARIFICATION'
    else:
        status = 'VERIFIED'
    
    return status, risk_score


# ==================== CROWDFUNDING API ENDPOINTS ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'user_type', 'confirm_password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
        
        # Validate passwords match
        if data.get('password') != data.get('confirm_password'):
            return jsonify({'success': False, 'error': 'Passwords do not match'}), 400
        
        result = auth_manager.register_user(
            email=data.get('email'),
            password=data.get('password'),
            user_type=data.get('user_type'),
            profile_data=data.get('profile_data', {})
        )
        return jsonify(result), 201 if result['success'] else 400
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'success': False, 'error': 'Registration failed'}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        result = auth_manager.login_user(
            email=data.get('email'),
            password=data.get('password')
        )
        return jsonify(result), 200 if result['success'] else 401
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'error': 'Login failed'}), 500


@app.route('/api/campaigns/create', methods=['POST'])
@jwt_required()
def create_campaign():
    """Create new campaign"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        result = campaign_manager.create_campaign(
            patient_id=user_id,
            campaign_data=data,
            verification_id=data.get('verification_id')
        )
        return jsonify(result), 201 if result['success'] else 400
    except Exception as e:
        logger.error(f"Campaign creation error: {e}")
        return jsonify({'success': False, 'error': 'Campaign creation failed'}), 500


@app.route('/api/campaigns/active', methods=['GET'])
def get_active_campaigns():
    """Get all active campaigns"""
    try:
        limit = int(request.args.get('limit', 20))
        campaigns = campaign_manager.get_active_campaigns(limit=limit)
        return jsonify(campaigns), 200
    except Exception as e:
        logger.error(f"Error getting active campaigns: {e}")
        return jsonify([]), 500


@app.route('/api/campaigns/search', methods=['GET'])
def search_campaigns():
    """Search campaigns"""
    try:
        query = request.args.get('q', '')
        urgency = request.args.get('urgency', '')
        limit = int(request.args.get('limit', 20))
        
        campaigns = campaign_manager.search_campaigns(query, limit)
        
        # Filter by urgency if specified
        if urgency:
            campaigns = [c for c in campaigns if c.get('urgency_level') == urgency]
        
        return jsonify(campaigns), 200
    except Exception as e:
        logger.error(f"Error searching campaigns: {e}")
        return jsonify([]), 500


@app.route('/api/campaigns/<campaign_id>', methods=['GET'])
def get_campaign(campaign_id):
    """Get specific campaign details"""
    try:
        campaign = campaign_manager.get_campaign(campaign_id)
        if campaign:
            return jsonify(campaign), 200
        else:
            return jsonify({'error': 'Campaign not found'}), 404
    except Exception as e:
        logger.error(f"Error getting campaign: {e}")
        return jsonify({'error': 'Failed to get campaign'}), 500


@app.route('/api/donations/create', methods=['POST'])
@jwt_required()
def create_donation():
    """Create donation"""
    try:
        data = request.get_json()
        donor_id = get_jwt_identity()
        
        result = donation_manager.create_donation(
            donor_id=donor_id,
            campaign_id=data.get('campaign_id'),
            amount=data.get('amount'),
            payment_method_id=data.get('payment_method_id'),
            anonymous=data.get('anonymous', False)
        )
        return jsonify(result), 201 if result['success'] else 400
    except Exception as e:
        logger.error(f"Donation creation error: {e}")
        return jsonify({'success': False, 'error': 'Donation failed'}), 500


@app.route('/api/donations/history/<donor_id>', methods=['GET'])
@jwt_required()
def get_donation_history(donor_id):
    """Get donor's donation history"""
    try:
        current_user_id = get_jwt_identity()
        # Users can only see their own donation history
        if current_user_id != donor_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        donations = donation_manager.get_donor_donations(donor_id)
        return jsonify(donations), 200
    except Exception as e:
        logger.error(f"Error getting donation history: {e}")
        return jsonify([]), 500


@app.route('/api/campaigns/<campaign_id>/donations', methods=['GET'])
def get_campaign_donations(campaign_id):
    """Get donations for a specific campaign"""
    try:
        donations = donation_manager.get_campaign_donations(campaign_id)
        return jsonify(donations), 200
    except Exception as e:
        logger.error(f"Error getting campaign donations: {e}")
        return jsonify([]), 500


@app.route('/api/verify-enhanced', methods=['POST'])
def verify_documents_enhanced():
    """Enhanced verification with BERT"""
    try:
        # Check if files are present
        if 'files' not in request.files:
            return jsonify({
                'error': 'No files provided',
                'message': 'Please upload at least one document'
            }), 400
        
        files = request.files.getlist('files')
        
        if not files or len(files) == 0:
            return jsonify({
                'error': 'Empty file list',
                'message': 'Please upload at least one document'
            }), 400
        
        logger.info(f"Processing {len(files)} documents with enhanced verification")
        
        # Process each document
        processed_documents = []
        all_extracted_data = []
        
        for idx, file in enumerate(files):
            if file and allowed_file(file.filename):
                try:
                    # Save file temporarily
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_{idx}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    
                    logger.info(f"Processing document: {filename}")
                    
                    # Step 1: OCR - Extract text from document
                    extracted_text = ocr_processor.extract_text(filepath)
                    
                    if not extracted_text or len(extracted_text.strip()) < 10:
                        logger.warning(f"Insufficient text extracted from {filename}")
                        processed_documents.append({
                            'filename': filename,
                            'status': 'FAILED',
                            'error': 'Unable to extract text from document',
                            'entities': {},
                            'issues': ['No readable text found in document']
                        })
                        os.remove(filepath)
                        continue
                    
                    # Step 2: NLP - Extract medical entities
                    entities = entity_extractor.extract_entities(extracted_text)
                    
                    # Step 3: BERT - Document authenticity
                    authenticity = bert_authenticator.predict_authenticity(extracted_text, entities)
                    
                    # Step 4: Determine document type
                    document_type = determine_document_type(extracted_text, entities)
                    
                    # Step 5: Validate mandatory fields
                    issues = validate_mandatory_fields(entities)
                    
                    # Add authenticity check to issues
                    if authenticity['prediction'] == 'FORGED':
                        issues.append(f"Document appears to be forged (confidence: {authenticity['confidence']:.2f})")
                    
                    # Store extracted data
                    doc_data = {
                        'filename': filename,
                        'document_type': document_type,
                        'entities': entities,
                        'authenticity': authenticity,
                        'issues': issues,
                        'raw_text': extracted_text[:500]
                    }
                    
                    all_extracted_data.append(doc_data)
                    processed_documents.append(doc_data)
                    
                    # Clean up uploaded file
                    os.remove(filepath)
                    
                except Exception as e:
                    logger.error(f"Error processing {file.filename}: {e}")
                    processed_documents.append({
                        'filename': file.filename,
                        'status': 'FAILED',
                        'error': str(e),
                        'entities': {},
                        'issues': ['Processing error']
                    })
        
        # Step 6: Cross-document validation
        cross_document_issues = validator.validate_documents(all_extracted_data)
        
        # Step 7: Calculate final status and risk score
        final_status, risk_score = calculate_final_status(processed_documents, cross_document_issues)
        
        # Step 8: Prepare response
        verification_result = {
            'final_status': final_status,
            'risk_score': risk_score,
            'total_documents': len(files),
            'processed_documents': len(processed_documents),
            'cross_document_issues': cross_document_issues,
            'documents': processed_documents,
            'enhanced_verification': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Step 9: Save to database
        verification_id = save_to_database(verification_result)
        if verification_id:
            verification_result['verification_id'] = verification_id
        
        return jsonify(verification_result), 200
        
    except Exception as e:
        logger.error(f"Enhanced verification error: {e}")
        return jsonify({
            'error': 'Verification failed',
            'message': str(e)
        }), 500


@app.route('/api/admin/fulfillment/start', methods=['POST'])
@jwt_required()
def start_fulfillment_monitoring():
    """Start campaign fulfillment monitoring (admin only)"""
    try:
        user_id = get_jwt_identity()
        # Check if user is admin (you'd implement proper admin check)
        user = auth_manager.users_collection.find_one({"_id": ObjectId(user_id)})
        if not user or user.get("user_type") != "admin":
            return jsonify({'error': 'Admin access required'}), 403
        
        fulfillment_manager.start_monitoring()
        return jsonify({'success': True, 'message': 'Fulfillment monitoring started'}), 200
    except Exception as e:
        logger.error(f"Error starting fulfillment monitoring: {e}")
        return jsonify({'error': 'Failed to start monitoring'}), 500


@app.route('/api/admin/fulfillment/check/<campaign_id>', methods=['POST'])
@jwt_required()
def check_campaign_fulfillment(campaign_id):
    """Manually check campaign fulfillment (admin only)"""
    try:
        user_id = get_jwt_identity()
        # Check if user is admin
        user = auth_manager.users_collection.find_one({"_id": ObjectId(user_id)})
        if not user or user.get("user_type") != "admin":
            return jsonify({'error': 'Admin access required'}), 403
        
        result = fulfillment_manager.check_campaign_manually(campaign_id)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"Error checking campaign fulfillment: {e}")
        return jsonify({'error': 'Failed to check campaign'}), 500


if __name__ == '__main__':
    logger.info("Starting Medical Document Verification API")
    logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    
    # Start automated fulfillment monitoring
    try:
        fulfillment_manager.start_monitoring()
        logger.info("Campaign fulfillment monitoring started")
    except Exception as e:
        logger.error(f"Failed to start fulfillment monitoring: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
