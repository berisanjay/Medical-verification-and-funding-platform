def classify_risk(local_issues, cross_issues):
    total = len(local_issues) + len(cross_issues)

    if total == 0:
        return "VERIFIED"
    elif total <= 2:
        return "NEEDS_CLARIFICATION"
    else:
        return "HIGH_RISK"
