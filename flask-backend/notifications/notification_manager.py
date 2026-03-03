"""
Notification System for Campaign Fulfillment and Updates
Handles email notifications to donors and patients
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manages email notifications for campaigns and donations"""
    
    def __init__(self, db, email_config=None):
        """Initialize with database and email configuration"""
        self.db = db
        self.users_collection = db.users if db is not None else None
        self.campaigns_collection = db.campaigns if db is not None else None
        self.donations_collection = db.donations if db is not None else None
        
        # Email configuration
        self.email_config = email_config or {
            "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "sender_email": os.getenv("SENDER_EMAIL", ""),
            "sender_password": os.getenv("SENDER_PASSWORD", ""),
            "sender_name": os.getenv("SENDER_NAME", "Medical Crowdfunding Platform")
        }
        
        self.email_enabled = bool(self.email_config["sender_email"] and self.email_config["sender_password"])
    
    def send_campaign_fulfillment_notification(self, campaign_id):
        """Send notifications when a campaign is fully funded"""
        if not self.email_enabled or not self.donations_collection:
            logger.warning("Email not configured or database unavailable")
            return False
        
        try:
            # Get campaign details
            campaign = self.campaigns_collection.find_one({"_id": campaign_id})
            if not campaign:
                logger.error(f"Campaign not found: {campaign_id}")
                return False
            
            # Get all donors for this campaign
            donors = self.donations_collection.find({
                "campaign_id": campaign_id,
                "status": "completed",
                "anonymous": False
            })
            
            # Send email to each donor
            success_count = 0
            for donation in donors:
                donor = self.users_collection.find_one({"_id": donation["donor_id"]})
                if donor and donor.get("profile", {}).get("email"):
                    if self._send_fulfillment_email(donor["profile"]["email"], campaign, donation):
                        success_count += 1
            
            # Send notification to patient
            patient = self.users_collection.find_one({"_id": campaign["patient_id"]})
            if patient and patient.get("profile", {}).get("email"):
                self._send_patient_fulfillment_email(patient["profile"]["email"], campaign)
            
            logger.info(f"Sent fulfillment notifications for campaign {campaign_id}: {success_count} donors")
            return True
            
        except Exception as e:
            logger.error(f"Error sending fulfillment notifications: {e}")
            return False
    
    def send_donation_receipt(self, donor_id, donation_id):
        """Send donation receipt to donor"""
        if not self.email_enabled or not self.donations_collection:
            return False
        
        try:
            # Get donation and donor details
            donation = self.donations_collection.find_one({"_id": ObjectId(donation_id)})
            donor = self.users_collection.find_one({"_id": ObjectId(donor_id)})
            
            if not donation or not donor:
                return False
            
            campaign = self.campaigns_collection.find_one({"_id": donation["campaign_id"]})
            if not campaign:
                return False
            
            donor_email = donor.get("profile", {}).get("email")
            if not donor_email:
                return False
            
            return self._send_donation_receipt_email(donor_email, donation, campaign)
            
        except Exception as e:
            logger.error(f"Error sending donation receipt: {e}")
            return False
    
    def send_campaign_update_notification(self, campaign_id, update_text):
        """Send campaign update to all donors"""
        if not self.email_enabled:
            return False
        
        try:
            campaign = self.campaigns_collection.find_one({"_id": campaign_id})
            if not campaign:
                return False
            
            # Get all donors
            donors = self.donations_collection.find({
                "campaign_id": campaign_id,
                "status": "completed",
                "anonymous": False
            })
            
            success_count = 0
            for donation in donors:
                donor = self.users_collection.find_one({"_id": donation["donor_id"]})
                if donor and donor.get("profile", {}).get("email"):
                    if self._send_update_email(donor["profile"]["email"], campaign, update_text):
                        success_count += 1
            
            logger.info(f"Sent update notifications for campaign {campaign_id}: {success_count} donors")
            return True
            
        except Exception as e:
            logger.error(f"Error sending update notifications: {e}")
            return False
    
    def send_welcome_email(self, user_email, user_type, user_name):
        """Send welcome email to new users"""
        if not self.email_enabled:
            return False
        
        try:
            return self._send_welcome_email(user_email, user_type, user_name)
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
            return False
    
    def _send_fulfillment_email(self, donor_email, campaign, donation):
        """Send fulfillment notification to donor"""
        try:
            subject = f"Great News! {campaign['title']} is Now Fully Funded!"
            
            body = f"""
            Dear Donor,
            
            We're excited to share some wonderful news! The medical campaign you supported:
            
            Campaign: {campaign['title']}
            Patient: {campaign.get('patient_name', 'Anonymous Patient')}
            Medical Condition: {campaign['medical_condition']}
            
            has reached its funding goal of ${campaign['target_amount']:,.2f}!
            
            Your generous donation of ${donation['amount']:,.2f} helped make this possible.
            Together with {self._get_donor_count(campaign['_id'])} other donors, you've helped
            provide critical medical care to someone in need.
            
            The patient will now be able to receive the necessary treatment, and we'll
            continue to share updates on their progress.
            
            Thank you for your compassion and generosity. You've truly made a difference
            in someone's life.
            
            With gratitude,
            The Medical Crowdfunding Team
            
            ---
            Campaign ID: {campaign['_id']}
            Donation ID: {donation['_id']}
            Date: {datetime.now().strftime('%Y-%m-%d')}
            """
            
            return self._send_email(donor_email, subject, body)
            
        except Exception as e:
            logger.error(f"Error sending fulfillment email: {e}")
            return False
    
    def _send_patient_fulfillment_email(self, patient_email, campaign):
        """Send fulfillment notification to patient"""
        try:
            subject = f"Congratulations! Your Campaign is Fully Funded!"
            
            body = f"""
            Dear Patient,
            
            We have wonderful news! Your medical fundraising campaign:
            
            Campaign: {campaign['title']}
            Medical Condition: {campaign['medical_condition']}
            Target Amount: ${campaign['target_amount']:,.2f}
            Amount Raised: ${campaign['current_amount']:,.2f}
            
            has been fully funded! Thanks to the generosity of {self._get_donor_count(campaign['_id'])} donors,
            you've raised the complete amount needed for your treatment.
            
            Next Steps:
            1. We will coordinate with the hospital to process the payment
            2. You'll receive updates on the payment process
            3. We'll continue to support you throughout your treatment journey
            
            Please keep us updated on your progress, and don't hesitate to reach out
            if you need any assistance.
            
            Wishing you a speedy recovery,
            The Medical Crowdfunding Team
            
            ---
            Campaign ID: {campaign['_id']}
            Date: {datetime.now().strftime('%Y-%m-%d')}
            """
            
            return self._send_email(patient_email, subject, body)
            
        except Exception as e:
            logger.error(f"Error sending patient fulfillment email: {e}")
            return False
    
    def _send_donation_receipt_email(self, donor_email, donation, campaign):
        """Send donation receipt to donor"""
        try:
            subject = f"Donation Receipt - {campaign['title']}"
            
            body = f"""
            Dear Donor,
            
            Thank you for your generous donation! This is your official receipt:
            
            Donation Details:
            - Campaign: {campaign['title']}
            - Amount: ${donation['amount']:,.2f}
            - Date: {donation['created_at'].strftime('%Y-%m-%d %H:%M:%S')}
            - Transaction ID: {donation.get('transaction_id', 'N/A')}
            - Donation ID: {donation['_id']}
            
            Campaign Progress:
            - Total Raised: ${campaign['current_amount']:,.2f}
            - Goal: ${campaign['target_amount']:,.2f}
            - Progress: {(campaign['current_amount']/campaign['target_amount']*100):.1f}%
            
            Your contribution is tax-deductible to the extent allowed by law.
            Please keep this email for your records.
            
            We'll keep you updated on the campaign's progress and notify you
            when the funding goal is reached.
            
            With gratitude,
            The Medical Crowdfunding Team
            
            ---
            This is an automated receipt. For questions, please contact our support team.
            """
            
            return self._send_email(donor_email, subject, body)
            
        except Exception as e:
            logger.error(f"Error sending donation receipt: {e}")
            return False
    
    def _send_update_email(self, donor_email, campaign, update_text):
        """Send campaign update to donor"""
        try:
            subject = f"Update: {campaign['title']}"
            
            body = f"""
            Dear Donor,
            
            There's an update for the campaign you supported:
            
            Campaign: {campaign['title']}
            Current Progress: ${campaign['current_amount']:,.2f} / ${campaign['target_amount']:,.2f}
            
            Update:
            {update_text}
            
            Thank you for your continued support. We appreciate your generosity
            and commitment to helping this patient.
            
            Best regards,
            The Medical Crowdfunding Team
            
            ---
            Campaign ID: {campaign['_id']}
            Date: {datetime.now().strftime('%Y-%m-%d')}
            """
            
            return self._send_email(donor_email, subject, body)
            
        except Exception as e:
            logger.error(f"Error sending update email: {e}")
            return False
    
    def _send_welcome_email(self, user_email, user_type, user_name):
        """Send welcome email to new user"""
        try:
            subject = "Welcome to the Medical Crowdfunding Platform"
            
            if user_type == "patient":
                body = f"""
                Dear {user_name},
                
                Welcome to our Medical Crowdfunding Platform! We're here to help you
                raise funds for your medical treatment.
                
                Getting Started:
                1. Complete your profile information
                2. Upload your medical documents for verification
                3. Create your fundraising campaign
                4. Share your story with potential donors
                
                Our team will review your documents and help you through every step
                of the process.
                
                If you have any questions, please don't hesitate to reach out.
                
                With care and support,
                The Medical Crowdfunding Team
                """
            elif user_type == "donor":
                body = f"""
                Dear {user_name},
                
                Thank you for joining our Medical Crowdfunding Platform! Your
                generosity can make a life-changing difference for patients in need.
                
                How You Can Help:
                1. Browse active campaigns
                2. Read patient stories
                3. Donate to causes that resonate with you
                4. Share campaigns with your network
                
                Every contribution, no matter the size, brings hope to someone
                fighting a medical condition.
                
                Together, we can make healthcare accessible to all.
                
                With gratitude,
                The Medical Crowdfunding Team
                """
            else:
                body = f"""
                Dear {user_name},
                
                Welcome to the Medical Crowdfunding Platform! We're glad to have you
                as part of our community dedicated to helping patients in need.
                
                Thank you for joining us in this important mission.
                
                Best regards,
                The Medical Crowdfunding Team
                """
            
            return self._send_email(user_email, subject, body)
            
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
            return False
    
    def _send_email(self, to_email, subject, body):
        """Send email using SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = f"{self.email_config['sender_name']} <{self.email_config['sender_email']}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['sender_email'], self.email_config['sender_password'])
            
            text = msg.as_string()
            server.sendmail(self.email_config['sender_email'], to_email, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def _get_donor_count(self, campaign_id):
        """Get number of unique donors for a campaign"""
        try:
            return self.donations_collection.count_documents({
                "campaign_id": campaign_id,
                "status": "completed"
            })
        except:
            return 0
