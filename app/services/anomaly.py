from scipy import stats

def anomaly_detection(df, column):
    issues = []

    if column not in df.columns:
        return issues

    zscores = stats.zscore(df[column], nan_policy="omit")

    for idx, z in enumerate(zscores):
        if abs(z) > 3:
            issues.append({
                "row": idx,
                "column": column,
                "issue": "Statistical anomaly detected"
            })

    return issues
