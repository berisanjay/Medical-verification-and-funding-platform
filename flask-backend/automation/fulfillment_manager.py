"""
MediTrust Fulfillment Manager
Background automation for campaign lifecycle management
No database queries — communicates with Node.js backend via HTTP
"""

import logging
import os
import requests
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class FulfillmentManager:
    """
    Monitors campaign lifecycle and triggers automated actions.
    Runs as a background thread.
    Communicates with MediTrust Node.js backend via HTTP.
    """

    def __init__(self, notification_manager, check_interval=300):
        """
        Initialize fulfillment manager.
        check_interval = how often to check (seconds). Default 300 = 5 minutes.
        """
        self.notification  = notification_manager
        self.interval      = check_interval
        self.backend_url   = os.getenv("MEDITRUST_BACKEND_URL", "http://localhost:3000")
        self.flask_secret  = os.getenv("FLASK_INTERNAL_SECRET", "")
        self._running      = False
        self._thread       = None

        logger.info(f"FulfillmentManager initialized — backend: {self.backend_url}")

    # ─────────────────────────────────────────
    # THREAD CONTROL
    # ─────────────────────────────────────────

    def start(self):
        """Start background fulfillment thread"""
        if self._running:
            logger.warning("FulfillmentManager already running")
            return

        self._running = True
        self._thread  = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="FulfillmentManager"
        )
        self._thread.start()
        logger.info("FulfillmentManager background thread started")

    def stop(self):
        """Stop background fulfillment thread"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("FulfillmentManager stopped")

    def _run_loop(self):
        """Main background loop"""
        logger.info("FulfillmentManager loop running...")
        while self._running:
            try:
                self._check_all()
            except Exception as e:
                logger.error(f"FulfillmentManager loop error: {e}")
            time.sleep(self.interval)

    # ─────────────────────────────────────────
    # MAIN CHECK — runs every interval
    # ─────────────────────────────────────────

    def _check_all(self):
        """Run all automated checks"""
        logger.info(f"Running fulfillment checks at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._check_completed_campaigns()
        self._check_expired_campaigns()
        self._check_expired_documents()
        self._check_pending_fund_releases()

    # ─────────────────────────────────────────
    # CHECK 1 — Completed Campaigns
    # ─────────────────────────────────────────

    def _check_completed_campaigns(self):
        """Find campaigns where outstanding amount = 0 and mark COMPLETED"""
        try:
            response = self._get("/internal/campaigns/check-completed")
            if not response:
                return

            completed = response.get("completed_campaigns", [])
            logger.info(f"Completed campaigns found: {len(completed)}")

            for campaign in completed:
                self._handle_completed_campaign(campaign)

        except Exception as e:
            logger.error(f"Error checking completed campaigns: {e}")

    def _handle_completed_campaign(self, campaign):
        """Handle a newly completed campaign"""
        try:
            campaign_id    = campaign.get("id")
            campaign_title = campaign.get("title")
            patient_email  = campaign.get("patient_email")
            patient_name   = campaign.get("patient_name")
            total_raised   = campaign.get("collected_amount", 0)
            donors         = campaign.get("donors", [])

            logger.info(f"Handling completed campaign: {campaign_id} — {campaign_title}")

            # 1. Mark campaign as COMPLETED in Node.js backend
            self._post(f"/internal/campaigns/{campaign_id}/complete", {})

            # 2. Notify patient
            if patient_email:
                self.notification.send_campaign_live_email(
                    patient_email,
                    patient_name,
                    campaign_title,
                    campaign.get("public_url", ""),
                    campaign.get("upi_id", "")
                )

            # 3. Notify all donors — campaign completed + excess fund info
            for donor in donors:
                if donor.get("email") and not donor.get("is_anonymous"):
                    self.notification.send_campaign_completed_email(
                        donor["email"],
                        donor.get("name", "Donor"),
                        campaign_title,
                        total_raised,
                        donor.get("amount", 0)
                    )

            logger.info(f"Campaign {campaign_id} completed — {len(donors)} donors notified")

        except Exception as e:
            logger.error(f"Error handling completed campaign: {e}")

    # ─────────────────────────────────────────
    # CHECK 2 — Expired Campaigns
    # ─────────────────────────────────────────

    def _check_expired_campaigns(self):
        """Find campaigns past their expiry date and mark EXPIRED"""
        try:
            response = self._get("/internal/campaigns/check-expired")
            if not response:
                return

            expired = response.get("expired_campaigns", [])
            logger.info(f"Expired campaigns found: {len(expired)}")

            for campaign in expired:
                self._handle_expired_campaign(campaign)

        except Exception as e:
            logger.error(f"Error checking expired campaigns: {e}")

    def _handle_expired_campaign(self, campaign):
        """Handle an expired campaign"""
        try:
            campaign_id = campaign.get("id")

            # Mark as EXPIRED in Node.js backend
            self._post(f"/internal/campaigns/{campaign_id}/expire", {})

            logger.info(f"Campaign {campaign_id} marked EXPIRED")

        except Exception as e:
            logger.error(f"Error handling expired campaign: {e}")

    # ─────────────────────────────────────────
    # CHECK 3 — Expired Documents
    # ─────────────────────────────────────────

    def _check_expired_documents(self):
        """
        Find LIVE campaigns where hospital estimate document has expired.
        Update status to UPDATE_NEEDED and block fund releases.
        """
        try:
            response = self._get("/internal/campaigns/check-document-expiry")
            if not response:
                return

            expired_doc_campaigns = response.get("update_needed_campaigns", [])
            logger.info(f"Campaigns needing document update: {len(expired_doc_campaigns)}")

            for campaign in expired_doc_campaigns:
                self._handle_expired_documents(campaign)

        except Exception as e:
            logger.error(f"Error checking expired documents: {e}")

    def _handle_expired_documents(self, campaign):
        """Handle campaign with expired documents"""
        try:
            campaign_id    = campaign.get("id")
            campaign_title = campaign.get("title")
            patient_email  = campaign.get("patient_email")
            patient_name   = campaign.get("patient_name")

            # Update status to UPDATE_NEEDED in Node.js backend
            self._post(f"/internal/campaigns/{campaign_id}/update-needed", {})

            # Notify patient to upload fresh documents
            if patient_email:
                self.notification.send_verification_status_email(
                    patient_email,
                    patient_name,
                    "UPDATE_NEEDED",
                    campaign_title,
                    reason="Your hospital estimate document has expired. Please upload fresh documents to resume fund releases."
                )

            logger.info(f"Campaign {campaign_id} marked UPDATE_NEEDED — patient notified")

        except Exception as e:
            logger.error(f"Error handling expired documents: {e}")

    # ─────────────────────────────────────────
    # CHECK 4 — Pending Fund Releases
    # ─────────────────────────────────────────

    def _check_pending_fund_releases(self):
        """
        Check for milestone-triggered fund releases pending.
        For each, run 3 pre-release checks:
            1. Hospital still same verified hospital?
            2. Patient still active (not discharged)?
            3. HMS outstanding amount > 0?
        """
        try:
            response = self._get("/internal/releases/pending")
            if not response:
                return

            pending_releases = response.get("pending_releases", [])
            logger.info(f"Pending fund releases found: {len(pending_releases)}")

            for release in pending_releases:
                self._process_fund_release(release)

        except Exception as e:
            logger.error(f"Error checking pending fund releases: {e}")

    def _process_fund_release(self, release):
        """
        Process a single pending fund release.
        All 3 pre-release checks must pass before releasing.
        """
        try:
            release_id     = release.get("id")
            campaign_id    = release.get("campaign_id")
            patient_hms_id = release.get("patient_hms_id")
            amount         = release.get("amount")
            patient_email  = release.get("patient_email")
            patient_name   = release.get("patient_name")
            campaign_title = release.get("campaign_title")

            logger.info(f"Processing release {release_id} for campaign {campaign_id}")

            # ── Pre-release Check 1: Hospital still verified? ──
            hospital_check = self._get(f"/internal/campaigns/{campaign_id}/verify-hospital")
            if not hospital_check or not hospital_check.get("hospital_verified"):
                logger.warning(f"Release {release_id} BLOCKED — hospital not verified")
                self._post(f"/internal/releases/{release_id}/block",
                           {"reason": "Hospital not verified or changed"})
                return

            # ── Pre-release Check 2: Patient still active in HMS? ──
            hms_url      = os.getenv("HMS_BASE_URL", "http://localhost:4000")
            hms_response = requests.get(
                f"{hms_url}/hms/patients/{patient_hms_id}/status",
                timeout=10
            )
            hms_data = hms_response.json()

            if hms_data.get("status") == "DISCHARGED":
                logger.warning(f"Release {release_id} BLOCKED — patient discharged")
                self._post(f"/internal/releases/{release_id}/block",
                           {"reason": "Patient already discharged"})
                return

            # ── Pre-release Check 3: Outstanding amount > 0? ──
            outstanding_response = requests.get(
                f"{hms_url}/hms/patients/{patient_hms_id}/outstanding",
                timeout=10
            )
            outstanding_data = outstanding_response.json()
            outstanding      = float(outstanding_data.get("outstanding", 0))

            if outstanding <= 0:
                logger.info(f"Release {release_id} — outstanding is 0, marking campaign COMPLETED")
                self._post(f"/internal/campaigns/{campaign_id}/complete", {})
                return

            # ── All checks passed — trigger release ──
            release_amount = min(float(amount), outstanding)

            result = self._post(f"/internal/releases/{release_id}/approve",
                                {"amount": release_amount})

            if result and result.get("success"):
                # Update HMS ledger
                requests.post(
                    f"{hms_url}/hms/payments",
                    json={
                        "patient_hms_id": patient_hms_id,
                        "amount"        : release_amount,
                        "source"        : "MediTrust Crowdfunding",
                        "notes"         : f"Campaign {campaign_id} — Release {release_id}"
                    },
                    timeout=10
                )

                # Notify patient
                if patient_email:
                    self.notification.send_fund_release_notification(
                        patient_email,
                        patient_name,
                        campaign_title,
                        release_amount,
                        outstanding - release_amount
                    )

                logger.info(f"Release {release_id} approved — Rs. {release_amount} released")
            else:
                logger.error(f"Release {release_id} approval failed")

        except Exception as e:
            logger.error(f"Error processing release {release.get('id')}: {e}")

    # ─────────────────────────────────────────
    # MANUAL TRIGGER — called from Flask route
    # ─────────────────────────────────────────

    def run_manual_check(self):
        """Manually trigger all checks — called from /internal/run-checks endpoint"""
        logger.info("Manual fulfillment check triggered")
        try:
            self._check_all()
            return {"success": True, "message": "Manual check completed", "timestamp": datetime.now().isoformat()}
        except Exception as e:
            logger.error(f"Manual check error: {e}")
            return {"success": False, "error": str(e)}

    # ─────────────────────────────────────────
    # HTTP HELPERS — talk to Node.js backend
    # ─────────────────────────────────────────

    def _get(self, path):
        """GET request to MediTrust Node.js backend"""
        try:
            url      = f"{self.backend_url}{path}"
            headers  = {"x-flask-secret": self.flask_secret}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"GET {path} returned {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"GET {path} failed: {e}")
            return None

    def _post(self, path, data):
        """POST request to MediTrust Node.js backend"""
        try:
            url      = f"{self.backend_url}{path}"
            headers  = {
                "x-flask-secret" : self.flask_secret,
                "Content-Type"   : "application/json"
            }
            response = requests.post(url, json=data, headers=headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"POST {path} returned {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"POST {path} failed: {e}")
            return None