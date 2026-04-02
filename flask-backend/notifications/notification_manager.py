"""
MediTrust Notification Manager
Handles all email notifications via SMTP + Gmail
No database queries — Node.js backend passes all required data
"""

import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

class NotificationManager:
    """Sends email notifications for MediTrust platform"""

    def __init__(self):
        self.smtp_server   = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port     = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email  = os.getenv("EMAIL_USER", "")
        self.sender_password = os.getenv("EMAIL_APP_PASSWORD", "")
        self.sender_name   = os.getenv("SENDER_NAME", "MediTrust Platform")
        self.enabled = bool(self.sender_email and self.sender_password)

        if not self.enabled:
            logger.warning("Email not configured — notifications disabled")

    # ─────────────────────────────────────────
    # PUBLIC METHODS — called from Node.js backend
    # ─────────────────────────────────────────

    def send_welcome_email(self, to_email, patient_name, language="en"):
        """Send welcome email after patient registration"""
        subject = "Welcome to MediTrust — Your Verified Medical Crowdfunding Platform"
        body = self._welcome_body(patient_name)
        return self._send(to_email, subject, body)

    def send_otp_email(self, to_email, otp_code, purpose="registration"):
        """Send OTP email for registration / campaign creation / hospital change"""
        purposes = {
            "registration"    : "complete your registration",
            "campaign"        : "create your campaign",
            "hospital_change" : "confirm hospital change request",
            "admin_login"     : "complete admin login"
        }
        action = purposes.get(purpose, "verify your action")
        subject = f"MediTrust — Your OTP to {action}"
        body = self._otp_body(otp_code, action)
        return self._send(to_email, subject, body)

    def send_verification_status_email(self, to_email, patient_name, status, campaign_title, reason=None):
        """Notify patient about their document verification result"""
        status_messages = {
            "VERIFIED"             : "Your documents have been verified successfully!",
            "PENDING"              : "Your documents are under admin review.",
            "VERIFICATION_NEEDED"  : "Admin review required — issues found in your documents.",
            "UPDATE_NEEDED"        : "Your hospital estimate has expired. Please upload fresh documents.",
            "CANCELLED"            : "Your campaign has been cancelled after review."
        }
        subject = f"MediTrust — Document Verification Update: {status}"
        body = self._verification_body(patient_name, campaign_title, status, status_messages.get(status, ""), reason)
        return self._send(to_email, subject, body)

    def send_campaign_live_email(self, to_email, patient_name, campaign_title, public_url, upi_id):
        """Notify patient that campaign is now live"""
        subject = f"MediTrust — Your Campaign is Now LIVE!"
        body = self._campaign_live_body(patient_name, campaign_title, public_url, upi_id)
        return self._send(to_email, subject, body)

    def send_donation_receipt(self, to_email, donor_name, campaign_title,
                               amount, transaction_id, donated_at):
        """Send PDF-style donation receipt to donor after successful payment"""
        subject = f"MediTrust — Donation Receipt for {campaign_title}"
        body = self._donation_receipt_body(donor_name, campaign_title, amount, transaction_id, donated_at)
        return self._send(to_email, subject, body)

    def send_fund_release_notification(self, to_email, patient_name, campaign_title,
                                        amount_released, outstanding_remaining):
        """Notify patient when funds are released to hospital"""
        subject = f"MediTrust — Funds Released to Hospital"
        body = self._fund_release_body(patient_name, campaign_title, amount_released, outstanding_remaining)
        return self._send(to_email, subject, body)

    def send_campaign_completed_email(self, to_email, donor_name, campaign_title,
                                       total_raised, donor_amount):
        """Notify donor that campaign is fully funded — excess fund info included"""
        subject = f"MediTrust — Campaign Fully Funded: {campaign_title}"
        body = self._campaign_completed_body(donor_name, campaign_title, total_raised, donor_amount)
        return self._send(to_email, subject, body)

    def send_hospital_change_notification(self, to_email, ngo_name, campaign_title,
                                           patient_name, old_hospital, new_hospital):
        """Notify NGO about hospital change in a campaign they are linked to"""
        subject = f"MediTrust — Hospital Change Alert: {campaign_title}"
        body = self._hospital_change_body(ngo_name, campaign_title, patient_name, old_hospital, new_hospital)
        return self._send(to_email, subject, body)

    def send_ngo_match_email(self, to_email, ngo_name, campaign_title,
                              patient_name, disease, hospital_name,
                              hospital_city, documents_url):
        """Send matched campaign details to NGO for potential funding"""
        subject = f"MediTrust — NGO Support Request: {campaign_title}"
        body = self._ngo_match_body(ngo_name, campaign_title, patient_name,
                                    disease, hospital_name, hospital_city, documents_url)
        return self._send(to_email, subject, body)

    def send_hospital_suggestion_email(self, to_email, patient_name,
                                        disease, suggestions, language="en"):
        """Send validated hospital suggestions to patient in their native language"""
        subject = "MediTrust — Hospital Suggestions for Your Case"
        body = self._suggestion_body(patient_name, disease, suggestions)
        return self._send(to_email, subject, body)

    def send_campaign_update_email(self, to_email, donor_name, campaign_title, update_text):
        """Notify donor of a successful campaign milestone update"""
        subject = f"MediTrust — Update: {campaign_title}"
        body = self._update_body(donor_name, campaign_title, update_text)
        return self._send(to_email, subject, body)

    def send_blacklist_notification(self, to_email, name):
        """Notify user their account has been suspended due to fraud"""
        subject = "MediTrust — Account Suspended"
        body = self._blacklist_body(name)
        return self._send(to_email, subject, body)

    # ─────────────────────────────────────────
    # EMAIL BODY BUILDERS
    # ─────────────────────────────────────────

    def _welcome_body(self, name):
        return f"""
Dear {name},

Welcome to MediTrust — India's AI-powered transparent medical crowdfunding platform.

Your account has been created successfully.

What happens next:
1. Create your campaign and upload your medical documents
2. Our AI system will verify your documents automatically
3. Once verified, write your story — Gemini AI will help polish it
4. Your campaign goes LIVE with a unique QR code and UPI ID
5. Donations will be released directly to your verified hospital in phases

We are here to support you through every step.

With care,
Team MediTrust

---
This is an automated email. Please do not reply.
"""

    def _otp_body(self, otp, action):
        return f"""
Dear User,

Your OTP to {action} on MediTrust is:

    {otp}

This OTP is valid for 10 minutes. Do not share this with anyone.

If you did not request this OTP, please ignore this email.

With care,
Team MediTrust

---
This is an automated email. Please do not reply.
"""

    def _verification_body(self, name, campaign_title, status, message, reason):
        reason_text = f"\nReason: {reason}" if reason else ""
        return f"""
Dear {name},

Update on your campaign: {campaign_title}

Verification Status: {status}
{message}
{reason_text}

Please login to your MediTrust dashboard for more details.

With care,
Team MediTrust

---
This is an automated email. Please do not reply.
"""

    def _campaign_live_body(self, name, title, url, upi_id):
        return f"""
Dear {name},

Congratulations! Your campaign is now LIVE on MediTrust.

Campaign: {title}
Public URL: {url}
UPI ID for donations: {upi_id}

Share this link with your family, friends, and community.
Funds collected will be released directly to your verified hospital in phases.

We wish you a speedy recovery.

With care,
Team MediTrust

---
This is an automated email. Please do not reply.
"""

    def _donation_receipt_body(self, donor_name, campaign_title, amount, txn_id, donated_at):
        return f"""
Dear {donor_name},

Thank you for your generous donation! Here is your receipt:

Campaign    : {campaign_title}
Amount      : Rs. {amount:,.2f}
Date        : {donated_at}
Transaction : {txn_id}

Your donation will be released directly to the verified hospital.
We will notify you when the campaign reaches its goal.

With gratitude,
Team MediTrust

---
Please keep this email for your records.
This is an automated email. Please do not reply.
"""

    def _fund_release_body(self, name, title, released, remaining):
        return f"""
Dear {name},

Funds have been released to your verified hospital.

Campaign          : {title}
Amount Released   : Rs. {released:,.2f}
Outstanding Left  : Rs. {remaining:,.2f}
Date              : {datetime.now().strftime('%d %B %Y')}

Please login to your dashboard for full release history.

With care,
Team MediTrust

---
This is an automated email. Please do not reply.
"""

    def _campaign_completed_body(self, donor_name, title, total, your_amount):
        return f"""
Dear {donor_name},

Great news! The campaign you supported has been fully funded.

Campaign         : {title}
Total Raised     : Rs. {total:,.2f}
Your Donation    : Rs. {your_amount:,.2f}

The full treatment cost has been paid to the verified hospital.
Any excess amount collected will be utilized for similar medical cases.

Thank you for making a difference in someone's life.

With gratitude,
Team MediTrust

---
This is an automated email. Please do not reply.
"""

    def _hospital_change_body(self, ngo_name, title, patient, old_hospital, new_hospital):
        return f"""
Dear {ngo_name},

This is to inform you of a hospital change in a campaign you are linked to.

Campaign      : {title}
Patient       : {patient}
Old Hospital  : {old_hospital}
New Hospital  : {new_hospital}
Status        : Under Re-Verification

IMPORTANT: All payouts have been suspended until re-verification is complete.
If you plan to send funds, please verify the new hospital directly before releasing any amount.

Latest status is always available on your MediTrust dashboard.

Disclaimer: Funding approvals are valid only against the currently verified hospital.
NGOs must confirm hospital billing before releasing funds.

With regards,
Team MediTrust

---
This is an automated email. Please do not reply.
"""

    def _ngo_match_body(self, ngo_name, title, patient, disease,
                         hospital, city, docs_url):
        return f"""
Dear {ngo_name},

MediTrust has identified a case that matches your NGO's area of support.

Campaign      : {title}
Patient       : {patient}
Disease       : {disease}
Hospital      : {hospital}
Hospital City : {city}
Documents     : {docs_url}

All documents have been AI-verified by MediTrust before this notification was sent.

If you wish to support this case, please contact the hospital directly and
verify patient admission and outstanding billing before releasing any funds.

MediTrust is responsible only for matching and notifying. Fund transfer
is entirely at your NGO's discretion after independent verification.

With regards,
Team MediTrust

---
This is an automated email. Please do not reply.
"""

    def _suggestion_body(self, name, disease, suggestions):
        suggestion_text = ""
        for i, s in enumerate(suggestions, 1):
            suggestion_text += f"""
{i}. Hospital : {s.get('hospital_name', 'N/A')}
   Address  : {s.get('hospital_address', 'N/A')}
   Note     : {s.get('suggestion_text', 'N/A')}
"""
        return f"""
Dear {name},

Based on your diagnosis ({disease}), fellow donors and community members
have suggested the following hospitals that may be able to help:

{suggestion_text}

These hospitals have been validated by Google Places API.
Please consult your doctor before making any decisions.

With care,
Team MediTrust

---
This is an automated email. Please do not reply.
"""

    def _update_body(self, donor_name, title, update):
        return f"""
Dear {donor_name},

There is a new update for the campaign you supported:

Campaign : {title}
Update   : {update}
Date     : {datetime.now().strftime('%d %B %Y')}

Thank you for your continued support.

With gratitude,
Team MediTrust

---
This is an automated email. Please do not reply.
"""

    def _blacklist_body(self, name):
        return f"""
Dear {name},

Your MediTrust account has been suspended following a review by our admin team.

If you believe this is a mistake, please contact our support team with
your details and we will look into your case.

Team MediTrust

---
This is an automated email. Please do not reply.
"""

    # ─────────────────────────────────────────
    # CORE EMAIL SENDER
    # ─────────────────────────────────────────

    def _send(self, to_email, subject, body):
        """Core SMTP email sender"""
        if not self.enabled:
            logger.warning(f"Email disabled — skipping send to {to_email}")
            return False

        try:
            msg = MIMEMultipart()
            msg['From']    = f"{self.sender_name} <{self.sender_email}>"
            msg['To']      = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, to_email, msg.as_string())
            server.quit()

            logger.info(f"Email sent to {to_email} — {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False