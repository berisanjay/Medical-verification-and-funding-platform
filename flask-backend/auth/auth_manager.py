"""
User Authentication and Management System
Handles patients, donors, and admin authentication
"""

import bcrypt
import jwt
from datetime import datetime, timedelta
from flask import current_app
from bson import ObjectId
import logging
import re

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages user authentication and authorization"""

    def __init__(self, db):
        """Initialize with database connection"""
        self.db = db
        self.users_collection = db.users if db is not None else None

    # ========================= REGISTER =========================
    def register_user(self, email, password, user_type, profile_data):

        if not self.users_collection:
            return {"success": False, "error": "Database not available"}

        try:
            # Validate email
            if not self._validate_email(email):
                return {"success": False, "error": "Invalid email format"}

            # Check existing user
            if self.users_collection.find_one({"email": email}):
                return {"success": False, "error": "Email already registered"}

            # Validate password
            if not self._validate_password(password):
                return {
                    "success": False,
                    "error": "Password must be at least 8 characters with 1 uppercase, 1 lowercase, 1 digit, and 1 special character"
                }

            # Hash password
            password_hash = self._hash_password(password)

            user = {
                "email": email,
                "password_hash": password_hash,
                "user_type": user_type,
                "profile": profile_data,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True,
                "email_verified": False
            }

            # Role specific fields
            if user_type == "patient":
                user.update({
                    "medical_conditions": [],
                    "campaigns": [],
                    "verification_status": "pending"
                })

            elif user_type == "donor":
                user.update({
                    "total_donated": 0,
                    "donations": [],
                    "preferences": {}
                })

            elif user_type == "admin":
                user.update({
                    "permissions": [
                        "manage_users",
                        "verify_documents",
                        "manage_campaigns"
                    ]
                })

            result = self.users_collection.insert_one(user)

            return {
                "success": True,
                "user_id": str(result.inserted_id),
                "message": f"{user_type.title()} registered successfully"
            }

        except Exception as e:
            logger.error("Registration error: %s", str(e))
            return {"success": False, "error": "Registration failed"}

    # ========================= LOGIN =========================
    def login_user(self, email, password):

        if not self.users_collection:
            return {"success": False, "error": "Database not available"}

        try:
            user = self.users_collection.find_one({"email": email})

            if not user:
                return {"success": False, "error": "Invalid credentials"}

            if not user.get("is_active", True):
                return {"success": False, "error": "Account is deactivated"}

            if not self._verify_password(password, user["password_hash"]):
                return {"success": False, "error": "Invalid credentials"}

            # Generate token
            token = self._generate_token(user)

            # Update last login
            self.users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"last_login": datetime.utcnow()}}
            )

            return {
                "success": True,
                "token": token,
                "user": {
                    "id": str(user["_id"]),
                    "email": user["email"],
                    "user_type": user["user_type"],
                    "profile": user.get("profile", {}),
                    "verification_status": user.get("verification_status")
                }
            }

        except Exception as e:
            logger.error("Login error: %s", str(e))
            return {"success": False, "error": "Login failed"}

    # ========================= VERIFY TOKEN =========================
    def verify_token(self, token):

        try:
            payload = jwt.decode(
                token,
                current_app.config.get("JWT_SECRET_KEY"),
                algorithms=["HS256"]
            )

            user_id = payload.get("user_id")

            if not user_id:
                return {"success": False, "error": "Invalid token"}

            user = self.users_collection.find_one(
                {"_id": ObjectId(user_id)}
            )

            if not user or not user.get("is_active", True):
                return {"success": False, "error": "User not found or inactive"}

            return {
                "success": True,
                "user": {
                    "id": str(user["_id"]),
                    "email": user["email"],
                    "user_type": user["user_type"],
                    "profile": user.get("profile", {})
                }
            }

        except jwt.ExpiredSignatureError:
            return {"success": False, "error": "Token expired"}

        except jwt.InvalidTokenError:
            return {"success": False, "error": "Invalid token"}

        except Exception as e:
            logger.error("Token verification error: %s", str(e))
            return {"success": False, "error": "Token verification failed"}

    # ========================= UPDATE PROFILE =========================
    def update_profile(self, user_id, profile_data):

        if not self.users_collection:
            return {"success": False, "error": "Database not available"}

        try:
            self.users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "profile": profile_data,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            return {"success": True, "message": "Profile updated successfully"}

        except Exception as e:
            logger.error("Profile update error: %s", str(e))
            return {"success": False, "error": "Profile update failed"}

    # ========================= HELPERS =========================
    def _validate_email(self, email):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def _validate_password(self, password):
        """Validate password strength"""
        if len(password) < 8:
            return False
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in password):
            return False
            
        # Check for at least one lowercase letter
        if not any(c.islower() for c in password):
            return False
            
        # Check for at least one digit
        if not any(c.isdigit() for c in password):
            return False
            
        # Check for at least one special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:'\",.<>?/"
        if not any(c in special_chars for c in password):
            return False
            
        return True

    def _hash_password(self, password):
        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        )
        return hashed.decode("utf-8")

    def _verify_password(self, password, password_hash):
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8")
        )

    def _generate_token(self, user):

        payload = {
            "user_id": str(user["_id"]),   # MUST convert to string
            "email": user["email"],
            "user_type": user["user_type"],
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }

        token = jwt.encode(
            payload,
            current_app.config.get("JWT_SECRET_KEY"),
            algorithm="HS256"
        )

        return token