"""
MediTrust HMS (Hospital Management System) Mock Service
Separate Node.js service for patient ledger, billing truth, and discharge management
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid
import logging

logger = logging.getLogger(__name__)

class MediTrustHMS:
    """Mock Hospital Management System for MediTrust platform"""
    
    def __init__(self):
        """Initialize HMS with mock data"""
        self.patients = {}
        self.billing_ledger = {}
        self.documents = {}
        self.payments = {}
        self.setup_mock_data()
    
    def setup_mock_data(self):
        """Setup initial mock hospital data"""
        # Mock hospital data
        self.hospitals = {
            "apollo_hospital": {
                "name": "Apollo Hospital",
                "address": "123 Medical Complex, Bangalore, Karnataka 560001",
                "phone": "+91-80-12345678",
                "email": "billing@apollohospital.com",
                "verified": True
            },
            "fortis_hospital": {
                "name": "Fortis Healthcare",
                "address": "456 Health Avenue, Mumbai, Maharashtra 400001",
                "phone": "+91-22-87654321",
                "email": "accounts@fortishealthcare.com",
                "verified": True
            },
            "max_healthcare": {
                "name": "Max Super Speciality Hospital",
                "address": "789 Medical Plaza, Delhi, Delhi 110001",
                "phone": "+91-11-98765432",
                "email": "billing@maxhealthcare.com",
                "verified": True
            }
        }
    
    # ==================== PATIENT MANAGEMENT ====================
    
    def create_patient(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new patient in HMS"""
        try:
            patient_id = str(uuid.uuid4())
            
            patient = {
                "patient_id": patient_id,
                "name": patient_data.get("name", ""),
                "email": patient_data.get("email", ""),
                "phone": patient_data.get("phone", ""),
                "aadhaar": patient_data.get("aadhaar", ""),
                "date_of_birth": patient_data.get("date_of_birth", ""),
                "blood_group": patient_data.get("blood_group", ""),
                "emergency_contact": patient_data.get("emergency_contact", {}),
                "current_hospital": patient_data.get("hospital_name", ""),
                "status": "ACTIVE",  # ACTIVE, DISCHARGED, TRANSFERRED
                "admission_date": datetime.utcnow(),
                "discharge_date": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            self.patients[patient_id] = patient
            
            # Initialize billing ledger
            self.billing_ledger[patient_id] = {
                "patient_id": patient_id,
                "hospital_name": patient["current_hospital"],
                "total_estimated_amount": 0,
                "total_paid_amount": 0,
                "outstanding_amount": 0,
                "transactions": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            return {
                "success": True,
                "patient_id": patient_id,
                "patient": patient,
                "message": "Patient created successfully in HMS"
            }
            
        except Exception as e:
            logger.error(f"Patient creation failed: {e}")
            return {"success": False, "error": "Failed to create patient"}
    
    def get_patient_outstanding_amount(self, patient_id: str) -> Dict[str, Any]:
        """Get outstanding amount for patient"""
        try:
            if patient_id not in self.billing_ledger:
                return {"success": False, "error": "Patient not found"}
            
            ledger = self.billing_ledger[patient_id]
            outstanding = ledger["outstanding_amount"]
            
            return {
                "success": True,
                "patient_id": patient_id,
                "outstanding_amount": outstanding,
                "total_estimated": ledger["total_estimated_amount"],
                "total_paid": ledger["total_paid_amount"],
                "last_updated": ledger["updated_at"]
            }
            
        except Exception as e:
            logger.error(f"Outstanding amount fetch failed: {e}")
            return {"success": False, "error": "Failed to get outstanding amount"}
    
    def get_patient_status(self, patient_id: str) -> Dict[str, Any]:
        """Get current status of patient"""
        try:
            if patient_id not in self.patients:
                return {"success": False, "error": "Patient not found"}
            
            patient = self.patients[patient_id]
            
            return {
                "success": True,
                "patient_id": patient_id,
                "status": patient["status"],
                "current_hospital": patient["current_hospital"],
                "admission_date": patient["admission_date"],
                "discharge_date": patient["discharge_date"],
                "last_updated": patient["updated_at"]
            }
            
        except Exception as e:
            logger.error(f"Patient status fetch failed: {e}")
            return {"success": False, "error": "Failed to get patient status"}
    
    def discharge_patient(self, patient_id: str, discharge_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Discharge patient from hospital"""
        try:
            if patient_id not in self.patients:
                return {"success": False, "error": "Patient not found"}
            
            patient = self.patients[patient_id]
            patient["status"] = "DISCHARGED"
            patient["discharge_date"] = datetime.utcnow()
            patient["discharge_reason"] = discharge_data.get("reason", "Treatment completed") if discharge_data else "Treatment completed"
            patient["updated_at"] = datetime.utcnow()
            
            return {
                "success": True,
                "patient_id": patient_id,
                "message": "Patient discharged successfully",
                "discharge_date": patient["discharge_date"]
            }
            
        except Exception as e:
            logger.error(f"Patient discharge failed: {e}")
            return {"success": False, "error": "Failed to discharge patient"}
    
    def update_patient_hospital(self, patient_id: str, new_hospital: str, new_estimate: float = None) -> Dict[str, Any]:
        """Update patient's registered hospital"""
        try:
            if patient_id not in self.patients:
                return {"success": False, "error": "Patient not found"}
            
            patient = self.patients[patient_id]
            old_hospital = patient["current_hospital"]
            
            patient["current_hospital"] = new_hospital
            patient["updated_at"] = datetime.utcnow()
            
            # Update billing ledger
            if patient_id in self.billing_ledger:
                ledger = self.billing_ledger[patient_id]
                ledger["hospital_name"] = new_hospital
                ledger["updated_at"] = datetime.utcnow()
                
                if new_estimate:
                    ledger["total_estimated_amount"] = new_estimate
                    ledger["outstanding_amount"] = new_estimate - ledger["total_paid_amount"]
            
            return {
                "success": True,
                "patient_id": patient_id,
                "old_hospital": old_hospital,
                "new_hospital": new_hospital,
                "message": "Hospital updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Hospital update failed: {e}")
            return {"success": False, "error": "Failed to update hospital"}
    
    # ==================== BILLING MANAGEMENT ====================
    
    def create_billing_estimate(self, patient_id: str, estimate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create initial billing estimate for patient"""
        try:
            if patient_id not in self.billing_ledger:
                return {"success": False, "error": "Patient not found"}
            
            ledger = self.billing_ledger[patient_id]
            
            estimate = {
                "estimate_id": str(uuid.uuid4()),
                "patient_id": patient_id,
                "hospital_name": ledger["hospital_name"],
                "total_amount": estimate_data.get("total_amount", 0),
                "breakdown": estimate_data.get("breakdown", {}),
                "valid_until": datetime.utcnow() + timedelta(days=30),
                "status": "ACTIVE",  # ACTIVE, EXPIRED, REPLACED
                "created_at": datetime.utcnow()
            }
            
            ledger["total_estimated_amount"] = estimate["total_amount"]
            ledger["outstanding_amount"] = estimate["total_amount"] - ledger["total_paid_amount"]
            ledger["updated_at"] = datetime.utcnow()
            
            return {
                "success": True,
                "estimate_id": estimate["estimate_id"],
                "total_amount": estimate["total_amount"],
                "outstanding_amount": ledger["outstanding_amount"],
                "message": "Billing estimate created successfully"
            }
            
        except Exception as e:
            logger.error(f"Billing estimate creation failed: {e}")
            return {"success": False, "error": "Failed to create billing estimate"}
    
    def record_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record payment and update billing ledger"""
        try:
            patient_id = payment_data.get("patient_id")
            
            if patient_id not in self.billing_ledger:
                return {"success": False, "error": "Patient not found"}
            
            ledger = self.billing_ledger[patient_id]
            
            payment = {
                "payment_id": str(uuid.uuid4()),
                "patient_id": patient_id,
                "campaign_id": payment_data.get("campaign_id", ""),
                "milestone_id": payment_data.get("milestone_id", ""),
                "amount": payment_data.get("amount", 0),
                "payment_type": payment_data.get("payment_type", "DONATION"),
                "transaction_id": payment_data.get("transaction_id", ""),
                "hospital_name": ledger["hospital_name"],
                "status": "COMPLETED",  # PENDING, COMPLETED, FAILED
                "processed_at": datetime.utcnow(),
                "created_at": datetime.utcnow()
            }
            
            # Update ledger
            ledger["total_paid_amount"] += payment["amount"]
            ledger["outstanding_amount"] = ledger["total_estimated_amount"] - ledger["total_paid_amount"]
            ledger["transactions"].append(payment)
            ledger["updated_at"] = datetime.utcnow()
            
            # Store payment record
            self.payments[payment["payment_id"]] = payment
            
            return {
                "success": True,
                "payment_id": payment["payment_id"],
                "amount": payment["amount"],
                "outstanding_amount": ledger["outstanding_amount"],
                "message": f"Payment of ₹{payment['amount']:,.2f} recorded successfully"
            }
            
        except Exception as e:
            logger.error(f"Payment recording failed: {e}")
            return {"success": False, "error": "Failed to record payment"}
    
    def get_billing_ledger(self, patient_id: str) -> Dict[str, Any]:
        """Get complete billing ledger for patient"""
        try:
            if patient_id not in self.billing_ledger:
                return {"success": False, "error": "Patient not found"}
            
            ledger = self.billing_ledger[patient_id]
            
            return {
                "success": True,
                "ledger": ledger,
                "transactions": ledger["transactions"],
                "summary": {
                    "total_estimated": ledger["total_estimated_amount"],
                    "total_paid": ledger["total_paid_amount"],
                    "outstanding": ledger["outstanding_amount"],
                    "payment_count": len(ledger["transactions"])
                }
            }
            
        except Exception as e:
            logger.error(f"Billing ledger fetch failed: {e}")
            return {"success": False, "error": "Failed to get billing ledger"}
    
    # ==================== DOCUMENT MANAGEMENT ====================
    
    def upload_patient_document(self, patient_id: str, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upload and store patient document"""
        try:
            if patient_id not in self.patients:
                return {"success": False, "error": "Patient not found"}
            
            document_id = str(uuid.uuid4())
            
            document = {
                "document_id": document_id,
                "patient_id": patient_id,
                "document_type": document_data.get("document_type", ""),
                "file_name": document_data.get("file_name", ""),
                "file_path": document_data.get("file_path", ""),
                "file_size": document_data.get("file_size", 0),
                "upload_date": datetime.utcnow(),
                "verified": False,
                "verification_date": None,
                "hospital_verified": False
            }
            
            if patient_id not in self.documents:
                self.documents[patient_id] = []
            
            self.documents[patient_id].append(document)
            
            return {
                "success": True,
                "document_id": document_id,
                "message": "Document uploaded successfully"
            }
            
        except Exception as e:
            logger.error(f"Document upload failed: {e}")
            return {"success": False, "error": "Failed to upload document"}
    
    def get_patient_documents(self, patient_id: str) -> Dict[str, Any]:
        """Get all documents for patient"""
        try:
            if patient_id not in self.documents:
                return {"success": True, "documents": []}
            
            documents = self.documents[patient_id]
            
            return {
                "success": True,
                "documents": documents,
                "count": len(documents)
            }
            
        except Exception as e:
            logger.error(f"Documents fetch failed: {e}")
            return {"success": False, "error": "Failed to get documents"}
    
    # ==================== HOSPITAL MANAGEMENT ====================
    
    def get_hospital_details(self, hospital_name: str) -> Dict[str, Any]:
        """Get hospital details"""
        try:
            # Search hospital by name (case-insensitive)
            hospital_key = None
            for key, hospital in self.hospitals.items():
                if hospital["name"].lower() == hospital_name.lower():
                    hospital_key = key
                    break
            
            if not hospital_key:
                return {"success": False, "error": "Hospital not found"}
            
            hospital = self.hospitals[hospital_key]
            
            return {
                "success": True,
                "hospital": hospital,
                "verified": hospital["verified"]
            }
            
        except Exception as e:
            logger.error(f"Hospital details fetch failed: {e}")
            return {"success": False, "error": "Failed to get hospital details"}
    
    def verify_hospital(self, hospital_name: str, verification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify hospital credentials"""
        try:
            hospital_result = self.get_hospital_details(hospital_name)
            
            if not hospital_result["success"]:
                return {"success": False, "error": "Hospital not found"}
            
            hospital = hospital_result["hospital"]
            
            # Update hospital verification status
            hospital["verified"] = True
            hospital["verification_date"] = datetime.utcnow()
            hospital["verification_documents"] = verification_data.get("documents", [])
            hospital["verified_by"] = verification_data.get("verified_by", "system")
            
            return {
                "success": True,
                "hospital": hospital,
                "message": "Hospital verified successfully"
            }
            
        except Exception as e:
            logger.error(f"Hospital verification failed: {e}")
            return {"success": False, "error": "Failed to verify hospital"}
    
    # ==================== REPORTING ====================
    
    def get_patient_summary(self, patient_id: str) -> Dict[str, Any]:
        """Get complete patient summary"""
        try:
            patient_result = self.get_patient_status(patient_id)
            if not patient_result["success"]:
                return patient_result
            
            billing_result = self.get_billing_ledger(patient_id)
            documents_result = self.get_patient_documents(patient_id)
            
            return {
                "success": True,
                "patient": patient_result,
                "billing": billing_result,
                "documents": documents_result,
                "summary": {
                    "patient_id": patient_id,
                    "name": self.patients[patient_id]["name"],
                    "current_hospital": self.patients[patient_id]["current_hospital"],
                    "status": self.patients[patient_id]["status"],
                    "outstanding_amount": billing_result.get("ledger", {}).get("outstanding_amount", 0),
                    "document_count": len(documents_result.get("documents", [])),
                    "last_updated": datetime.utcnow()
                }
            }
            
        except Exception as e:
            logger.error(f"Patient summary failed: {e}")
            return {"success": False, "error": "Failed to get patient summary"}
    
    def get_hospital_summary(self, hospital_name: str) -> Dict[str, Any]:
        """Get hospital summary with all patients"""
        try:
            hospital_result = self.get_hospital_details(hospital_name)
            if not hospital_result["success"]:
                return hospital_result
            
            # Get all patients for this hospital
            hospital_patients = []
            total_outstanding = 0
            
            for patient_id, patient in self.patients.items():
                if patient["current_hospital"].lower() == hospital_name.lower():
                    hospital_patients.append(patient)
                    
                    if patient_id in self.billing_ledger:
                        total_outstanding += self.billing_ledger[patient_id]["outstanding_amount"]
            
            return {
                "success": True,
                "hospital": hospital_result["hospital"],
                "patients": hospital_patients,
                "patient_count": len(hospital_patients),
                "total_outstanding": total_outstanding,
                "summary": {
                    "hospital_name": hospital_name,
                    "verified": hospital_result["hospital"]["verified"],
                    "active_patients": len([p for p in hospital_patients if p["status"] == "ACTIVE"]),
                    "discharged_patients": len([p for p in hospital_patients if p["status"] == "DISCHARGED"]),
                    "total_outstanding": total_outstanding
                }
            }
            
        except Exception as e:
            logger.error(f"Hospital summary failed: {e}")
            return {"success": False, "error": "Failed to get hospital summary"}
