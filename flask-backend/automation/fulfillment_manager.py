"""
Automated Campaign Fulfillment Detection and Management
Automatically checks for completed campaigns and handles notifications
"""
import threading
import time
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CampaignFulfillmentManager:
    """Manages automated campaign fulfillment detection"""
    
    def __init__(self, campaign_manager, notification_manager):
        """Initialize with campaign and notification managers"""
        self.campaign_manager = campaign_manager
        self.notification_manager = notification_manager
        self.running = False
        self.check_interval = 300  # Check every 5 minutes
    
    def start_monitoring(self):
        """Start the background monitoring thread"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_campaigns, daemon=True)
            self.monitor_thread.start()
            logger.info("Campaign fulfillment monitoring started")
    
    def stop_monitoring(self):
        """Stop the background monitoring thread"""
        self.running = False
        logger.info("Campaign fulfillment monitoring stopped")
    
    def _monitor_campaigns(self):
        """Background thread to monitor campaigns"""
        while self.running:
            try:
                self._check_completed_campaigns()
                self._check_expired_campaigns()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in campaign monitoring: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _check_completed_campaigns(self):
        """Check for campaigns that have reached their funding goal"""
        try:
            if not self.campaign_manager.campaigns_collection:
                return
            
            # Find campaigns that are active but have reached or exceeded target
            completed_campaigns = self.campaign_manager.campaigns_collection.find({
                "status": "active",
                "$expr": {"$gte": ["$current_amount", "$target_amount"]}
            })
            
            for campaign in completed_campaigns:
                campaign_id = str(campaign["_id"])
                logger.info(f"Campaign {campaign_id} has reached its funding goal")
                
                # Update campaign status
                self.campaign_manager.update_campaign_status(campaign_id, "completed")
                
                # Send fulfillment notifications
                self.notification_manager.send_campaign_fulfillment_notification(campaign["_id"])
                
                # Log the completion
                logger.info(f"Campaign {campaign_id} marked as completed and notifications sent")
        
        except Exception as e:
            logger.error(f"Error checking completed campaigns: {e}")
    
    def _check_expired_campaigns(self):
        """Check for campaigns that have passed their deadline"""
        try:
            if not self.campaign_manager.campaigns_collection:
                return
            
            # Find active campaigns that have passed their deadline
            expired_campaigns = self.campaign_manager.campaigns_collection.find({
                "status": "active",
                "deadline": {"$lt": datetime.utcnow()}
            })
            
            for campaign in expired_campaigns:
                campaign_id = str(campaign["_id"])
                logger.info(f"Campaign {campaign_id} has expired")
                
                # Update campaign status
                self.campaign_manager.update_campaign_status(campaign_id, "cancelled")
                
                # Send notifications to donors about expiration
                self._send_expiration_notifications(campaign)
                
                # Log the expiration
                logger.info(f"Campaign {campaign_id} marked as expired")
        
        except Exception as e:
            logger.error(f"Error checking expired campaigns: {e}")
    
    def _send_expiration_notifications(self, campaign):
        """Send notifications about campaign expiration"""
        try:
            # Get all donors for this campaign
            donations = self.campaign_manager.donations_collection.find({
                "campaign_id": campaign["_id"],
                "status": "completed",
                "anonymous": False
            })
            
            for donation in donations:
                donor = self.campaign_manager.db.users.find_one({"_id": donation["donor_id"]})
                if donor and donor.get("profile", {}).get("email"):
                    self._send_expiration_email(donor["profile"]["email"], campaign)
        
        except Exception as e:
            logger.error(f"Error sending expiration notifications: {e}")
    
    def _send_expiration_email(self, donor_email, campaign):
        """Send expiration email to donor"""
        try:
            subject = f"Campaign Update: {campaign['title']} Has Ended"
            
            body = f"""
            Dear Donor,
            
            We're writing to update you on a campaign you supported:
            
            Campaign: {campaign['title']}
            Medical Condition: {campaign['medical_condition']}
            
            This campaign has ended without reaching its funding goal.
            Final Amount Raised: ${campaign['current_amount']:,.2f}
            Goal: ${campaign['target_amount']:,.2f}
            
            While the campaign didn't reach its target, your contribution
            still made a difference. The patient may be able to use the
            funds raised for partial treatment or other medical expenses.
            
            Thank you for your generosity and support.
            
            With gratitude,
            The Medical Crowdfunding Team
            
            ---
            Campaign ID: {campaign['_id']}
            End Date: {datetime.now().strftime('%Y-%m-%d')}
            """
            
            self.notification_manager._send_email(donor_email, subject, body)
            
        except Exception as e:
            logger.error(f"Error sending expiration email: {e}")
    
    def check_campaign_manually(self, campaign_id):
        """Manually check a specific campaign for fulfillment"""
        try:
            campaign = self.campaign_manager.get_campaign(campaign_id)
            if not campaign:
                return {"success": False, "error": "Campaign not found"}
            
            if campaign["status"] != "active":
                return {"success": False, "error": "Campaign is not active"}
            
            # Check if campaign is completed
            if campaign["current_amount"] >= campaign["target_amount"]:
                # Update status and send notifications
                self.campaign_manager.update_campaign_status(campaign_id, "completed")
                self.notification_manager.send_campaign_fulfillment_notification(campaign_id)
                
                return {
                    "success": True,
                    "message": "Campaign marked as completed and notifications sent",
                    "status": "completed"
                }
            
            # Check if campaign is expired
            elif datetime.fromisoformat(campaign["deadline"].replace('Z', '+00:00')) < datetime.utcnow():
                self.campaign_manager.update_campaign_status(campaign_id, "cancelled")
                self._send_expiration_notifications(campaign)
                
                return {
                    "success": True,
                    "message": "Campaign marked as expired",
                    "status": "expired"
                }
            
            else:
                return {
                    "success": True,
                    "message": "Campaign is still active",
                    "status": "active"
                }
        
        except Exception as e:
            logger.error(f"Error checking campaign manually: {e}")
            return {"success": False, "error": "Failed to check campaign"}
