"""
Disease text → NGO capability column mapper
Maps raw OCR-extracted disease names to structured NGO database columns
"""

DISEASE_CATEGORY_MAP = {
    'cardiac': [
        'coronary', 'cardiac', 'heart', 'cabg', 'bypass',
        'angioplasty', 'myocardial', 'infarction', 'vessel',
        'artery', 'stent', 'valve', 'pacemaker', 'angina',
        'cardiomyopathy', 'arrhythmia', 'aorta', 'triple vessel',
        'open heart', 'heart failure', 'atrial', 'ventricular'
    ],
    'cancer': [
        'cancer', 'tumor', 'tumour', 'carcinoma', 'lymphoma',
        'leukemia', 'leukaemia', 'chemotherapy', 'oncology',
        'malignant', 'sarcoma', 'melanoma', 'biopsy', 'metastasis',
        'radiation', 'radiotherapy'
    ],
    'neuro': [
        'neuro', 'brain', 'stroke', 'paralysis', 'epilepsy',
        'seizure', 'parkinson', 'alzheimer', 'dementia',
        'spinal', 'spine', 'migraine', 'cerebral', 'nervous',
        'multiple sclerosis', 'neuropathy', 'head injury'
    ],
    'kidney': [
        'kidney', 'renal', 'dialysis', 'nephro', 'urinary',
        'bladder', 'nephrotic', 'nephritis', 'ckd',
        'chronic kidney', 'kidney failure', 'kidney stone'
    ],
    'liver': [
        'liver', 'hepatic', 'hepatitis', 'cirrhosis',
        'jaundice', 'gallbladder', 'bile', 'fatty liver',
        'fibrosis', 'liver failure', 'liver transplant'
    ],
    'orthopedic': [
        'bone', 'fracture', 'orthopedic', 'joint', 'knee',
        'hip', 'replacement', 'disc', 'ligament',
        'tendon', 'osteoporosis', 'arthritis', 'scoliosis',
        'spinal cord', 'vertebra'
    ],
    'eye': [
        'eye', 'vision', 'retina', 'cataract', 'glaucoma',
        'cornea', 'optic', 'blindness', 'ocular', 'vitreous',
        'macular', 'diabetic retinopathy'
    ],
    'rare': [
        'rare', 'genetic', 'muscular dystrophy', 'thalassemia',
        'hemophilia', 'down syndrome', 'wilson',
        'gaucher', 'fabry', 'pompe', 'hunter syndrome',
        'cystic fibrosis', 'sickle cell'
    ],
}


def map_disease_to_categories(disease_text: str) -> dict:
    """
    Takes raw disease text and returns NGO capability columns to match.

    Example:
        Input:  "Triple Vessel Coronary Artery Disease"
        Output: { "disease_cardiac": True }

        Input:  "Chronic Kidney Disease with Dialysis"
        Output: { "disease_kidney": True }
    """
    if not disease_text:
        return {'disease_general': True}

    text_lower = disease_text.lower()
    matched    = {}

    for category, keywords in DISEASE_CATEGORY_MAP.items():
        for keyword in keywords:
            if keyword in text_lower:
                matched[f'disease_{category}'] = True
                break  # One match per category is enough

    # Fallback to general if nothing matched
    if not matched:
        matched['disease_general'] = True

    return matched


def build_ngo_query_conditions(disease_text: str, patient_age: int = None) -> dict:
    """
    Build full NGO query conditions including age group + disease.

    Returns dict ready to use in Prisma WHERE clause.

    Example:
        disease_text = "Triple Vessel Coronary Artery Disease"
        patient_age  = 21
        Returns: { "disease_cardiac": True, "supports_adults": True }
    """
    conditions = map_disease_to_categories(disease_text)

    # Age group mapping
    if patient_age is not None:
        if patient_age < 18:
            conditions['supports_children'] = True
        elif patient_age >= 60:
            conditions['supports_elderly']  = True
        else:
            conditions['supports_adults']   = True

    return conditions


def get_disease_label(disease_text: str) -> str:
    """
    Returns human-readable category label for display.

    Example:
        "Triple Vessel Coronary Artery Disease" → "Cardiac / Heart"
        "Chronic Kidney Disease"                → "Kidney / Renal"
    """
    label_map = {
        'cardiac'    : 'Cardiac / Heart',
        'cancer'     : 'Cancer / Oncology',
        'neuro'      : 'Neurology / Brain',
        'kidney'     : 'Kidney / Renal',
        'liver'      : 'Liver / Hepatic',
        'orthopedic' : 'Orthopedic / Bone',
        'eye'        : 'Eye / Vision',
        'rare'       : 'Rare / Genetic Disease',
        'general'    : 'General / Other',
    }

    if not disease_text:
        return label_map['general']

    text_lower = disease_text.lower()

    for category, keywords in DISEASE_CATEGORY_MAP.items():
        for keyword in keywords:
            if keyword in text_lower:
                return label_map.get(category, label_map['general'])

    return label_map['general']


# ── Test ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    test_cases = [
        ("Triple Vessel Coronary Artery Disease", 21),
        ("Chronic Kidney Disease with Dialysis",  65),
        ("Brain Tumor - Chemotherapy required",   10),
        ("Liver Cirrhosis",                        45),
        ("Knee Replacement Surgery",               55),
        ("Unknown condition",                      30),
    ]

    print("\n=== Disease → NGO Mapper Test ===\n")
    for disease, age in test_cases:
        conditions = build_ngo_query_conditions(disease, age)
        label      = get_disease_label(disease)
        print(f"Disease : {disease}")
        print(f"Age     : {age}")
        print(f"Label   : {label}")
        print(f"Columns : {conditions}")
        print()