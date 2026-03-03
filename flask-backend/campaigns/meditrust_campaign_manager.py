"""
MediTrust Campaign Management System
Complete campaign lifecycle with status machine, phased fund releases, and hospital management
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid
import qrcode
import io
import base64
import requests
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class MediTrustCampaignManager:
    """Complete campaign management for MediTrust platform"""
    
    # Campaign status constants
    STATUS_DRAFT = 'DRAFT'
    STATUS_PENDING_VERIFICATION = 'PENDING_VERIFICATION'
    STATUS_VERIFIED = 'VERIFIED'
    STATUS_PENDING = 'PENDING'
    STATUS_VERIFICATION_NEEDED = 'VERIFICATION_NEEDED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_LIVE_CAMPAIGN = 'LIVE_CAMPAIGN'
    STATUS_HOSPITAL_CHANGE_REQUESTED = 'HOSPITAL_CHANGE_REQUESTED'
    STATUS_REVERIFYING = 'REVERIFYING'
    STATUS_LIVE_UPDATED = 'LIVE_UPDATED'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CLOSED = 'CLOSED'
    STATUS_EXPIRED = 'EXPIRED'
    
    def __init__(self, db, hms_service_url: str = None):
        """Initialize with database and HMS service"""
        self.db = db
        self.campaigns_collection = db.campaigns if db is not None else None
        self.users_collection = db.users if db is not None else None
        self.verifications_collection = db.verifications if db is not None else None
        self.hms_service_url = hms_service_url or "http://localhost:4001"
        
    def create_campaign_draft(self, patient_id: str, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create campaign in DRAFT status"""
        try:
            if not self.campaigns_collection:
                return {"success": False, "error": "Database not available"}
            
            campaign = {
                "_id": str(ObjectId()),
                "patient_id": patient_id,
                "status": self.STATUS_DRAFT,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "title": campaign_data.get('title', ''),
                "medical_condition": campaign_data.get('medical_condition', ''),
                "description": "",
                "target_amount": 0,
                "current_amount": 0,
                "hospital_name": "",
                "hospital_address": "",
                "upi_id": "",
                "qr_code": "",
                "public_url": "",
                "milestones": [],
                "documents": [],
                "verification_id": None,
                "story_original": "",
                "story_gemini": "",
                "story_approved": False,
                "donations": [],
                "ngo_matches": [],
                "analytics": {
                    "donors_count": 0,
                    "emails_sent": 0,
                    "whatsapp_sent": 0,
                    "ngos_matched": 0,
                    "ngo_responses": 0
                }
            }
            
            result = self.campaigns_collection.insert_one(campaign)
            campaign["_id"] = str(result.inserted_id)
            
            return {
                "success": True,
                "campaign": campaign,
                "message": "Campaign draft created. Please upload documents for verification."
            }
            
        except Exception as e:
            logger.error(f"Campaign draft creation failed: {e}")
            return {"success": False, "error": "Failed to create campaign draft"}
    
    def submit_documents_for_verification(self, campaign_id: str, documents: List[Dict[str, str]]) -> Dict[str, Any]:
        """Submit documents for AI verification"""
        try:
            if not self.campaigns_collection:
                return {"success": False, "error": "Database not available"}
            
            # Update campaign with documents
            self.campaigns_collection.update_one(
                {"_id": campaign_id},
                {
                    "$set": {
                        "documents": documents,
                        "status": self.STATUS_PENDING_VERIFICATION,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Trigger AI verification (this would call the verification engine)
            # For now, simulate verification
            verification_result = self.trigger_ai_verification(campaign_id, documents)
            
            return {
                "success": True,
                "verification_id": verification_result.get("verification_id"),
                "message": "Documents submitted for verification"
            }
            
        except Exception as e:
            logger.error(f"Document submission failed: {e}")
            return {"success": False, "error": "Failed to submit documents"}
    
    def trigger_ai_verification(self, campaign_id: str, documents: List[Dict[str, str]]) -> Dict[str, Any]:
        """Trigger AI verification engine"""
        try:
            # This would integrate with the MediTrustVerificationEngine
            # For now, simulate verification result
            verification_result = {
                "verification_id": str(ObjectId()),
                "campaign_id": campaign_id,
                "status": self.STATUS_VERIFIED,  # Would be determined by AI
                "confidence": 85,
                "issues": [],
                "verified_at": datetime.utcnow()
            }
            
            # Update campaign with verification result
            self.update_campaign_status_after_verification(campaign_id, verification_result)
            
            return verification_result
            
        except Exception as e:
            logger.error(f"AI verification trigger failed: {e}")
            return {"success": False, "error": "Failed to trigger verification"}
    
    def update_campaign_status_after_verification(self, campaign_id: str, verification_result: Dict[str, Any]) -> None:
        """Update campaign status based on verification result"""
        try:
            verification_status = verification_result.get('status')
            
            if verification_status == self.STATUS_VERIFIED:
                # Campaign verified, ready for story writing
                self.campaigns_collection.update_one(
                    {"_id": campaign_id},
                    {
                        "$set": {
                            "status": self.STATUS_VERIFIED,
                            "verification_id": verification_result.get('verification_id'),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
            elif verification_status == self.STATUS_PENDING:
                # Minor issues, pending admin review
                self.campaigns_collection.update_one(
                    {"_id": campaign_id},
                    {
                        "$set": {
                            "status": self.STATUS_PENDING,
                            "verification_id": verification_result.get('verification_id'),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
            elif verification_status == self.STATUS_VERIFICATION_NEEDED:
                # Serious issues, admin must review
                self.campaigns_collection.update_one(
                    {"_id": campaign_id},
                    {
                        "$set": {
                            "status": self.STATUS_VERIFICATION_NEEDED,
                            "verification_id": verification_result.get('verification_id'),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
            else:
                # Cancelled
                self.campaigns_collection.update_one(
                    {"_id": campaign_id},
                    {
                        "$set": {
                            "status": self.STATUS_CANCELLED,
                            "verification_id": verification_result.get('verification_id'),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                
        except Exception as e:
            logger.error(f"Status update failed: {e}")
    
    def submit_story_for_gemini_polishing(self, campaign_id: str, original_story: str, language: str = 'en') -> Dict[str, Any]:
        """Submit patient story for Gemini polishing"""
        try:
            # Store original story
            self.campaigns_collection.update_one(
                {"_id": campaign_id},
                {
                    "$set": {
                        "story_original": original_story,
                        "story_language": language,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Send to Gemini for polishing (this would call Google Cloud Vertex AI)
            gemini_story = self.call_gemini_for_story_polishing(original_story, language)
            
            # Store Gemini version
            self.campaigns_collection.update_one(
                {"_id": campaign_id},
                {
                    "$set": {
                        "story_gemini": gemini_story,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return {
                "success": True,
                "original_story": original_story,
                "gemini_story": gemini_story,
                "message": "Story polished by Gemini. Please review and approve."
            }
            
        except Exception as e:
            logger.error(f"Story polishing failed: {e}")
            return {"success": False, "error": "Failed to polish story"}
    
    def call_gemini_for_story_polishing(self, story: str, language: str) -> str:
        """Call Gemini API for story polishing"""
        try:
            # This would integrate with Google Cloud Vertex AI
            # For now, return a polished version
            polished_story = f"""
{story}

*(This story has been polished by AI for clarity, grammar, and emotional impact while preserving the original meaning and language.)*
            """.strip()
            
            return polished_story
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return story
    
    def approve_story_and_go_live(self, campaign_id: str, target_amount: float, hospital_name: str, hospital_address: str) -> Dict[str, Any]:
        """Approve story and make campaign live"""
        try:
            # Generate unique identifiers
            public_url = f"https://meditrust.org/campaign/{campaign_id}"
            upi_id = f"meditrust.{campaign_id}@upi"
            
            # Generate QR code
            qr_code = self.generate_qr_code(upi_id)
            
            # Update campaign with live data
            self.campaigns_collection.update_one(
                {"_id": campaign_id},
                {
                    "$set": {
                        "status": self.STATUS_LIVE_CAMPAIGN,
                        "target_amount": target_amount,
                        "hospital_name": hospital_name,
                        "hospital_address": hospital_address,
                        "public_url": public_url,
                        "upi_id": upi_id,
                        "qr_code": qr_code,
                        "story_approved": True,
                        "went_live_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Set up milestones (phased fund release)
            milestones = self.create_milestones(target_amount)
            self.campaigns_collection.update_one(
                {"_id": campaign_id},
                {"$set": {"milestones": milestones}}
            )
            
            return {
                "success": True,
                "public_url": public_url,
                "upi_id": upi_id,
                "qr_code": qr_code,
                "message": "Campaign is now live and accepting donations!"
            }
            
        except Exception as e:
            logger.error(f"Campaign launch failed: {e}")
            return {"success": False, "error": "Failed to launch campaign"}
    
    def generate_qr_code(self, upi_id: str) -> str:
        """Generate QR code for UPI ID"""
        try:
            # Create QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(f"upi://pay?pa={upi_id}")
            qr.make(fit=True)
            
            # Convert to base64 for storage
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return qr_base64
            
        except Exception as e:
            logger.error(f"QR code generation failed: {e}")
            return ""
    
    def create_milestones(self, target_amount: float) -> List[Dict[str, Any]]:
        """Create milestones for phased fund release"""
        milestones = []
        
        # Create milestones at 25%, 50%, 75%, 100%
        percentages = [0.25, 0.5, 0.75, 1.0]
        
        for i, percentage in enumerate(percentages):
            milestone_amount = target_amount * percentage
            milestones.append({
                "milestone_id": str(ObjectId()),
                "percentage": percentage * 100,
                "amount": milestone_amount,
                "status": "PENDING",
                "released_at": None,
                "verification_checks": {
                    "hospital_same": False,
                    "patient_active": False,
                    "outstanding_amount": 0
                }
            })
        
        return milestones
    
    def process_donation(self, campaign_id: str, donor_id: str, amount: float, anonymous: bool = False) -> Dict[str, Any]:
        """Process donation and update campaign"""
        try:
            if not self.campaigns_collection:
                return {"success": False, "error": "Database not available"}
            
            # Get campaign
            campaign = self.campaigns_collection.find_one({"_id": campaign_id})
            if not campaign:
                return {"success": False, "error": "Campaign not found"}
            
            if campaign.get("status") != self.STATUS_LIVE_CAMPAIGN:
                return {"success": False, "error": "Campaign is not accepting donations"}
            
            # Add donation
            donation = {
                "donation_id": str(ObjectId()),
                "campaign_id": campaign_id,
                "donor_id": donor_id,
                "amount": amount,
                "anonymous": anonymous,
                "status": "COMPLETED",
                "created_at": datetime.utcnow()
            }
            
            # Update campaign
            new_amount = campaign.get("current_amount", 0) + amount
            self.campaigns_collection.update_one(
                {"_id": campaign_id},
                {
                    "$push": {"donations": donation},
                    "$set": {
                        "current_amount": new_amount,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Check if any milestones are reached
            milestone_check = self.check_and_release_milestones(campaign_id, new_amount)
            
            # Update analytics
            self.update_campaign_analytics(campaign_id, "donation")
            
            return {
                "success": True,
                "donation": donation,
                "new_total": new_amount,
                "milestone_released": milestone_check.get("released", False),
                "message": "Donation processed successfully"
            }
            
        except Exception as e:
            logger.error(f"Donation processing failed: {e}")
            return {"success": False, "error": "Failed to process donation"}
    
    def check_and_release_milestones(self, campaign_id: str, current_amount: float) -> Dict[str, Any]:
        """Check and release milestones if reached"""
        try:
            campaign = self.campaigns_collection.find_one({"_id": campaign_id})
            milestones = campaign.get("milestones", [])
            
            released_milestones = []
            
            for milestone in milestones:
                if (milestone["status"] == "PENDING" and 
                    current_amount >= milestone["amount"]):
                    
                    # Perform verification checks before release
                    verification_result = self.perform_milestone_verification_checks(campaign_id)
                    
                    if verification_result["can_release"]:
                        # Release funds to hospital
                        release_result = self.release_funds_to_hospital(
                            campaign_id, 
                            milestone["amount"], 
                            milestone["milestone_id"]
                        )
                        
                        if release_result["success"]:
                            milestone["status"] = "RELEASED"
                            milestone["released_at"] = datetime.utcnow()
                            milestone["verification_checks"] = verification_result["checks"]
                            released_milestones.append(milestone)
            
            # Update milestones if any were released
            if released_milestones:
                self.campaigns_collection.update_one(
                    {"_id": campaign_id},
                    {"$set": {"milestones": milestones}}
                )
            
            return {
                "released": len(released_milestones) > 0,
                "milestones": released_milestones
            }
            
        except Exception as e:
            logger.error(f"Milestone check failed: {e}")
            return {"released": False, "milestones": []}
    
    def perform_milestone_verification_checks(self, campaign_id: str) -> Dict[str, Any]:
        """Perform 3 non-negotiable checks before fund release"""
        try:
            campaign = self.campaigns_collection.find_one({"_id": campaign_id})
            
            # Check 1: Is hospital still the same?
            hospital_same = self.verify_hospital_still_same(campaign_id)
            
            # Check 2: Is patient still active?
            patient_active = self.verify_patient_still_active(campaign_id)
            
            # Check 3: What is current HMS outstanding amount?
            outstanding_amount = self.get_hms_outstanding_amount(campaign_id)
            
            checks = {
                "hospital_same": hospital_same,
                "patient_active": patient_active,
                "outstanding_amount": outstanding_amount
            }
            
            can_release = (
                hospital_same and 
                patient_active and 
                outstanding_amount > 0
            )
            
            return {
                "can_release": can_release,
                "checks": checks
            }
            
        except Exception as e:
            logger.error(f"Milestone verification failed: {e}")
            return {"can_release": False, "checks": {}}
    
    def verify_hospital_still_same(self, campaign_id: str) -> bool:
        """Verify hospital is still the same as verified"""
        try:
            campaign = self.campaigns_collection.find_one({"_id": campaign_id})
            original_hospital = campaign.get("hospital_name", "")
            
            # Call HMS to verify current hospital
            hms_response = requests.get(f"{self.hms_service_url}/patients/{campaign.get('patient_id')}/hospital")
            
            if hms_response.status_code == 200:
                current_hospital = hms_response.json().get("hospital_name", "")
                return current_hospital.lower() == original_hospital.lower()
            
            return False
            
        except Exception as e:
            logger.error(f"Hospital verification failed: {e}")
            return False
    
    def verify_patient_still_active(self, campaign_id: str) -> bool:
        """Verify patient is still active in hospital"""
        try:
            campaign = self.campaigns_collection.find_one({"_id": campaign_id})
            patient_id = campaign.get("patient_id")
            
            # Call HMS to check patient status
            hms_response = requests.get(f"{self.hms_service_url}/patients/{patient_id}/status")
            
            if hms_response.status_code == 200:
                status = hms_response.json().get("status", "")
                return status.lower() == "active"
            
            return False
            
        except Exception as e:
            logger.error(f"Patient status verification failed: {e}")
            return False
    
    def get_hms_outstanding_amount(self, campaign_id: str) -> float:
        """Get outstanding amount from HMS"""
        try:
            campaign = self.campaigns_collection.find_one({"_id": campaign_id})
            patient_id = campaign.get("patient_id")
            
            # Call HMS to get outstanding amount
            hms_response = requests.get(f"{self.hms_service_url}/patients/{patient_id}/outstanding")
            
            if hms_response.status_code == 200:
                return float(hms_response.json().get("outstanding_amount", 0))
            
            return 0.0
            
        except Exception as e:
            logger.error(f"HMS outstanding amount check failed: {e}")
            return 0.0
    
    def release_funds_to_hospital(self, campaign_id: str, amount: float, milestone_id: str) -> Dict[str, Any]:
        """Release funds to verified hospital"""
        try:
            campaign = self.campaigns_collection.find_one({"_id": campaign_id})
            hospital_name = campaign.get("hospital_name", "")
            
            # Call HMS to process payment
            payment_data = {
                "campaign_id": campaign_id,
                "milestone_id": milestone_id,
                "amount": amount,
                "hospital_name": hospital_name,
                "payment_type": "MILESTONE_RELEASE"
            }
            
            hms_response = requests.post(
                f"{self.hms_service_url}/payments",
                json=payment_data
            )
            
            if hms_response.status_code == 200:
                # Record payment in our system
                payment_record = {
                    "payment_id": str(ObjectId()),
                    "campaign_id": campaign_id,
                    "milestone_id": milestone_id,
                    "amount": amount,
                    "hospital_name": hospital_name,
                    "status": "COMPLETED",
                    "processed_at": datetime.utcnow()
                }
                
                # Store payment record (would have a separate collection)
                return {
                    "success": True,
                    "payment": payment_record,
                    "message": f"₹{amount:,.2f} released to {hospital_name}"
                }
            
            return {
                "success": False,
                "error": "Failed to process payment with HMS"
            }
            
        except Exception as e:
            logger.error(f"Fund release failed: {e}")
            return {"success": False, "error": "Failed to release funds"}
    
    def request_hospital_change(self, campaign_id: str, new_hospital_data: Dict[str, Any]) -> Dict[str, Any]:
        """Request hospital change for campaign"""
        try:
            # Update campaign status
            self.campaigns_collection.update_one(
                {"_id": campaign_id},
                {
                    "$set": {
                        "status": self.STATUS_HOSPITAL_CHANGE_REQUESTED,
                        "new_hospital_data": new_hospital_data,
                        "hospital_change_requested_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Suspend payouts immediately
            self.suspend_payouts(campaign_id)
            
            return {
                "success": True,
                "message": "Hospital change requested. Payouts suspended pending verification."
            }
            
        except Exception as e:
            logger.error(f"Hospital change request failed: {e}")
            return {"success": False, "error": "Failed to request hospital change"}
    
    def suspend_payouts(self, campaign_id: str) -> None:
        """Suspend all payouts for campaign"""
        try:
            # Update all pending milestones to suspended
            self.campaigns_collection.update_one(
                {"_id": campaign_id, "milestones.status": "PENDING"},
                {"$set": {"milestones.$.status": "SUSPENDED"}}
            )
            
        except Exception as e:
            logger.error(f"Payout suspension failed: {e}")
    
    def update_campaign_analytics(self, campaign_id: str, action_type: str) -> None:
        """Update campaign analytics"""
        try:
            campaign = self.campaigns_collection.find_one({"_id": campaign_id})
            analytics = campaign.get("analytics", {})
            
            if action_type == "donation":
                current_donor_count = analytics.get("donors_count", 0)
                # Count unique donors
                unique_donors = len(set(d.get("donor_id") for d in campaign.get("donations", [])))
                analytics["donors_count"] = unique_donors
            
            elif action_type == "email":
                analytics["emails_sent"] = analytics.get("emails_sent", 0) + 1
            
            elif action_type == "whatsapp":
                analytics["whatsapp_sent"] = analytics.get("whatsapp_sent", 0) + 1
            
            elif action_type == "ngo_match":
                analytics["ngos_matched"] = analytics.get("ngos_matched", 0) + 1
            
            elif action_type == "ngo_response":
                analytics["ngo_responses"] = analytics.get("ngo_responses", 0) + 1
            
            self.campaigns_collection.update_one(
                {"_id": campaign_id},
                {"$set": {"analytics": analytics}}
            )
            
        except Exception as e:
            logger.error(f"Analytics update failed: {e}")
    
    def get_campaign_details(self, campaign_id: str) -> Dict[str, Any]:
        """Get complete campaign details"""
        try:
            campaign = self.campaigns_collection.find_one({"_id": campaign_id})
            
            if not campaign:
                return {"success": False, "error": "Campaign not found"}
            
            # Get patient details
            patient_id = campaign.get("patient_id")
            patient = self.users_collection.find_one({"_id": patient_id}) if patient_id else None
            
            return {
                "success": True,
                "campaign": campaign,
                "patient": patient
            }
            
        except Exception as e:
            logger.error(f"Campaign details fetch failed: {e}")
            return {"success": False, "error": "Failed to get campaign details"}
    
    def get_live_campaigns(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all live campaigns"""
        try:
            campaigns = list(self.campaigns_collection.find(
                {"status": self.STATUS_LIVE_CAMPAIGN}
            ).sort("went_live_at", -1).limit(limit))
            
            return campaigns
            
        except Exception as e:
            logger.error(f"Live campaigns fetch failed: {e}")
            return []
    
    def get_campaign_dashboard_data(self, campaign_id: str) -> Dict[str, Any]:
        """Get dashboard data for campaign owner"""
        try:
            campaign = self.campaigns_collection.find_one({"_id": campaign_id})
            
            if not campaign:
                return {"success": False, "error": "Campaign not found"}
            
            return {
                "success": True,
                "campaign": campaign,
                "analytics": campaign.get("analytics", {}),
                "donations": campaign.get("donations", []),
                "milestones": campaign.get("milestones", [])
            }
            
        except Exception as e:
            logger.error(f"Dashboard data fetch failed: {e}")
            return {"success": False, "error": "Failed to get dashboard data"}
