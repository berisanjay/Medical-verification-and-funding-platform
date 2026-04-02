# API Documentation

Complete API reference for the Medical Document Verification System.

---

## Base URLs

- **Node.js Backend**: `http://localhost:3000`
- **Flask Backend**: `http://127.0.0.1:5000`

---

## Authentication

Currently, the API does not require authentication. This will be added in future versions using JWT tokens.

---

## Endpoints

### Node.js Endpoints

#### 1. Health Check

Check if the Node.js server and Flask API are running.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "node": "running",
  "flask": "healthy",
  "timestamp": "2024-01-20T10:30:00.000Z"
}
```

**Status Codes**:
- `200 OK` - Both services are healthy
- `503 Service Unavailable` - Flask API is down

---

#### 2. Upload and Verify Documents

Upload multiple medical documents for verification.

**Endpoint**: `POST /upload`

**Content-Type**: `multipart/form-data`

**Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| files | File[] | Yes | Array of medical documents (PDF, PNG, JPG, JPEG, WEBP) |

**Example Request**:
```javascript
const formData = new FormData();
formData.append('files', file1);
formData.append('files', file2);

fetch('http://localhost:3000/upload', {
  method: 'POST',
  body: formData
})
```

**Response**:
```json
{
  "final_status": "VERIFIED",
  "risk_score": 15,
  "total_documents": 2,
  "processed_documents": 2,
  "cross_document_issues": [],
  "documents": [
    {
      "filename": "estimate.pdf",
      "document_type": "ESTIMATE",
      "entities": {
        "patient_name": "Suresh Kumar",
        "doctor_name": "Dr. Rajesh Sharma",
        "hospital_name": "Yashoda Hospitals",
        "hospital_pincode": "500082",
        "diseases": ["Angioplasty"],
        "date": "15/01/2024",
        "amount": "4,95,000"
      },
      "issues": []
    }
  ],
  "verification_id": "65abc123def456",
  "timestamp": "2024-01-20T10:30:00Z"
}
```

**Status Codes**:
- `200 OK` - Verification successful
- `400 Bad Request` - No files or invalid files
- `500 Internal Server Error` - Processing error
- `503 Service Unavailable` - Flask API unavailable

---

#### 3. Get Verification by ID

Retrieve a past verification result.

**Endpoint**: `GET /verification/:id`

**Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | String | Yes | MongoDB ObjectId of the verification |

**Example Request**:
```javascript
fetch('http://localhost:3000/verification/65abc123def456')
```

**Response**: Same as upload response

**Status Codes**:
- `200 OK` - Verification found
- `404 Not Found` - Verification not found
- `400 Bad Request` - Invalid ID format

---

#### 4. List All Verifications

Get a paginated list of all verifications.

**Endpoint**: `GET /verifications`

**Query Parameters**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| page | Integer | 1 | Page number |
| limit | Integer | 10 | Items per page |

**Example Request**:
```javascript
fetch('http://localhost:3000/verifications?page=1&limit=10')
```

**Response**:
```json
{
  "total": 50,
  "page": 1,
  "limit": 10,
  "results": [
    {
      "_id": "65abc123def456",
      "final_status": "VERIFIED",
      "risk_score": 15,
      "total_documents": 2,
      "created_at": "2024-01-20T10:30:00Z",
      ...
    }
  ]
}
```

**Status Codes**:
- `200 OK` - Success
- `503 Service Unavailable` - Database unavailable

---

### Flask Endpoints

#### 1. Health Check

Check Flask API health.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00.000000",
  "services": {
    "ocr": "available",
    "nlp": "available",
    "database": "available"
  }
}
```

---

#### 2. Verify Documents

Direct endpoint for document verification (used by Node.js).

**Endpoint**: `POST /verify`

**Content-Type**: `multipart/form-data`

**Parameters**: Same as Node.js `/upload` endpoint

**Response**: Same as Node.js `/upload` endpoint

---

## Response Fields

### Verification Response

| Field | Type | Description |
|-------|------|-------------|
| final_status | String | Overall verification status: VERIFIED, NEEDS_CLARIFICATION, HIGH_RISK |
| risk_score | Integer | Risk score from 0-100 |
| total_documents | Integer | Total number of documents uploaded |
| processed_documents | Integer | Number of documents successfully processed |
| cross_document_issues | Array | List of inconsistencies across documents |
| documents | Array | Individual document analysis results |
| verification_id | String | MongoDB ObjectId (if database is available) |
| timestamp | String | ISO 8601 timestamp |

### Document Object

| Field | Type | Description |
|-------|------|-------------|
| filename | String | Original filename |
| document_type | String | Detected document type: ESTIMATE, BILL, PRESCRIPTION, etc. |
| entities | Object | Extracted medical entities |
| issues | Array | Issues found in this document |
| status | String | FAILED if processing failed |
| error | String | Error message if processing failed |

### Entities Object

| Field | Type | Description |
|-------|------|-------------|
| patient_name | String/null | Patient's name |
| doctor_name | String/null | Doctor's name |
| hospital_name | String/null | Hospital name |
| hospital_pincode | String/null | Hospital pincode |
| diseases | Array | List of detected diseases/diagnoses |
| date | String/null | Treatment date |
| amount | String/null | Medical cost amount |

### Cross-Document Issue Object

| Field | Type | Description |
|-------|------|-------------|
| type | String | Issue type: PATIENT_NAME_MISMATCH, HOSPITAL_MISMATCH, etc. |
| severity | String | Severity: LOW, MEDIUM, HIGH |
| description | String | Human-readable description |
| details | Object | Additional details about the issue |

---

## Risk Scoring

The system calculates a risk score from 0-100 based on:

- **Failed Documents** (+20 per document)
- **Documents with Issues** (+15 per document)
- **Cross-Document Issues** (+10 per issue)
- **Specific High-Risk Issues**:
  - Patient name mismatch (+30)
  - Conflicting dates (+20)
  - Missing hospital info (+15)
  - Bill exceeds estimate (+25)

### Final Status Mapping

| Risk Score | Status |
|------------|--------|
| 0-29 | VERIFIED ✅ |
| 30-69 | NEEDS_CLARIFICATION ⚠️ |
| 70-100 | HIGH_RISK 🚨 |

---

## Error Responses

All errors follow this format:

```json
{
  "error": "Error type",
  "message": "Human-readable error message"
}
```

### Common Errors

**400 Bad Request**
```json
{
  "error": "No files provided",
  "message": "Please upload at least one document"
}
```

**500 Internal Server Error**
```json
{
  "error": "Internal server error",
  "message": "OCR extraction failed: Tesseract not found"
}
```

**503 Service Unavailable**
```json
{
  "error": "Service unavailable",
  "message": "Flask API is not available"
}
```

---

## Rate Limiting

Currently, there are no rate limits. This will be added in future versions:
- Planned limit: 100 requests per hour per IP
- Burst limit: 20 requests per minute

---

## Webhooks (Future)

In future versions, you'll be able to register webhook URLs to receive verification results asynchronously for long-running processes.

---

## Examples

### cURL Examples

**Upload documents**:
```bash
curl -X POST http://localhost:3000/upload \
  -F "files=@estimate.pdf" \
  -F "files=@bill.pdf"
```

**Get verification**:
```bash
curl http://localhost:3000/verification/65abc123def456
```

**List verifications**:
```bash
curl "http://localhost:3000/verifications?page=1&limit=5"
```

### Python Example

```python
import requests

# Upload documents
files = [
    ('files', open('estimate.pdf', 'rb')),
    ('files', open('bill.pdf', 'rb'))
]

response = requests.post('http://localhost:3000/upload', files=files)
result = response.json()

print(f"Status: {result['final_status']}")
print(f"Risk Score: {result['risk_score']}")
```

### JavaScript Example

```javascript
// Upload documents
const formData = new FormData();
formData.append('files', fileInput.files[0]);
formData.append('files', fileInput.files[1]);

const response = await fetch('http://localhost:3000/upload', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log('Status:', result.final_status);
console.log('Risk Score:', result.risk_score);
```

---

## Support

For API issues or questions:
1. Check the troubleshooting section in README.md
2. Open an issue on GitHub
3. Contact support team

---

**Last Updated**: January 2024
