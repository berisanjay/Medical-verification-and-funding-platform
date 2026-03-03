# Sample Test Documents

This directory should contain sample medical documents for testing the verification system.

## Recommended Test Documents

### 1. Medical Estimate
Create a document with:
- Patient Name: Suresh Kumar
- Hospital: Yashoda Hospitals, Somajiguda
- Pincode: 500082
- Doctor: Dr. Rajesh Sharma
- Diagnosis: Coronary Artery Disease requiring angioplasty
- Date: 15/01/2024
- Estimated Cost: Rs. 4,95,000

### 2. Medical Bill
Create a document with:
- Patient Name: Suresh Kumar (same as estimate)
- Hospital: Yashoda Hospitals (same as estimate)
- Pincode: 500082
- Date: 20/01/2024
- Total Amount Payable: Rs. 5,10,000

### 3. Prescription
Create a document with:
- Patient Name: Suresh Kumar
- Doctor: Dr. Rajesh Sharma
- Date: 22/01/2024
- Medications and dosages

## Creating Test PDFs

You can create test PDFs using:

### Option 1: Microsoft Word
1. Create document with above content
2. Save as PDF

### Option 2: Google Docs
1. Create document with above content
2. File → Download → PDF

### Option 3: Online Tools
- Use tools like Canva or Adobe Express
- Create medical document templates

## Testing Different Scenarios

### Positive Test Cases (Should Pass)
1. Upload estimate + bill with matching details
2. All mandatory fields present
3. Consistent patient names
4. Bill amount ≤ Estimate amount

### Negative Test Cases (Should Flag Issues)
1. **Patient Name Mismatch**
   - Estimate: "Suresh Kumar"
   - Bill: "S. Kumar" (too different)

2. **Missing Mandatory Fields**
   - Document without patient name
   - Document without disease/diagnosis
   - Document without amount

3. **Bill Exceeds Estimate**
   - Estimate: Rs. 4,00,000
   - Bill: Rs. 5,00,000

4. **Conflicting Dates**
   - Bill date before estimate date
   - Dates more than 1 year apart

5. **Hospital Mismatch**
   - Different hospital names
   - Different pincodes

## Sample Text Content

### Medical Estimate Template
```
MEDICAL ESTIMATE

Hospital: Yashoda Hospitals
Address: Somajiguda, Hyderabad - 500082
Phone: +91-40-12345678

Patient Name: Suresh Kumar
Age: 52 Years
Date: 15/01/2024

Consulting Doctor: Dr. Rajesh Sharma
Department: Cardiology

Diagnosis: Coronary Artery Disease

Procedure: Coronary Angioplasty with Stent Placement

Estimated Cost Breakdown:
- Room Charges: Rs. 1,50,000
- Procedure Charges: Rs. 2,50,000
- Medicines: Rs. 50,000
- Diagnostic Tests: Rs. 25,000
- Other Charges: Rs. 20,000

Total Estimated Cost: Rs. 4,95,000/-

Note: This is an estimate. Actual costs may vary.

Signature: _________________
Dr. Rajesh Sharma
MD, DM Cardiology
```

### Medical Bill Template
```
FINAL MEDICAL BILL

Hospital: Yashoda Hospitals
Somajiguda, Hyderabad - 500082

Patient Name: Suresh Kumar
Date of Admission: 18/01/2024
Date of Discharge: 20/01/2024

Doctor: Dr. Rajesh Sharma

Treatment: Coronary Angioplasty

Bill Breakdown:
- Room Charges (2 days): Rs. 1,60,000
- Procedure Charges: Rs. 2,60,000
- Medicines: Rs. 55,000
- Laboratory Tests: Rs. 20,000
- ICU Charges: Rs. 10,000
- Miscellaneous: Rs. 5,000

Total Amount Payable: Rs. 5,10,000/-

Payment Due Date: 25/01/2024

Authorized Signatory: _______________
```

## File Naming Convention

Use descriptive names:
- `estimate_suresh_kumar_yashoda.pdf`
- `bill_suresh_kumar_yashoda.pdf`
- `prescription_suresh_kumar.pdf`

## Notes

- Ensure documents are clear and readable
- Use standard medical terminology
- Include all mandatory fields
- Test both PDF and image formats
- Keep file sizes reasonable (<10MB)

## Automated Test Generation

For automated testing, you can use the included script:
```bash
python generate_test_documents.py
```

This will create a set of test documents with various scenarios.
