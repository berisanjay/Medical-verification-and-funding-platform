"""
Patient Campaign Management System
Handles creation, management, and tracking of patient fundraising campaigns
"""

from datetime import datetime, timedelta
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)


class CampaignManager:
    """Manages patient fundraising campaigns"""

    def __init__(self, db):
        """Initialize with database connection"""
        self.db = db
        self.campaigns_collection = db.campaigns if db is not None else None
        self.donations_collection = db.donations if db is not None else None

    # ========================= CREATE =========================
    def create_campaign(self, patient_id, campaign_data, verification_id=None):

        if self.campaigns_collection is None:
            return {"success": False, "error": "Database not available"}

        try:
            required_fields = ["title", "description", "target_amount", "medical_condition"]
            for field in required_fields:
                if not campaign_data.get(field):
                    return {"success": False, "error": f"Missing required field: {field}"}

            campaign = {
                "patient_id": ObjectId(patient_id),
                "title": campaign_data["title"],
                "description": campaign_data["description"],
                "medical_condition": campaign_data["medical_condition"],
                "target_amount": float(campaign_data["target_amount"]),
                "current_amount": 0.0,
                "verification_id": verification_id,
                "status": "pending_approval",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "deadline": datetime.utcnow() + timedelta(days=90),
                "donors": [],
                "updates": [],
                "documents": campaign_data.get("documents", []),
                "hospital_name": campaign_data.get("hospital_name"),
                "treating_doctor": campaign_data.get("treating_doctor"),
                "estimated_cost_breakdown": campaign_data.get("estimated_cost_breakdown", {}),
                "patient_story": campaign_data.get("patient_story", ""),
                "is_verified": verification_id is not None,
                "featured": False,
                "urgency_level": campaign_data.get("urgency_level", "medium")
            }

            result = self.campaigns_collection.insert_one(campaign)

            return {
                "success": True,
                "campaign_id": str(result.inserted_id),
                "message": "Campaign created successfully"
            }

        except Exception as e:
            logger.error("Campaign creation error: %s", str(e))
            return {"success": False, "error": "Campaign creation failed"}

    # ========================= GET ONE =========================
    def get_campaign(self, campaign_id):

        if self.campaigns_collection is None:
            return None

        try:
            campaign = self.campaigns_collection.find_one({"_id": ObjectId(campaign_id)})

            if campaign:
                campaign["_id"] = str(campaign["_id"])
                campaign["patient_id"] = str(campaign["patient_id"])

                if campaign["target_amount"] > 0:
                    campaign["progress_percentage"] = (
                        campaign["current_amount"] / campaign["target_amount"]
                    ) * 100
                else:
                    campaign["progress_percentage"] = 0

            return campaign

        except Exception as e:
            logger.error("Error getting campaign: %s", str(e))
            return None

    # ========================= GET ACTIVE =========================
    def get_active_campaigns(self, limit=20, skip=0):

        if self.campaigns_collection is None:
            return []

        try:
            campaigns = self.campaigns_collection.find({
                "status": "active",
                "deadline": {"$gt": datetime.utcnow()}
            }).sort("created_at", -1).skip(skip).limit(limit)

            return self._format_campaign_list(campaigns)

        except Exception as e:
            logger.error("Error getting active campaigns: %s", str(e))
            return []

    # ========================= GET BY PATIENT =========================
    def get_campaigns_by_patient(self, patient_id):

        if self.campaigns_collection is None:
            return []

        try:
            campaigns = self.campaigns_collection.find({
                "patient_id": ObjectId(patient_id)
            }).sort("created_at", -1)

            return self._format_campaign_list(campaigns)

        except Exception as e:
            logger.error("Error getting patient campaigns: %s", str(e))
            return []

    # ========================= UPDATE STATUS =========================
    def update_campaign_status(self, campaign_id, status):

        if self.campaigns_collection is None:
            return {"success": False, "error": "Database not available"}

        try:
            valid_statuses = ["pending_approval", "active", "completed", "paused", "cancelled"]

            if status not in valid_statuses:
                return {"success": False, "error": "Invalid status"}

            result = self.campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {"$set": {"status": status, "updated_at": datetime.utcnow()}}
            )

            if result.modified_count > 0:
                return {"success": True, "message": "Status updated successfully"}

            return {"success": False, "error": "Campaign not found"}

        except Exception as e:
            logger.error("Error updating campaign status: %s", str(e))
            return {"success": False, "error": "Status update failed"}

    # ========================= ADD UPDATE =========================
    def add_campaign_update(self, campaign_id, update_text, update_type="general"):

        if self.campaigns_collection is None:
            return {"success": False, "error": "Database not available"}

        try:
            update = {
                "text": update_text,
                "type": update_type,
                "created_at": datetime.utcnow()
            }

            result = self.campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {
                    "$push": {"updates": update},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )

            if result.modified_count > 0:
                return {"success": True, "message": "Update added successfully"}

            return {"success": False, "error": "Campaign not found"}

        except Exception as e:
            logger.error("Error adding campaign update: %s", str(e))
            return {"success": False, "error": "Failed to add update"}

    # ========================= FEATURED =========================
    def get_featured_campaigns(self, limit=5):

        if self.campaigns_collection is None:
            return []

        try:
            campaigns = self.campaigns_collection.find({
                "status": "active",
                "featured": True,
                "deadline": {"$gt": datetime.utcnow()}
            }).sort("created_at", -1).limit(limit)

            return self._format_campaign_list(campaigns)

        except Exception as e:
            logger.error("Error getting featured campaigns: %s", str(e))
            return []

    # ========================= SEARCH =========================
    def search_campaigns(self, query, limit=20):

        if self.campaigns_collection is None:
            return []

        try:
            search_filter = {
                "status": "active",
                "deadline": {"$gt": datetime.utcnow()},
                "$or": [
                    {"title": {"$regex": query, "$options": "i"}},
                    {"description": {"$regex": query, "$options": "i"}},
                    {"medical_condition": {"$regex": query, "$options": "i"}}
                ]
            }

            campaigns = self.campaigns_collection.find(search_filter)\
                .sort("created_at", -1).limit(limit)

            return self._format_campaign_list(campaigns)

        except Exception as e:
            logger.error("Error searching campaigns: %s", str(e))
            return []

    # ========================= HELPER =========================
    def _format_campaign_list(self, campaigns_cursor):
        """Convert ObjectIds and calculate progress"""

        result = []

        for campaign in campaigns_cursor:
            campaign["_id"] = str(campaign["_id"])
            campaign["patient_id"] = str(campaign["patient_id"])

            if campaign["target_amount"] > 0:
                campaign["progress_percentage"] = (
                    campaign["current_amount"] / campaign["target_amount"]
                ) * 100
            else:
                campaign["progress_percentage"] = 0

            result.append(campaign)

        return result