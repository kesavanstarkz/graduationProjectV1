import pandas as pd
from app.services.validator import rule_validation

df = pd.read_csv("data/dmsap_test.csv")
issues = rule_validation(df)

print(f"Total issues found: {len(issues)}")
for issue in issues:
    print(f"Row {issue['row']}, Col {issue['column']}: {issue['issue']}")
    print(f"  Orig: {issue.get('original_value')}, Corr: {issue.get('corrected_value')}, Reason: {issue.get('reason')}")
    print("-" * 20)
