def cross_document_checks(docs):
    issues = []

    patient_names = {d["entities"]["patient_name"] for d in docs if d["entities"]["patient_name"]}
    if len(patient_names) > 1:
        issues.append("Multiple patient names detected")

    years = set()
    for d in docs:
        for date in d["entities"]["dates"]:
            for y in date.split():
                if y.isdigit() and len(y) == 4:
                    years.add(y)

    if len(years) > 1:
        issues.append("Multiple treatment years detected")

    return issues
