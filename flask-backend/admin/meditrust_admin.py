"""
MediTrust Admin System
Secure admin authentication and management with role-based access
"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from bson import ObjectId
import logging
import os
from functools import wraps

logger = logging.getLogger(__name__)

class MediTrustAdminManager:
    """Admin management system with secure authentication and role-based access"""
    
    def __init__(self, db, secret_key: str = None):
        """Initialize with database and JWT secret"""
        self.db = db
        self.admins_collection = db.admins if db is not None else None
        self.jwt_secret = secret_key or os.getenv('JWT_SECRET_KEY', 'admin-secret-key')
        self.jwt_algorithm = 'HS256'
        self.token_expiry = timedelta(hours=24)
        
        # Create default admin if none exists
        self.create_default_admin()
    
    def create_default_admin(self) -> None:
        """Create default admin if no admins exist"""
        try:
            if not self.admins_collection:
                return
            
            existing_admin = self.admins_collection.find_one({})
            if existing_admin:
                return
            
            # Create default admin
            default_admin = {
                "_id": str(ObjectId()),
                "admin_id": "admin_001",
                "username": "admin",
                "email": "admin@meditrust.org",
                "password_hash": self._hash_password("Admin@123!"),
                "role": "super_admin",
                "permissions": ["all"],
                "is_active": True,
                "created_at": datetime.utcnow(),
                "last_login": None,
                "login_attempts": 0,
                "locked_until": None
            }
            
            self.admins_collection.insert_one(default_admin)
            logger.info("Default admin created: admin / Admin@123!")
            
        except Exception as e:
            logger.error(f"Default admin creation failed: {e}")
    
    def admin_login(self, username: str, password: str, secret_key: str = None) -> Dict[str, Any]:
        """Authenticate admin login"""
        try:
            if not self.admins_collection:
                return {"success": False, "error": "Database not available"}
            
            # Check if admin is locked
            admin = self.admins_collection.find_one({"username": username})
            if not admin:
                return {"success": False, "error": "Invalid credentials"}
            
            # Check lock status
            if admin.get("locked_until") and admin["locked_until"] > datetime.utcnow():
                return {"success": False, "error": "Account temporarily locked"}
            
            # Verify secret key (second layer)
            if secret_key and secret_key != os.getenv('ADMIN_SECRET_KEY', 'MediTrust2024!'):
                self._record_failed_login(admin["_id"])
                return {"success": False, "error": "Invalid secret key"}
            
            # Verify password
            if not self._verify_password(password, admin["password_hash"]):
                self._record_failed_login(admin["_id"])
                return {"success": False, "error": "Invalid credentials"}
            
            # Check if admin is active
            if not admin.get("is_active", True):
                return {"success": False, "error": "Account deactivated"}
            
            # Reset failed attempts and update last login
            self.admins_collection.update_one(
                {"_id": admin["_id"]},
                {
                    "$set": {
                        "last_login": datetime.utcnow(),
                        "login_attempts": 0,
                        "locked_until": None
                    }
                }
            )
            
            # Generate JWT token
            token = self._generate_admin_token(admin)
            
            return {
                "success": True,
                "admin": {
                    "admin_id": admin["admin_id"],
                    "username": admin["username"],
                    "email": admin["email"],
                    "role": admin["role"],
                    "permissions": admin["permissions"]
                },
                "token": token,
                "expires_in": int(self.token_expiry.total_seconds()),
                "message": "Login successful"
            }
            
        except Exception as e:
            logger.error(f"Admin login failed: {e}")
            return {"success": False, "error": "Login failed"}
    
    def _record_failed_login(self, admin_id: str) -> None:
        """Record failed login attempt"""
        try:
            admin = self.admins_collection.find_one({"_id": admin_id})
            if not admin:
                return
            
            attempts = admin.get("login_attempts", 0) + 1
            update_data = {
                "$set": {
                    "login_attempts": attempts,
                    "updated_at": datetime.utcnow()
                }
            }
            
            # Lock account after 5 failed attempts for 30 minutes
            if attempts >= 5:
                update_data["$set"]["locked_until"] = datetime.utcnow() + timedelta(minutes=30)
            
            self.admins_collection.update_one({"_id": admin_id}, update_data)
            
        except Exception as e:
            logger.error(f"Failed login recording failed: {e}")
    
    def _generate_admin_token(self, admin: Dict[str, Any]) -> str:
        """Generate JWT token for admin"""
        try:
            payload = {
                "admin_id": admin["admin_id"],
                "username": admin["username"],
                "email": admin["email"],
                "role": admin["role"],
                "permissions": admin["permissions"],
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + self.token_expiry
            }
            
            token = jwt.encode(
                payload,
                self.jwt_secret,
                algorithm=self.jwt_algorithm
            )
            
            return token
            
        except Exception as e:
            logger.error(f"Token generation failed: {e}")
            return ""
    
    def verify_admin_token(self, token: str) -> Dict[str, Any]:
        """Verify admin JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            
            # Check if admin still exists and is active
            admin = self.admins_collection.find_one({"admin_id": payload["admin_id"]})
            if not admin or not admin.get("is_active", True):
                return {"valid": False, "error": "Admin not found or inactive"}
            
            return {
                "valid": True,
                "admin": {
                    "admin_id": payload["admin_id"],
                    "username": payload["username"],
                    "email": payload["email"],
                    "role": payload["role"],
                    "permissions": payload["permissions"]
                }
            }
            
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError:
            return {"valid": False, "error": "Invalid token"}
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return {"valid": False, "error": "Verification failed"}
    
    def create_admin(self, admin_data: Dict[str, Any], creator_id: str) -> Dict[str, Any]:
        """Create new admin (super admin only)"""
        try:
            if not self.admins_collection:
                return {"success": False, "error": "Database not available"}
            
            # Verify creator is super admin
            creator = self.admins_collection.find_one({"admin_id": creator_id})
            if not creator or creator.get("role") != "super_admin":
                return {"success": False, "error": "Insufficient permissions"}
            
            # Check if admin already exists
            existing = self.admins_collection.find_one({
                "$or": [
                    {"username": admin_data.get("username")},
                    {"email": admin_data.get("email")}
                ]
            })
            
            if existing:
                return {"success": False, "error": "Admin already exists"}
            
            # Create new admin
            new_admin = {
                "_id": str(ObjectId()),
                "admin_id": f"admin_{str(ObjectId())[-6:]}",
                "username": admin_data.get("username"),
                "email": admin_data.get("email"),
                "password_hash": self._hash_password(admin_data.get("password")),
                "role": admin_data.get("role", "admin"),
                "permissions": admin_data.get("permissions", ["view", "edit"]),
                "is_active": True,
                "created_by": creator_id,
                "created_at": datetime.utcnow(),
                "last_login": None,
                "login_attempts": 0,
                "locked_until": None
            }
            
            result = self.admins_collection.insert_one(new_admin)
            new_admin["_id"] = str(result.inserted_id)
            
            return {
                "success": True,
                "admin": {
                    "admin_id": new_admin["admin_id"],
                    "username": new_admin["username"],
                    "email": new_admin["email"],
                    "role": new_admin["role"],
                    "permissions": new_admin["permissions"]
                },
                "message": "Admin created successfully"
            }
            
        except Exception as e:
            logger.error(f"Admin creation failed: {e}")
            return {"success": False, "error": "Failed to create admin"}
    
    def get_pending_verifications(self) -> Dict[str, Any]:
        """Get all campaigns pending admin review"""
        try:
            if not self.db:
                return {"success": False, "error": "Database not available"}
            
            campaigns = list(self.db.campaigns.find({
                "status": {"$in": ["PENDING", "VERIFICATION_NEEDED", "HOSPITAL_CHANGE_REQUESTED"]}
            }).sort("updated_at", -1))
            
            # Get verification details for each campaign
            pending_campaigns = []
            for campaign in campaigns:
                verification_id = campaign.get("verification_id")
                verification = None
                
                if verification_id:
                    verification = self.db.verifications.find_one({"verification_id": verification_id})
                
                pending_campaigns.append({
                    "campaign": campaign,
                    "verification": verification,
                    "pending_reason": self._get_pending_reason(campaign["status"])
                })
            
            return {
                "success": True,
                "pending_campaigns": pending_campaigns,
                "count": len(pending_campaigns)
            }
            
        except Exception as e:
            logger.error(f"Pending verifications fetch failed: {e}")
            return {"success": False, "error": "Failed to get pending verifications"}
    
    def _get_pending_reason(self, status: str) -> str:
        """Get human-readable reason for pending status"""
        reasons = {
            "PENDING": "Minor issues detected - admin review needed",
            "VERIFICATION_NEEDED": "Serious issues detected - immediate admin review required",
            "HOSPITAL_CHANGE_REQUESTED": "Patient requested hospital change - re-verification needed"
        }
        return reasons.get(status, "Unknown pending status")
    
    def approve_verification(self, campaign_id: str, admin_id: str, notes: str = "") -> Dict[str, Any]:
        """Approve pending verification"""
        try:
            if not self.campaigns_collection:
                return {"success": False, "error": "Database not available"}
            
            # Get campaign
            campaign = self.campaigns_collection.find_one({"_id": campaign_id})
            if not campaign:
                return {"success": False, "error": "Campaign not found"}
            
            # Update campaign status
            new_status = "VERIFIED"
            if campaign.get("status") == "HOSPITAL_CHANGE_REQUESTED":
                new_status = "LIVE_UPDATED"
            
            self.campaigns_collection.update_one(
                {"_id": campaign_id},
                {
                    "$set": {
                        "status": new_status,
                        "admin_approved_by": admin_id,
                        "admin_approval_notes": notes,
                        "admin_approved_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "new_status": new_status,
                "message": f"Campaign {new_status.lower()} successfully"
            }
            
        except Exception as e:
            logger.error(f"Verification approval failed: {e}")
            return {"success": False, "error": "Failed to approve verification"}
    
    def cancel_verification(self, campaign_id: str, admin_id: str, reason: str, notes: str = "") -> Dict[str, Any]:
        """Cancel pending verification"""
        try:
            if not self.campaigns_collection:
                return {"success": False, "error": "Database not available"}
            
            # Get campaign
            campaign = self.campaigns_collection.find_one({"_id": campaign_id})
            if not campaign:
                return {"success": False, "error": "Campaign not found"}
            
            # Update campaign status
            self.campaigns_collection.update_one(
                {"_id": campaign_id},
                {
                    "$set": {
                        "status": "CANCELLED",
                        "admin_cancelled_by": admin_id,
                        "cancellation_reason": reason,
                        "admin_cancellation_notes": notes,
                        "cancelled_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "message": "Campaign cancelled successfully"
            }
            
        except Exception as e:
            logger.error(f"Verification cancellation failed: {e}")
            return {"success": False, "error": "Failed to cancel verification"}
    
    def get_admin_dashboard(self) -> Dict[str, Any]:
        """Get admin dashboard data"""
        try:
            if not self.db:
                return {"success": False, "error": "Database not available"}
            
            # Campaign statistics
            total_campaigns = self.db.campaigns.count_documents({})
            live_campaigns = self.db.campaigns.count_documents({"status": "LIVE_CAMPAIGN"})
            pending_campaigns = self.db.campaigns.count_documents({
                "status": {"$in": ["PENDING", "VERIFICATION_NEEDED"]}
            })
            completed_campaigns = self.db.campaigns.count_documents({"status": "COMPLETED"})
            
            # User statistics
            total_users = self.db.users.count_documents({})
            patients = self.db.users.count_documents({"user_type": "patient"})
            donors = self.db.users.count_documents({"user_type": "donor"})
            
            # Financial statistics
            total_donations = list(self.db.donations.find({}))
            total_amount = sum(d.get("amount", 0) for d in total_donations)
            
            # Recent activities
            recent_campaigns = list(self.db.campaigns.find({}).sort("updated_at", -1).limit(5))
            recent_verifications = list(self.db.verifications.find({}).sort("verification_timestamp", -1).limit(5))
            
            return {
                "success": True,
                "dashboard": {
                    "campaign_stats": {
                        "total": total_campaigns,
                        "live": live_campaigns,
                        "pending": pending_campaigns,
                        "completed": completed_campaigns
                    },
                    "user_stats": {
                        "total": total_users,
                        "patients": patients,
                        "donors": donors
                    },
                    "financial_stats": {
                        "total_donations": len(total_donations),
                        "total_amount": total_amount
                    },
                    "recent_activities": {
                        "campaigns": recent_campaigns,
                        "verifications": recent_verifications
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Dashboard data fetch failed: {e}")
            return {"success": False, "error": "Failed to get dashboard data"}
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        try:
            hashed = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt()
            )
            return hashed.decode("utf-8")
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            return ""
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8")
            )
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False


# Decorator for admin authentication
def require_admin_auth(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # This would be used in Flask routes
        # For now, return the function
        return f(*args, **kwargs)
    return decorated_function


# Decorator for admin permissions
def require_admin_permission(permission: str):
    """Decorator to require specific admin permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # This would be used in Flask routes
            # For now, return the function
            return f(*args, **kwargs)
        return decorated_function
    return decorator
