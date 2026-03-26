"""
MediTrust AI Verification Service
Flask backend for OCR + NLP + Tampering Detection + Cross-Document Validation
Pure verification service — no auth, no campaigns, no donations
Those are handled by Node.js MediTrust backend
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime
import os
import logging
import traceback
import base64

load_dotenv()

# Import core AI modules only
from nlp.entity_extractor import MedicalEntityExtractor
from nlp.bert_authenticator import BERTDocumentAuthenticator
from ocr.pdf_ocr import DocumentOCR
from validation.cross_document import CrossDocumentValidator
from notifications.notification_manager import NotificationManager
from automation.fulfillment_manager import FulfillmentManager
from nlp.disease_mapper import build_ngo_query_conditions, get_disease_label

# ─────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# FLASK APP
# ─────────────────────────────────────────
app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
app.config['UPLOAD_FOLDER']      = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ─────────────────────────────────────────
# INTERNAL SECRET — only Node.js can call us
# ─────────────────────────────────────────
FLASK_INTERNAL_SECRET = os.getenv("FLASK_INTERNAL_SECRET", "")

def verify_internal_secret():
    """Check that request is coming from MediTrust Node.js backend"""
    secret = request.headers.get("x-flask-secret", "")
    if FLASK_INTERNAL_SECRET and secret != FLASK_INTERNAL_SECRET:
        return False
    return True

# ─────────────────────────────────────────
# INITIALIZE AI COMPONENTS
# ─────────────────────────────────────────
logger.info("Loading AI components...")

ocr_processor      = DocumentOCR()
entity_extractor   = MedicalEntityExtractor()
bert_authenticator = BERTDocumentAuthenticator()
validator          = CrossDocumentValidator()
notification       = NotificationManager()
fulfillment        = FulfillmentManager(notification)

logger.info("All AI components loaded successfully")

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def determine_document_type(text, entities):
    """Determine medical document type from content"""
    text_lower = text.lower()
    if 'estimate'   in text_lower: return 'ESTIMATE'
    if 'discharge'  in text_lower: return 'DISCHARGE_SUMMARY'
    if 'bill'       in text_lower or 'invoice' in text_lower: return 'BILL'
    if 'prescription' in text_lower: return 'PRESCRIPTION'
    if 'report'     in text_lower or 'test' in text_lower: return 'MEDICAL_REPORT'
    if 'aadhaar'    in text_lower or 'aadhar' in text_lower: return 'AADHAAR'
    if 'ration'     in text_lower: return 'RATION_CARD'
    if 'income'     in text_lower: return 'INCOME_CERTIFICATE'
    if 'admission'  in text_lower: return 'ADMISSION_SUMMARY'
    return 'UNKNOWN'


def validate_mandatory_fields(entities, document_type):
    """
    Validate mandatory fields based on document type.
    Returns list of issues found.
    """
    issues = []

    # All documents must have patient name
    if not entities.get('patient_name'):
        issues.append("Missing: Patient name")

    # Medical documents must have disease and date
    medical_types = ['ESTIMATE', 'BILL', 'DISCHARGE_SUMMARY',
                     'PRESCRIPTION', 'MEDICAL_REPORT', 'ADMISSION_SUMMARY']

    if document_type in medical_types:
        if not entities.get('diseases') or len(entities['diseases']) == 0:
            issues.append("Missing: Disease / Diagnosis")
        if not entities.get('date'):
            issues.append("Missing: Date")
        if not entities.get('hospital_name') and not entities.get('hospital_pincode'):
            issues.append("Missing: Hospital name or pincode")

    # Financial documents must have amount
    financial_types = ['ESTIMATE', 'BILL']
    if document_type in financial_types:
        if not entities.get('amount'):
            issues.append("Missing: Amount")

    return issues


def check_document_expiry(entities, document_type):
    """
    Check if hospital estimate or bill is expired.
    Estimates are valid for 90 days.
    Returns (is_expired, days_old)
    """
    if document_type not in ['ESTIMATE', 'BILL']:
        return False, 0

    try:
        date_str = entities.get('date')
        if not date_str:
            return False, 0

        # Try common Indian date formats
        for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d %B %Y']:
            try:
                doc_date = datetime.strptime(date_str.strip(), fmt)
                days_old = (datetime.now() - doc_date).days
                if days_old > 90:
                    return True, days_old
                return False, days_old
            except ValueError:
                continue
        return False, 0

    except Exception as e:
        logger.warning(f"Date check error: {e}")
        return False, 0


def calculate_final_status(documents, cross_document_issues, has_expired_docs, has_tampering):
    """
    Calculate final verification status and risk score.
ate final verification status and risk score.

    Status mapping:
        VERIFIED            → risk < 30, no tampering, no expiry
        PENDING             → risk 30-69, minor issues
        VERIFICATION_NEEDED → risk >= 70 OR tampering detected
        UPDATE_NEEDED       → expired documents found
    """
    risk_score = 0

    failed_docs      = sum(1 for d in documents if d.get('status') == 'FAILED')
    docs_with_issues = sum(1 for d in documents if len(d.get('issues', [])) > 0)

    # Base scoring
    risk_score += failed_docs * 20
    risk_score += docs_with_issues * 15
    risk_score += len(cross_document_issues) * 10

    # Cross-document issue severity
    for issue in cross_document_issues:
        issue_lower = issue.lower()
        if 'patient name mismatch' in issue_lower:
            risk_score += 30
        elif 'conflicting dates'   in issue_lower:
            risk_score += 20
        elif 'missing hospital'    in issue_lower:
            risk_score += 15
        elif 'bill exceeds'        in issue_lower:
            risk_score += 25

    # Tampering detected — serious
    if has_tampering:
        risk_score += 50

    risk_score = min(risk_score, 100)

    # Status decision
    if has_expired_docs:
        return 'UPDATE_NEEDED', risk_score
    elif has_tampering or risk_score >= 70:
        return 'VERIFICATION_NEEDED', risk_score
    elif risk_score >= 30:
        return 'PENDING', risk_score
    else:
        return 'VERIFIED', risk_score


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health_check():
    """Health check — called by Node.js to confirm Flask is running"""
    return jsonify({
        'status'    : 'healthy',
        'service'   : 'MediTrust AI Verification Service',
        'timestamp' : datetime.utcnow().isoformat(),
        'components': {
            'ocr'      : 'ready',
            'nlp'      : 'ready',
            'bert'     : 'ready',
            'validator': 'ready'
        }
    })

@app.route('/verify', methods=['POST'])
def verify_documents():
    """AI Document Verification Endpoint"""
    try:
        # Internal secret check — disabled for development
        # Re-enable in production by uncommenting:
        # if not verify_internal_secret():
        #     return jsonify({'error': 'Unauthorized'}), 403

        data         = request.get_json()
        documents    = data.get('documents', [])
        patient_name = data.get('patient_name', '')

        if not documents:
            return jsonify({'error': 'No documents provided'}), 400

        logger.info(f"Verifying {len(documents)} documents for {patient_name}")

        all_extracted  = {}
        all_issues     = []
        has_tampering  = False
        has_expired    = False
        risk_score     = 0
        doc_results    = []

        for doc in documents:
            doc_type    = doc.get('document_type', 'UNKNOWN')
            # Frontend sends file_url (data URL) OR file_content (raw base64)
            file_url    = doc.get('file_url', '') or doc.get('file_content', '')
            mime_type   = doc.get('mime_type', 'application/pdf')
            file_name   = doc.get('file_name', '')

            logger.info(f"Processing document: {file_name} ({doc_type})")

            try:
                # Decode base64 content — handle both data URL and raw base64
                import tempfile
                if file_url.startswith('data:'):
                    # data:application/pdf;base64,XXXXX
                    header, b64data = file_url.split(',', 1)
                    mime_type = header.split(':')[1].split(';')[0]
                    file_bytes = base64.b64decode(b64data)
                else:
                    file_bytes = base64.b64decode(file_url)

                # Determine extension
                if mime_type == 'application/pdf' or file_name.endswith('.pdf'):
                    ext = '.pdf'
                elif mime_type == 'image/png':
                    ext = '.png'
                else:
                    ext = '.jpg'

                # Write to temp file
                tmp = tempfile.NamedTemporaryFile(
                    delete=False, suffix=ext,
                    dir=app.config['UPLOAD_FOLDER']
                )
                tmp.write(file_bytes)
                tmp.flush()
                tmp.close()

                # Extract text using OCR
                extracted_text = ocr_processor.extract_text(tmp.name)

                logger.info(f"Extracted {len(extracted_text)} chars from {file_name}")

                # ── STAGE 1: TAMPERING CHECK (before entity extraction) ──────
                # Pass file_path so Layer 1 (PDF metadata) + Layer 2 (ELA) run
                logger.info(f"Running tampering check on {file_name}...")
                auth_result = bert_authenticator.predict_authenticity(
                    extracted_text, {}, file_path=tmp.name
                )

                # Cleanup temp file AFTER forensics check
                try:
                    os.remove(tmp.name)
                except:
                    pass

                if auth_result.get('is_tampered'):
                    has_tampering = True
                    risk_score   += 50
                    tamper_flags  = auth_result.get('flags', [])
                    tamper_msg    = f"TAMPERING DETECTED in {file_name}"
                    if tamper_flags:
                        tamper_msg += f": {tamper_flags[0]}"
                    all_issues.append(tamper_msg)
                    logger.warning(f"🚨 {tamper_msg}")

                    # Add to doc result immediately — skip entity extraction
                    doc_results.append({{
                        'document_type' : doc_type,
                        'file_name'     : file_name,
                        'status'        : 'TAMPERED',
                        'is_tampered'   : True,
                        'tamper_flags'  : tamper_flags,
                        'entities'      : {{}}
                    }})
                    continue  # Skip entity extraction for tampered doc

                logger.info(f"✅ No tampering detected in {file_name}")

                # ── STAGE 2: ENTITY EXTRACTION (only if not tampered) ────────
                entities = entity_extractor.extract_entities(extracted_text)

                logger.info(f" === ENTITY EXTRACTION FOR {file_name} ===")
                logger.info(f"Patient Name   : {entities.get('patient_name')}")
                logger.info(f"Hospital Name  : {entities.get('hospital_name')}")
                logger.info(f"Diseases       : {entities.get('diseases')}")
                logger.info(f"Amount         : {entities.get('amount')}")
                logger.info(f"Aadhaar        : {entities.get('aadhaar_number')}")
                logger.info(f"Age/Gender     : {entities.get('age')} / {entities.get('gender')}")
                logger.info("=========================================")

                # Check expiry
                is_expired, days_old = check_document_expiry(entities, doc_type)
                if is_expired:
                    has_expired = True
                    risk_score += 20
                    all_issues.append(f"Expired document: {file_name}")

                # Merge extracted data
                logger.info(f" === MERGING DATA FOR {file_name} ({doc_type}) ===")

                if entities.get('hospital_name'):
                    if not all_extracted.get('hospital_name'):
                        all_extracted['hospital_name'] = entities.get('hospital_name')
                        logger.info(f"Set hospital: {entities.get('hospital_name')}")
                    else:
                        logger.info(f"Hospital already set, skipping")

                # Hospital pincode — ONLY from ESTIMATE or ADMISSION_SUMMARY
                # NOT from Aadhaar (that has patient's home pincode)
                if entities.get('hospital_pincode') and doc_type in ['ESTIMATE', 'ADMISSION_SUMMARY', 'BILL', 'DISCHARGE_SUMMARY']:
                    if not all_extracted.get('hospital_pincode'):
                        all_extracted['hospital_pincode'] = entities.get('hospital_pincode')
                        logger.info(f"Set hospital pincode: {entities.get('hospital_pincode')}")

                if entities.get('diseases') and entities.get('diseases') != []:
                    if not all_extracted.get('disease'):
                        # Store as single string — use first/primary diagnosis only
                        primary = entities.get('diseases')[0] if entities.get('diseases') else ''
                        all_extracted['disease'] = primary
                        logger.info(f"Set disease: {primary}")
                    else:
                        logger.info(f"Disease already set, skipping")

                # Amount from hospital documents only — not income cert
                if entities.get('amount') and doc_type in ['ESTIMATE', 'BILL', 'ADMISSION_SUMMARY']:
                    if not all_extracted.get('amount'):
                        all_extracted['amount'] = entities.get('amount')
                        logger.info(f"Set amount: {entities.get('amount')}")
                    else:
                        logger.info(f"Amount already set, skipping")

                # Annual income — ONLY from INCOME_CERTIFICATE
                if entities.get('amount') and doc_type == 'INCOME_CERTIFICATE':
                    all_extracted['annual_income'] = entities.get('amount')
                    logger.info(f"Set annual_income: {entities.get('amount')}")

                if entities.get('patient_name'):
                    if not all_extracted.get('patient_name'):
                        all_extracted['patient_name'] = entities.get('patient_name')
                        logger.info(f"Set patient: {entities.get('patient_name')}")
                    else:
                        logger.info(f"Patient already set, skipping")

                if entities.get('date'):
                    if not all_extracted.get('admission_date'):
                        all_extracted['admission_date'] = entities.get('date')
                        logger.info(f"Set date: {entities.get('date')}")
                    else:
                        logger.info(f"Date already set, skipping")

                # ── Extract Aadhaar fields (only from AADHAAR document) ──────
                if doc_type == 'AADHAAR':
                    if entities.get('aadhaar_number') and not all_extracted.get('aadhaar_number'):
                        all_extracted['aadhaar_number'] = entities.get('aadhaar_number')
                    if entities.get('age') and not all_extracted.get('age'):
                        all_extracted['age'] = entities.get('age')
                    if entities.get('gender') and not all_extracted.get('gender'):
                        all_extracted['gender'] = entities.get('gender')
                    if entities.get('city') and not all_extracted.get('city'):
                        all_extracted['city'] = entities.get('city')
                    if entities.get('state') and not all_extracted.get('state'):
                        all_extracted['state'] = entities.get('state')

                doc_results.append({
                    'document_type': doc_type,
                    'file_name'    : file_name,
                    'status'       : 'PROCESSED',
                    'entities'     : entities
                })

            except Exception as e:
                logger.error(f"Error processing {file_name}: {str(e)}")
                risk_score += 10
                all_issues.append(f"Could not process {file_name}: {str(e)}")
                doc_results.append({
                    'document_type': doc_type,
                    'file_name'    : file_name,
                    'status'       : 'ERROR',
                    'error'        : str(e)
                })

        # ── STAGE 3: CROSS-DOCUMENT CONSISTENCY CHECK ──────────────────
        # Check name consistency across all documents
        patient_names = []
        for dr in doc_results:
            if dr.get('status') == 'PROCESSED' and dr.get('entities', {}).get('patient_name'):
                patient_names.append(dr['entities']['patient_name'].lower().strip())

        name_mismatch = False
        if len(patient_names) >= 2:
            first_name = patient_names[0].split()[0]  # Compare first name only
            for name in patient_names[1:]:
                if first_name not in name and name.split()[0] not in patient_names[0]:
                    name_mismatch = True
                    all_issues.append(f"Patient name mismatch across documents: {patient_names}")
                    logger.warning(f"⚠️ Name mismatch: {patient_names}")
                    break

        # ── DETERMINE FINAL STATUS ───────────────────────────────────────────
        # FAKE_DETECTED → hard stop (tampering found)
        # PENDING       → silent flag (name mismatch, missing data)
        # VERIFIED      → all clean
        if has_tampering:
            final_status = 'FAKE_DETECTED'
        elif has_expired:
            final_status = 'UPDATE_NEEDED'
        elif name_mismatch:
            final_status = 'PENDING'
        elif risk_score >= 30:
            final_status = 'PENDING'
        else:
            final_status = 'VERIFIED'

        logger.info(f"Verification complete: {final_status}, risk: {risk_score}")

        return jsonify({
            'status'                : final_status,
            'final_status'          : final_status,
            'risk_score'            : risk_score,
            'total_documents'       : len(documents),
            'processed_documents'   : len(doc_results),
            'cross_document_issues' : all_issues,
            'has_expired_docs'      : has_expired,
            'has_tampering'         : has_tampering,
            'document_results'      : doc_results,
            'documents'             : doc_results,
            'extracted_data'        : all_extracted,
            'timestamp'             : datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Verification error: {str(e)}")
        # Return 500 with real error — do NOT fake a PENDING result
        # Frontend must know Flask failed so it can show real error
        return jsonify({
            'success'     : False,
            'error'       : str(e),
            'final_status': None,
            'risk_score'  : None,
        }), 500


@app.route('/map-disease', methods=['POST'])
def map_disease():
    """Map disease text to NGO capability columns"""
    try:
        secret = request.headers.get('x-flask-secret')
        if secret != 'meditrust_flask_internal_2026':
            return jsonify({'error': 'Unauthorized'}), 403

        data         = request.get_json()
        disease_text = data.get('disease_text', '')
        patient_age  = data.get('patient_age', 30)

        conditions = build_ngo_query_conditions(disease_text, patient_age)
        label      = get_disease_label(disease_text)

        return jsonify({
            'success'   : True,
            'label'     : label,
            'conditions': conditions
        })

    except Exception as e:
        logger.error(f"Disease mapping error: {e}")
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────
# HELPER — Merge entities from all docs
# ─────────────────────────────────────────

def merge_extracted_entities(all_docs):
    """
    Merge extracted entities from all documents into one clean object.
    Node.js backend uses this to pre-fill campaign fields.
    """
    merged = {
        'patient_name'     : None,
        'hospital_name'    : None,
        'hospital_pincode' : None,
        'diseases'         : [],
        'doctor_name'      : None,
        'admission_date'   : None,
        'amount'           : None,
    }

    for doc in all_docs:
        entities = doc.get('entities', {})

        if not merged['patient_name'] and entities.get('patient_name'):
            merged['patient_name'] = entities['patient_name']

        if not merged['hospital_name'] and entities.get('hospital_name'):
            merged['hospital_name'] = entities['hospital_name']

        if not merged['hospital_pincode'] and entities.get('hospital_pincode'):
            merged['hospital_pincode'] = entities['hospital_pincode']

        if not merged['doctor_name'] and entities.get('doctor_name'):
            merged['doctor_name'] = entities['doctor_name']

        if not merged['admission_date'] and entities.get('date'):
            merged['admission_date'] = entities['date']

        # Amount — prefer ESTIMATE over BILL
        if doc.get('document_type') == 'ESTIMATE' and entities.get('amount'):
            merged['amount'] = entities['amount']
        elif not merged['amount'] and entities.get('amount'):
            merged['amount'] = entities['amount']

        # Merge diseases
        for disease in entities.get('diseases', []):
            if disease not in merged['diseases']:
                merged['diseases'].append(disease)

    return merged




# ─────────────────────────────────────────
# NOTIFY ROUTES — called by Node.js backend
# ─────────────────────────────────────────

@app.route('/notify/campaign-live', methods=['POST'])
def notify_campaign_live():
    """Notify patient their campaign is now LIVE"""
    try:
        data           = request.get_json()
        to_email       = data.get('to_email', '')
        patient_name   = data.get('patient_name', '')
        campaign_title = data.get('campaign_title', '')
        public_url     = data.get('public_url', '')
        upi_id         = data.get('upi_id', '')

        notification.send_campaign_live_email(
            to_email, patient_name, campaign_title, public_url, upi_id
        )
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"notify_campaign_live error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/notify/campaign-rejected', methods=['POST'])
def notify_campaign_rejected():
    """Notify patient their campaign was rejected"""
    try:
        data           = request.get_json()
        to_email       = data.get('to_email', '')
        patient_name   = data.get('patient_name', '')
        campaign_title = data.get('campaign_title', '')
        reason         = data.get('reason', 'Did not meet verification requirements')

        subject = f"MediTrust — Your Campaign Was Not Approved"
        body = f"""Dear {patient_name},

We regret to inform you that your campaign "{campaign_title}" could not be approved after review.

Reason: {reason}

Your campaign data has been removed from our system. You are welcome to apply again with correct documents if applicable.

If you believe this is an error, please contact us at support@meditrust.in

With care,
Team MediTrust

---
This is an automated email. Please do not reply.
"""
        notification._send(to_email, subject, body)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"notify_campaign_rejected error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/notify/verification-status', methods=['POST'])
def notify_verification_status():
    """Notify patient about verification status"""
    try:
        data           = request.get_json()
        to_email       = data.get('to_email', '')
        patient_name   = data.get('patient_name', '')
        status         = data.get('status', '')
        campaign_title = data.get('campaign_title', '')
        reason         = data.get('reason', '')

        notification.send_verification_status_email(
            to_email, patient_name, status, campaign_title, reason
        )
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"notify_verification_status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/notify/fund-release', methods=['POST'])
def notify_fund_release():
    """Notify patient about fund release"""
    try:
        data                  = request.get_json()
        to_email              = data.get('to_email', '')
        patient_name          = data.get('patient_name', '')
        campaign_title        = data.get('campaign_title', '')
        amount_released       = data.get('amount_released', 0)
        outstanding_remaining = data.get('outstanding_remaining', 0)

        notification.send_fund_release_notification(
            to_email, patient_name, campaign_title,
            amount_released, outstanding_remaining
        )
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"notify_fund_release error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────

if __name__ == '__main__':
    logger.info("Starting MediTrust AI Verification Service")

    # Start background fulfillment thread
    fulfillment.start()
    logger.info("Fulfillment manager started")

    app.run(host='0.0.0.0', port=5000, debug=False)