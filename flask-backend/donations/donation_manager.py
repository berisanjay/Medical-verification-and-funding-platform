"""
Donation Processing and Payment Integration
Handles donations, payment processing with Stripe, and fund tracking
"""
import stripe
from datetime import datetime
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)

class DonationManager:
    """Manages donations and payment processing"""
    
    def __init__(self, db, stripe_secret_key=None):
        """Initialize with database and Stripe configuration"""
        self.db = db
        self.donations_collection = db.donations if db is not None else None
        self.campaigns_collection = db.campaigns if db is not None else None
        
        # Initialize Stripe
        if stripe_secret_key:
            stripe.api_key = stripe_secret_key
            self.stripe_enabled = True
        else:
            self.stripe_enabled = False
            logger.warning("Stripe not configured - using mock payment processing")
    
    def create_donation(self, donor_id, campaign_id, amount, payment_method_id=None, anonymous=False):
        """
        Create and process a donation
        
        Args:
            donor_id: ID of the donor user
            campaign_id: ID of the campaign
            amount: Donation amount
            payment_method_id: Stripe payment method ID (optional)
            anonymous: Whether donation should be anonymous
        
        Returns:
            Dict with success status and donation details or error
        """
        if not self.donations_collection or not self.campaigns_collection:
            return {"success": False, "error": "Database not available"}
        
        try:
            # Validate campaign
            campaign = self.campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
            if not campaign:
                return {"success": False, "error": "Campaign not found"}
            
            if campaign["status"] != "active":
                return {"success": False, "error": "Campaign is not active"}
            
            if campaign["current_amount"] >= campaign["target_amount"]:
                return {"success": False, "error": "Campaign already funded"}
            
            # Process payment
            payment_result = self._process_payment(amount, payment_method_id)
            if not payment_result["success"]:
                return payment_result
            
            # Create donation record
            donation = {
                "donor_id": ObjectId(donor_id),
                "campaign_id": ObjectId(campaign_id),
                "amount": float(amount),
                "payment_intent_id": payment_result.get("payment_intent_id"),
                "payment_method": payment_result.get("payment_method", "stripe"),
                "anonymous": anonymous,
                "status": "completed",
                "created_at": datetime.utcnow(),
                "transaction_id": payment_result.get("transaction_id"),
                "fee": payment_result.get("fee", 0),
                "net_amount": float(amount) - payment_result.get("fee", 0)
            }
            
            # Save donation
            result = self.donations_collection.insert_one(donation)
            donation_id = str(result.inserted_id)
            
            # Update campaign funds
            self._update_campaign_funds(campaign_id, float(amount))
            
            # Update donor's total donated
            self._update_donor_stats(donor_id, float(amount))
            
            # Check if campaign is now fully funded
            self._check_campaign_fulfillment(campaign_id)
            
            logger.info(f"Created donation: {donation_id} for campaign: {campaign_id}")
            
            return {
                "success": True,
                "donation_id": donation_id,
                "amount": amount,
                "transaction_id": payment_result.get("transaction_id"),
                "message": "Donation processed successfully"
            }
            
        except Exception as e:
            logger.error(f"Donation creation error: {e}")
            return {"success": False, "error": "Donation processing failed"}
    
    def get_donation_history(self, donor_id=None, campaign_id=None, limit=50):
        """Get donation history with filters"""
        if not self.donations_collection:
            return []
        
        try:
            # Build filter
            filter_dict = {"status": "completed"}
            if donor_id:
                filter_dict["donor_id"] = ObjectId(donor_id)
            if campaign_id:
                filter_dict["campaign_id"] = ObjectId(campaign_id)
            
            donations = self.donations_collection.find(filter_dict).sort("created_at", -1).limit(limit)
            
            result = []
            for donation in donations:
                donation["_id"] = str(donation["_id"])
                donation["donor_id"] = str(donation["donor_id"])
                donation["campaign_id"] = str(donation["campaign_id"])
                result.append(donation)
            
            return result
        except Exception as e:
            logger.error(f"Error getting donation history: {e}")
            return []
    
    def get_campaign_donations(self, campaign_id):
        """Get all donations for a specific campaign"""
        return self.get_donation_history(campaign_id=campaign_id)
    
    def get_donor_donations(self, donor_id):
        """Get all donations by a specific donor"""
        return self.get_donation_history(donor_id=donor_id)
    
    def get_donation_stats(self, campaign_id=None):
        """Get donation statistics"""
        if not self.donations_collection:
            return {}
        
        try:
            filter_dict = {"status": "completed"}
            if campaign_id:
                filter_dict["campaign_id"] = ObjectId(campaign_id)
            
            # Aggregate stats
            pipeline = [
                {"$match": filter_dict},
                {
                    "$group": {
                        "_id": None,
                        "total_amount": {"$sum": "$amount"},
                        "total_donations": {"$sum": 1},
                        "average_donation": {"$avg": "$amount"},
                        "unique_donors": {"$addToSet": "$donor_id"}
                    }
                }
            ]
            
            result = list(self.donations_collection.aggregate(pipeline))
            if result:
                stats = result[0]
                stats["unique_donors_count"] = len(stats["unique_donors"])
                del stats["unique_donors"]
                return stats
            
            return {
                "total_amount": 0,
                "total_donations": 0,
                "average_donation": 0,
                "unique_donors_count": 0
            }
            
        except Exception as e:
            logger.error(f"Error getting donation stats: {e}")
            return {}
    
    def refund_donation(self, donation_id, reason=""):
        """Process a refund for a donation"""
        if not self.donations_collection:
            return {"success": False, "error": "Database not available"}
        
        try:
            donation = self.donations_collection.find_one({"_id": ObjectId(donation_id)})
            if not donation:
                return {"success": False, "error": "Donation not found"}
            
            if donation["status"] != "completed":
                return {"success": False, "error": "Donation cannot be refunded"}
            
            # Process refund with Stripe if applicable
            if self.stripe_enabled and donation.get("payment_intent_id"):
                try:
                    refund = stripe.Refund.create(
                        payment_intent=donation["payment_intent_id"],
                        reason=reason or "requested_by_customer"
                    )
                    refund_id = refund.id
                except Exception as e:
                    logger.error(f"Stripe refund error: {e}")
                    return {"success": False, "error": "Refund processing failed"}
            else:
                refund_id = f"mock_refund_{datetime.utcnow().timestamp()}"
            
            # Update donation status
            self.donations_collection.update_one(
                {"_id": ObjectId(donation_id)},
                {
                    "$set": {
                        "status": "refunded",
                        "refund_id": refund_id,
                        "refund_reason": reason,
                        "refunded_at": datetime.utcnow()
                    }
                }
            )
            
            # Update campaign funds (subtract the refunded amount)
            self._update_campaign_funds(donation["campaign_id"], -donation["amount"])
            
            logger.info(f"Refunded donation: {donation_id}")
            
            return {"success": True, "message": "Refund processed successfully"}
            
        except Exception as e:
            logger.error(f"Refund error: {e}")
            return {"success": False, "error": "Refund failed"}
    
    def _process_payment(self, amount, payment_method_id=None):
        """Process payment via Stripe or mock"""
        if self.stripe_enabled and payment_method_id:
            try:
                # Create payment intent
                payment_intent = stripe.PaymentIntent.create(
                    amount=int(amount * 100),  # Convert to cents
                    currency='usd',
                    payment_method=payment_method_id,
                    confirm=True,
                    automatic_payment_methods={'enabled': True}
                )
                
                if payment_intent.status == 'succeeded':
                    return {
                        "success": True,
                        "payment_intent_id": payment_intent.id,
                        "transaction_id": payment_intent.id,
                        "payment_method": "stripe",
                        "fee": amount * 0.029 + 0.30  # Standard Stripe fees
                    }
                else:
                    return {"success": False, "error": "Payment failed"}
                    
            except Exception as e:
                logger.error(f"Stripe payment error: {e}")
                return {"success": False, "error": "Payment processing failed"}
        else:
            # Mock payment processing
            return {
                "success": True,
                "payment_intent_id": f"mock_payment_{datetime.utcnow().timestamp()}",
                "transaction_id": f"mock_txn_{datetime.utcnow().timestamp()}",
                "payment_method": "mock",
                "fee": 0
            }
    
    def _update_campaign_funds(self, campaign_id, amount):
        """Update campaign current amount"""
        try:
            self.campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {
                    "$inc": {"current_amount": amount},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
        except Exception as e:
            logger.error(f"Error updating campaign funds: {e}")
    
    def _update_donor_stats(self, donor_id, amount):
        """Update donor's total donated amount"""
        try:
            self.db.users.update_one(
                {"_id": ObjectId(donor_id)},
                {
                    "$inc": {"total_donated": amount},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
        except Exception as e:
            logger.error(f"Error updating donor stats: {e}")
    
    def _check_campaign_fulfillment(self, campaign_id):
        """Check if campaign is fully funded and update status"""
        try:
            campaign = self.campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
            if campaign and campaign["current_amount"] >= campaign["target_amount"]:
                self.campaigns_collection.update_one(
                    {"_id": ObjectId(campaign_id)},
                    {
                        "$set": {
                            "status": "completed",
                            "completed_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                logger.info(f"Campaign {campaign_id} is now fully funded")
                # Trigger notification system here
                return True
        except Exception as e:
            logger.error(f"Error checking campaign fulfillment: {e}")
        return False
