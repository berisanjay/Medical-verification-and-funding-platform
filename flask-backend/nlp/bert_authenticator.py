"""
MediTrust — Real Forensic Document Tampering Detector
Replaces the old BERT-based fake detector.

3 Layers of detection:
  Layer 1 — PDF Metadata Forensics    (catches edited PDFs)
  Layer 2 — Image ELA Forensics       (catches Photoshopped images)
  Layer 3 — Text Consistency Checks   (catches logical fraud)

No external API needed. Uses only:
  - PyMuPDF (fitz)   → PDF metadata
  - Pillow (PIL)     → Image ELA analysis
  - re, math         → Text consistency

Install:
  pip install PyMuPDF --break-system-packages
"""

import os
import re
import math
import logging
import tempfile
from io import BytesIO

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Try importing PyMuPDF — gracefully degrade if not installed
# ─────────────────────────────────────────────────────────────────────────────
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
    logger.info("PyMuPDF loaded — PDF metadata forensics enabled")
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not installed — PDF metadata forensics disabled")
    logger.warning("Run: pip install PyMuPDF --break-system-packages")

try:
    from PIL import Image, ImageChops, ImageEnhance
    PIL_AVAILABLE = True
    logger.info("Pillow loaded — ELA image forensics enabled")
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow not available — image forensics disabled")


class BERTDocumentAuthenticator:
    """
    Real forensic document tampering detector.

    Replaces the old BERT-based approach which only checked
    if fields were present/missing — not if they were forged.

    This detector runs 3 independent forensic layers:
      Layer 1 — PDF Metadata Forensics
      Layer 2 — ELA Image Forensics
      Layer 3 — Text Consistency Checks
    """

    # ─────────────────────────────────────────
    # Editing software signatures in PDF metadata
    # These appear when someone edits a PDF in Acrobat / online tools
    # ─────────────────────────────────────────
    EDITING_SOFTWARE_SIGNATURES = [
        'adobe acrobat',
        'adobe pdf library',
        'pdfescapes',
        'smallpdf',
        'ilovepdf',
        'pdf2go',
        'sejda',
        'pdffiller',
        'docfly',
        'pdfescape',
        'nitro',
        'foxit',
        'inkscape',
        'gimp',
        'photoshop',
        'canva',
        'microsoft word',       # Word → PDF conversion (suspicious for hospital docs)
        'libreoffice writer',   # Same reason
        'wps writer',
        'google docs',          # Genuine hospital systems don't use Google Docs
    ]

    # These are LEGITIMATE hospital software — not suspicious
    LEGITIMATE_HOSPITAL_SOFTWARE = [
        'apollo',
        'hims',
        'meditech',
        'epic',
        'practo',
        'healtheon',
        'narayana',
        'yashoda',
        'tally',                # For billing
        'winword',              # Older systems
    ]

    def __init__(self):
        logger.info("Forensic Document Tampering Detector initialized")
        logger.info(f"  PDF Metadata Forensics : {'ENABLED' if PYMUPDF_AVAILABLE else 'DISABLED (install PyMuPDF)'}")
        logger.info(f"  ELA Image Forensics    : {'ENABLED' if PIL_AVAILABLE else 'DISABLED'}")
        logger.info(f"  Text Consistency Checks: ENABLED (always)")

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN ENTRY POINT
    # Called from app.py for every document
    # ─────────────────────────────────────────────────────────────────────────
    def predict_authenticity(self, text, extracted_entities, file_path=None):
        """
        Run all 3 forensic layers on a document.

        Args:
            text             : OCR-extracted text from document
            extracted_entities: Dict of entities from entity_extractor.py
            file_path        : Optional path to original file for deep forensics

        Returns:
            Dict with:
              is_tampered     : bool — True if tampering detected
              confidence      : float 0.0–1.0 (how confident we are)
              risk_score      : int 0–100
              flags           : list of specific issues found
              layers          : dict of per-layer results
              method          : str
        """
        flags      = []
        risk_score = 0
        layers     = {}

        # ── Layer 1: PDF Metadata Forensics ──────────────────────────────────
        if file_path and PYMUPDF_AVAILABLE:
            layer1 = self._layer1_pdf_metadata(file_path)
            layers['pdf_metadata'] = layer1
            flags.extend(layer1['flags'])
            risk_score += layer1['risk_contribution']
        else:
            layers['pdf_metadata'] = {
                'ran'             : False,
                'reason'          : 'No file path provided or PyMuPDF not installed',
                'flags'           : [],
                'risk_contribution': 0
            }

        # ── Layer 2: ELA Image Forensics ─────────────────────────────────────
        if file_path and PIL_AVAILABLE:
            layer2 = self._layer2_ela_forensics(file_path)
            layers['ela_forensics'] = layer2
            flags.extend(layer2['flags'])
            risk_score += layer2['risk_contribution']
        else:
            layers['ela_forensics'] = {
                'ran'             : False,
                'reason'          : 'No file path provided or Pillow not available',
                'flags'           : [],
                'risk_contribution': 0
            }

        # ── Layer 3: Text Consistency Checks ─────────────────────────────────
        layer3 = self._layer3_text_consistency(text, extracted_entities)
        layers['text_consistency'] = layer3
        flags.extend(layer3['flags'])
        risk_score += layer3['risk_contribution']

        # ── Final Decision ────────────────────────────────────────────────────
        risk_score  = min(risk_score, 100)
        is_tampered = risk_score >= 50  # Threshold: 50+ = tampered

        # Confidence: how sure are we about the result
        if risk_score >= 80:
            confidence = 0.95
        elif risk_score >= 60:
            confidence = 0.80
        elif risk_score >= 40:
            confidence = 0.65
        elif risk_score >= 20:
            confidence = 0.55
        else:
            confidence = 0.90  # Confident it's genuine

        prediction = 'FORGED' if is_tampered else 'GENUINE'

        if flags:
            logger.warning(f"Tampering detected! Score: {risk_score}, Flags: {flags}")
        else:
            logger.info(f"Document appears genuine. Score: {risk_score}")

        return {
            'is_tampered'       : is_tampered,
            'prediction'        : prediction,
            'confidence'        : confidence,
            'risk_score'        : risk_score,
            'genuine_probability': 1.0 - (risk_score / 100),
            'forged_probability' : risk_score / 100,
            'flags'             : flags,
            'layers'            : layers,
            'method'            : 'FORENSIC_3LAYER',
            'total_checks_run'  : sum(1 for l in layers.values() if l.get('ran', True))
        }

    # =========================================================================
    # LAYER 1 — PDF METADATA FORENSICS
    # Catches: edited PDFs, online tool tampering, copy-paste fraud
    # =========================================================================
    def _layer1_pdf_metadata(self, file_path):
        """
        Analyze PDF metadata for tampering signs.

        Real hospital PDFs are usually:
          - Created and modified at the same time (never edited after creation)
          - Created by hospital billing software (not Word/Google Docs)
          - Have a single version/revision

        Tampered PDFs usually:
          - Have ModDate much later than CreationDate
          - Show editing software like Adobe Acrobat, Smallpdf, ilovepdf
          - Have multiple revisions
          - Creator ≠ Producer (someone opened and resaved)
        """
        result = {
            'ran'             : True,
            'flags'           : [],
            'risk_contribution': 0,
            'metadata'        : {}
        }

        ext = os.path.splitext(file_path)[1].lower()
        if ext != '.pdf':
            result['ran']    = False
            result['reason'] = 'Not a PDF file — skipping metadata check'
            return result

        try:
            doc = fitz.open(file_path)
            meta = doc.metadata
            doc.close()

            result['metadata'] = {
                'creator'     : meta.get('creator',  ''),
                'producer'    : meta.get('producer', ''),
                'created'     : meta.get('creationDate', ''),
                'modified'    : meta.get('modDate',  ''),
                'num_pages'   : 0,
                'has_form'    : False,
            }

            creator  = (meta.get('creator',  '') or '').lower().strip()
            producer = (meta.get('producer', '') or '').lower().strip()
            created  = (meta.get('creationDate', '') or '').strip()
            modified = (meta.get('modDate',  '') or '').strip()

            logger.info(f"PDF Metadata → Creator: '{creator}' | Producer: '{producer}'")
            logger.info(f"              Created : '{created}' | Modified: '{modified}'")

            # ── Check 1: Editing software in creator/producer ─────────────────
            for software in self.EDITING_SOFTWARE_SIGNATURES:
                if software in creator or software in producer:
                    # Is it a legitimate hospital system?
                    is_legit = any(
                        legit in creator or legit in producer
                        for legit in self.LEGITIMATE_HOSPITAL_SOFTWARE
                    )
                    if not is_legit:
                        result['flags'].append(
                            f"PDF created/edited with: '{software}' — "
                            f"genuine hospital PDFs are not created with this software"
                        )
                        result['risk_contribution'] += 35
                        break  # One flag is enough for this check

            # ── Check 2: Creation date vs Modification date ───────────────────
            if created and modified and created != modified:
                # Parse dates from PDF format: D:20240115123456+05'30'
                created_dt  = self._parse_pdf_date(created)
                modified_dt = self._parse_pdf_date(modified)

                if created_dt and modified_dt:
                    diff_seconds = (modified_dt - created_dt).total_seconds()

                    if diff_seconds > 300:  # Modified more than 5 minutes after creation
                        diff_hours = diff_seconds / 3600
                        result['flags'].append(
                            f"PDF was modified {diff_hours:.1f} hours after creation — "
                            f"indicates post-creation editing"
                        )
                        # Scale risk by how long after: 5min=10pts, 1hr=20pts, 1day=35pts
                        if diff_seconds > 86400:    # > 1 day
                            result['risk_contribution'] += 35
                        elif diff_seconds > 3600:   # > 1 hour
                            result['risk_contribution'] += 25
                        else:                       # 5 min – 1 hour
                            result['risk_contribution'] += 15

            # ── Check 3: Creator ≠ Producer (resaved in different software) ───
            if creator and producer:
                # Normalize both
                creator_clean  = re.sub(r'[\d\s\.\-]', '', creator)
                producer_clean = re.sub(r'[\d\s\.\-]', '', producer)

                if (creator_clean and producer_clean and
                        creator_clean != producer_clean and
                        len(creator_clean) > 3 and len(producer_clean) > 3):

                    # Only flag if neither is a legitimate hospital system
                    creator_legit  = any(l in creator  for l in self.LEGITIMATE_HOSPITAL_SOFTWARE)
                    producer_legit = any(l in producer for l in self.LEGITIMATE_HOSPITAL_SOFTWARE)

                    if not creator_legit and not producer_legit:
                        result['flags'].append(
                            f"PDF creator '{creator[:40]}' ≠ producer '{producer[:40]}' — "
                            f"document was opened and resaved in different software"
                        )
                        result['risk_contribution'] += 20

            # ── Check 4: Multiple revisions ───────────────────────────────────
            try:
                doc2 = fitz.open(file_path)
                if hasattr(doc2, 'xref_length'):
                    # High xref count can indicate many edits
                    xref_count = doc2.xref_length()
                    if xref_count > 500:  # Very high for a simple medical document
                        result['flags'].append(
                            f"PDF has {xref_count} internal references — "
                            f"unusually high for a medical document (may indicate repeated editing)"
                        )
                        result['risk_contribution'] += 10
                doc2.close()
            except Exception:
                pass

            result['risk_contribution'] = min(result['risk_contribution'], 60)

        except Exception as e:
            logger.error(f"Layer 1 PDF metadata error: {e}")
            result['ran']    = False
            result['reason'] = f"PDF metadata check failed: {str(e)}"

        return result

    # =========================================================================
    # LAYER 2 — ELA IMAGE FORENSICS (Error Level Analysis)
    # Catches: Photoshopped images, edited scans, copy-paste on images
    # =========================================================================
    def _layer2_ela_forensics(self, file_path):
        """
        Error Level Analysis (ELA) on images.

        How ELA works:
          - Save the image at a known JPEG quality (e.g. 95%)
          - Compare original vs re-saved
          - Regions that were edited show HIGHER error levels
          - Genuine photos have UNIFORM error levels
          - Copy-pasted / edited regions stand out as bright spots

        Works on: JPG, PNG, and PDF first pages converted to images.
        """
        result = {
            'ran'             : True,
            'flags'           : [],
            'risk_contribution': 0,
            'ela_stats'       : {}
        }

        try:
            ext = os.path.splitext(file_path)[1].lower()
            img = None

            # ── Load image ────────────────────────────────────────────────────
            if ext == '.pdf':
                # Convert first page of PDF to image for ELA
                if PYMUPDF_AVAILABLE:
                    doc  = fitz.open(file_path)
                    page = doc[0]
                    mat  = fitz.Matrix(2, 2)  # 2x zoom for better quality
                    pix  = page.get_pixmap(matrix=mat)
                    doc.close()
                    img_bytes = pix.tobytes('jpeg')
                    img = Image.open(BytesIO(img_bytes)).convert('RGB')
                else:
                    result['ran']    = False
                    result['reason'] = 'PyMuPDF needed for PDF ELA — not installed'
                    return result

            elif ext in ['.jpg', '.jpeg', '.png', '.webp']:
                img = Image.open(file_path).convert('RGB')
            else:
                result['ran']    = False
                result['reason'] = f'Unsupported format for ELA: {ext}'
                return result

            if img is None:
                result['ran']    = False
                result['reason'] = 'Could not load image'
                return result

            # ── Run ELA ───────────────────────────────────────────────────────
            ela_result = self._run_ela(img)
            result['ela_stats'] = ela_result

            # ── Interpret ELA results ─────────────────────────────────────────
            max_diff  = ela_result.get('max_diff',  0)
            mean_diff = ela_result.get('mean_diff', 0)
            std_diff  = ela_result.get('std_diff',  0)

            logger.info(
                f"ELA Results → max_diff: {max_diff:.2f}, "
                f"mean_diff: {mean_diff:.2f}, std_diff: {std_diff:.2f}"
            )

            # High std_diff = uneven error distribution = editing
            # Genuine scanned documents have LOW and UNIFORM ELA values
            # Edited images have HIGH and UNEVEN ELA values

            if std_diff > 25 and max_diff > 80:
                result['flags'].append(
                    f"ELA detected high image inconsistency "
                    f"(std={std_diff:.1f}, max={max_diff:.1f}) — "
                    f"possible image editing or copy-paste detected"
                )
                result['risk_contribution'] += 40

            elif std_diff > 18 and max_diff > 60:
                result['flags'].append(
                    f"ELA detected moderate image inconsistency "
                    f"(std={std_diff:.1f}, max={max_diff:.1f}) — "
                    f"document may have been digitally altered"
                )
                result['risk_contribution'] += 25

            elif std_diff > 12 and max_diff > 45:
                result['flags'].append(
                    f"ELA detected minor inconsistency "
                    f"(std={std_diff:.1f}) — "
                    f"possible minor editing (low confidence)"
                )
                result['risk_contribution'] += 10

            result['risk_contribution'] = min(result['risk_contribution'], 50)

        except Exception as e:
            logger.error(f"Layer 2 ELA forensics error: {e}")
            result['ran']    = False
            result['reason'] = f"ELA analysis failed: {str(e)}"

        return result

    def _run_ela(self, original_img):
        """
        Run Error Level Analysis on a PIL Image.
        Returns dict with max_diff, mean_diff, std_diff.
        """
        try:
            # Save image at quality 95 to a buffer
            buffer = BytesIO()
            original_img.save(buffer, format='JPEG', quality=95)
            buffer.seek(0)
            resaved_img = Image.open(buffer).convert('RGB')

            # Compute difference
            diff = ImageChops.difference(original_img, resaved_img)

            # Enhance the difference for better visibility
            enhancer = ImageEnhance.Brightness(diff)
            enhanced = enhancer.enhance(10)

            # Convert to raw pixels for statistics
            pixels = list(enhanced.getdata())

            # Calculate per-channel statistics
            if pixels and isinstance(pixels[0], tuple):
                # RGB image
                r_vals = [p[0] for p in pixels]
                g_vals = [p[1] for p in pixels]
                b_vals = [p[2] for p in pixels]
                all_vals = r_vals + g_vals + b_vals
            else:
                all_vals = [p for p in pixels]

            if not all_vals:
                return {'max_diff': 0, 'mean_diff': 0, 'std_diff': 0}

            mean_diff = sum(all_vals) / len(all_vals)
            max_diff  = max(all_vals)
            variance  = sum((x - mean_diff) ** 2 for x in all_vals) / len(all_vals)
            std_diff  = math.sqrt(variance)

            return {
                'max_diff'  : round(max_diff,  2),
                'mean_diff' : round(mean_diff, 2),
                'std_diff'  : round(std_diff,  2),
            }

        except Exception as e:
            logger.error(f"ELA computation error: {e}")
            return {'max_diff': 0, 'mean_diff': 0, 'std_diff': 0}

    # =========================================================================
    # LAYER 3 — TEXT CONSISTENCY CHECKS
    # Catches: amount in words ≠ digits, impossible dates,
    #          mismatched hospital name + pincode, logical fraud
    # =========================================================================
    def _layer3_text_consistency(self, text, entities):
        """
        Check internal consistency of the document text.

        These checks catch cases where someone changes one field
        (like the amount) but forgets to change the matching field
        (like the amount in words).

        Checks:
          1. Amount in digits vs amount in words
          2. Pincode matches known city/state format
          3. Date is not in the future
          4. Hospital name is not a known fake template
          5. Document has minimum real content (not blank/short)
          6. Amount is within realistic medical range for India
          7. Aadhaar format validation (if Aadhaar doc)
        """
        result = {
            'ran'             : True,
            'flags'           : [],
            'risk_contribution': 0
        }

        if not text:
            result['flags'].append("Document has no extractable text")
            result['risk_contribution'] += 20
            return result

        # ── Check 1: Minimum content check ───────────────────────────────────
        word_count = len(text.split())
        if word_count < 20:
            result['flags'].append(
                f"Document has very few words ({word_count}) — "
                f"possibly blank, corrupted, or a placeholder"
            )
            result['risk_contribution'] += 25

        # ── Check 2: Amount in words vs digits ────────────────────────────────
        amount_flag = self._check_amount_words_vs_digits(text)
        if amount_flag:
            result['flags'].append(amount_flag)
            result['risk_contribution'] += 30

        # ── Check 3: Future date check ────────────────────────────────────────
        future_flag = self._check_future_dates(text)
        if future_flag:
            result['flags'].append(future_flag)
            result['risk_contribution'] += 25

        # ── Check 4: Unrealistic medical amount ───────────────────────────────
        amount_range_flag = self._check_amount_range(entities)
        if amount_range_flag:
            result['flags'].append(amount_range_flag)
            result['risk_contribution'] += 20

        # ── Check 5: Aadhaar format check ─────────────────────────────────────
        aadhaar_flag = self._check_aadhaar_format(text)
        if aadhaar_flag:
            result['flags'].append(aadhaar_flag)
            result['risk_contribution'] += 30

        # ── Check 6: Known fake template patterns ─────────────────────────────
        template_flag = self._check_fake_templates(text)
        if template_flag:
            result['flags'].append(template_flag)
            result['risk_contribution'] += 40

        # ── Check 7: Pincode format (India: 6 digits, starts 1-8) ─────────────
        pincode = entities.get('hospital_pincode')
        if pincode:
            if not re.match(r'^[1-8][0-9]{5}$', str(pincode)):
                result['flags'].append(
                    f"Invalid pincode format: '{pincode}' — "
                    f"Indian pincodes are 6 digits starting with 1-8"
                )
                result['risk_contribution'] += 15

        result['risk_contribution'] = min(result['risk_contribution'], 60)
        return result

    def _check_amount_words_vs_digits(self, text):
        """
        Check if amount written in words matches the digit amount.
        Common fraud: change the digit amount but forget the words.
        Example: 'Rupees Five Lakh Only' but digits show 9,33,000
        """
        # Find amount in words patterns
        words_pattern = re.search(
            r'(?:Rupees?|Rs\.?)\s+([A-Za-z\s]+?)\s+Only',
            text, re.IGNORECASE
        )
        if not words_pattern:
            return None  # No words amount found — skip check

        words_amount_text = words_pattern.group(1).strip().lower()

        # Find nearby digit amount
        digit_pattern = re.search(
            r'(?:₹|Rs\.?|INR)?\s*([0-9,]{5,})',
            text[max(0, words_pattern.start() - 200):words_pattern.end() + 200]
        )
        if not digit_pattern:
            return None

        try:
            digit_amount = float(digit_pattern.group(1).replace(',', ''))
        except ValueError:
            return None

        # Convert words to approximate number for comparison
        words_amount = self._words_to_number(words_amount_text)
        if words_amount is None:
            return None

        # Allow 5% tolerance
        if words_amount > 0 and digit_amount > 0:
            diff_pct = abs(words_amount - digit_amount) / max(words_amount, digit_amount)
            if diff_pct > 0.05:
                return (
                    f"Amount mismatch: words say ~₹{words_amount:,.0f} "
                    f"but digits show ₹{digit_amount:,.0f} — "
                    f"possible amount tampering detected"
                )
        return None

    def _words_to_number(self, words):
        """Convert Indian number words to approximate integer."""
        if not words:
            return None
        w = words.lower()
        value = 0
        try:
            if 'crore' in w:
                parts = w.split('crore')
                crore_part = parts[0].strip()
                value += self._simple_words_to_num(crore_part) * 10000000
                if len(parts) > 1 and parts[1].strip():
                    value += self._words_to_number(parts[1]) or 0
            elif 'lakh' in w or 'lac' in w:
                parts = re.split(r'lakh|lac', w)
                lakh_part = parts[0].strip()
                value += self._simple_words_to_num(lakh_part) * 100000
                if len(parts) > 1 and parts[1].strip():
                    value += self._words_to_number(parts[1]) or 0
            elif 'thousand' in w:
                parts = w.split('thousand')
                value += self._simple_words_to_num(parts[0].strip()) * 1000
                if len(parts) > 1 and parts[1].strip():
                    value += self._words_to_number(parts[1]) or 0
            else:
                value = self._simple_words_to_num(w)
        except Exception:
            return None
        return value if value > 0 else None

    def _simple_words_to_num(self, words):
        """Convert simple number words (up to 999) to int."""
        number_map = {
            'zero':0,'one':1,'two':2,'three':3,'four':4,'five':5,
            'six':6,'seven':7,'eight':8,'nine':9,'ten':10,
            'eleven':11,'twelve':12,'thirteen':13,'fourteen':14,'fifteen':15,
            'sixteen':16,'seventeen':17,'eighteen':18,'nineteen':19,'twenty':20,
            'thirty':30,'forty':40,'fifty':50,'sixty':60,
            'seventy':70,'eighty':80,'ninety':90,'hundred':100
        }
        words = words.strip().lower()
        if not words:
            return 0
        total = 0
        current = 0
        for word in words.split():
            word = re.sub(r'[^a-z]', '', word)
            if word in number_map:
                num = number_map[word]
                if num == 100:
                    current = (current if current else 1) * 100
                else:
                    current += num
            elif word == 'and':
                continue
        total += current
        return total

    def _check_future_dates(self, text):
        """Check if any date in the document is in the future."""
        from datetime import datetime
        date_patterns = [
            r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b',
            r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b',
        ]
        now = datetime.now()
        for pattern in date_patterns:
            for match in re.finditer(pattern, text):
                try:
                    g = match.groups()
                    # Try DD/MM/YYYY first
                    try:
                        dt = datetime(int(g[2]), int(g[1]), int(g[0]))
                    except Exception:
                        # Try YYYY/MM/DD
                        dt = datetime(int(g[0]), int(g[1]), int(g[2]))

                    if dt > now:
                        return (
                            f"Document contains a future date: {match.group(0)} — "
                            f"medical documents cannot have future dates"
                        )
                except Exception:
                    continue
        return None

    def _check_amount_range(self, entities):
        """
        Check if claimed amount is within realistic Indian medical range.
        Realistic range: ₹5,000 – ₹2,00,00,000 (5K to 2 Crore)
        """
        amount = entities.get('amount')
        if not amount:
            return None

        try:
            if isinstance(amount, str):
                amount_num = float(re.sub(r'[^\d.]', '', amount.replace(',', '')))
            else:
                amount_num = float(amount)

            if amount_num < 1000:
                return (
                    f"Amount ₹{amount_num:,.0f} is unrealistically low — "
                    f"minimum expected medical cost is ₹1,000"
                )
            if amount_num > 20000000:  # 2 Crore
                return (
                    f"Amount ₹{amount_num:,.0f} exceeds ₹2 Crore — "
                    f"unusually high for a single medical procedure in India"
                )
        except Exception:
            pass
        return None

    def _check_aadhaar_format(self, text):
        """
        Validate Aadhaar number format if this is an Aadhaar document.
        Aadhaar: 12 digits, does NOT start with 0 or 1.
        """
        text_lower = text.lower()
        if 'aadhaar' not in text_lower and 'aadhar' not in text_lower:
            return None  # Not an Aadhaar document

        # Find Aadhaar numbers in text
        aadhaar_patterns = [
            r'\b(\d{4})\s+(\d{4})\s+(\d{4})\b',   # 1234 5678 9012
            r'\b(\d{4})-(\d{4})-(\d{4})\b',         # 1234-5678-9012
            r'\b(\d{12})\b',                          # 123456789012
        ]
        for pattern in aadhaar_patterns:
            match = re.search(pattern, text)
            if match:
                # Join all groups to get full number
                full_number = ''.join(match.groups())
                if len(full_number) == 12:
                    if full_number[0] in ('0', '1'):
                        return (
                            f"Aadhaar number '{full_number[:4]} XXXX {full_number[8:]}' "
                            f"starts with {full_number[0]} — "
                            f"valid Aadhaar numbers cannot start with 0 or 1"
                        )
                    # Check for obviously fake numbers (all same digit, sequential)
                    if len(set(full_number)) == 1:
                        return (
                            f"Aadhaar number appears to be fake (all same digit)"
                        )
                    if full_number in ('123456789012', '000000000000', '111111111111'):
                        return (
                            f"Aadhaar number appears to be a test/fake number"
                        )
        return None

    def _check_fake_templates(self, text):
        """
        Check for known fake document template patterns.
        Fraudsters often use downloaded templates with placeholder text.
        """
        fake_patterns = [
            r'\[.*?\]',             # [Patient Name], [Hospital Name] etc.
            r'<.*?>',               # <Insert Amount Here>
            r'Lorem\s+ipsum',       # Template placeholder text
            r'SAMPLE\s+DOCUMENT',   # Watermarks
            r'FOR\s+ILLUSTRATION',
            r'SPECIMEN\s+ONLY',
            r'NOT\s+A\s+VALID',
            r'YOUR\s+NAME\s+HERE',
            r'ENTER\s+(?:NAME|AMOUNT|DATE)',
        ]
        for pattern in fake_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found = re.search(pattern, text, re.IGNORECASE).group(0)
                return (
                    f"Document contains template placeholder text: '{found}' — "
                    f"this appears to be a fake/template document"
                )
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # HELPER — Parse PDF date format
    # PDF dates look like: D:20240115123456+05'30'
    # ─────────────────────────────────────────────────────────────────────────
    def _parse_pdf_date(self, pdf_date_str):
        """Parse PDF metadata date string to datetime."""
        from datetime import datetime
        if not pdf_date_str:
            return None
        try:
            # Remove 'D:' prefix
            s = pdf_date_str.strip()
            if s.startswith('D:'):
                s = s[2:]
            # Take first 14 characters: YYYYMMDDHHmmss
            s = s[:14]
            if len(s) >= 8:
                return datetime.strptime(s[:14].ljust(14, '0'), '%Y%m%d%H%M%S')
        except Exception:
            pass
        return None


# ─────────────────────────────────────────────────────────────────────────────
# QUICK TEST
# Run: python bert_authenticator.py
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)

    detector = BERTDocumentAuthenticator()

    print("\n" + "="*60)
    print("TEST 1 — Genuine document text")
    print("="*60)
    genuine_text = """
    APOLLO HOSPITALS VISAKHAPATNAM
    Waltair Main Road, Visakhapatnam - 530002
    PATIENT'S NAME: Gollapati Jesse Jasper
    DIAGNOSIS: Triple Vessel Coronary Artery Disease
    ADMISSION DATE: 15/01/2026
    CONSULTANT DOCTOR: Dr. R. Srinivas Rao
    ESTIMATED TOTAL (Rs) 9,33,000.00
    Rupees Nine Lakh Thirty Three Thousand Only
    """
    entities = {
        'patient_name' : 'Gollapati Jesse Jasper',
        'hospital_name': 'Apollo Hospitals Visakhapatnam',
        'diseases'     : ['Triple Vessel Coronary Artery Disease'],
        'amount'       : 933000,
        'date'         : '15/01/2026'
    }
    result = detector.predict_authenticity(genuine_text, entities)
    print(f"Prediction  : {result['prediction']}")
    print(f"Is Tampered : {result['is_tampered']}")
    print(f"Risk Score  : {result['risk_score']}")
    print(f"Flags       : {result['flags']}")

    print("\n" + "="*60)
    print("TEST 2 — Suspicious document (amount mismatch)")
    print("="*60)
    suspicious_text = """
    APOLLO HOSPITALS VISAKHAPATNAM
    PATIENT'S NAME: Gollapati Jesse Jasper
    DIAGNOSIS: Triple Vessel Coronary Artery Disease
    ADMISSION DATE: 15/01/2026
    ESTIMATED TOTAL (Rs) 9,33,000.00
    Rupees Five Lakh Only
    """
    result2 = detector.predict_authenticity(suspicious_text, entities)
    print(f"Prediction  : {result2['prediction']}")
    print(f"Is Tampered : {result2['is_tampered']}")
    print(f"Risk Score  : {result2['risk_score']}")
    print(f"Flags       : {result2['flags']}")

    print("\n" + "="*60)
    print("TEST 3 — Fake template document")
    print("="*60)
    fake_text = """
    [HOSPITAL NAME HERE]
    PATIENT'S NAME: [Enter Patient Name]
    DIAGNOSIS: [Disease]
    ESTIMATED TOTAL: [Amount]
    """
    result3 = detector.predict_authenticity(fake_text, {})
    print(f"Prediction  : {result3['prediction']}")
    print(f"Is Tampered : {result3['is_tampered']}")
    print(f"Risk Score  : {result3['risk_score']}")
    print(f"Flags       : {result3['flags']}")