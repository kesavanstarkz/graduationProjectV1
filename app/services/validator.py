import pandas as pd
import numpy as np
import re

# DMSAP Standardization Mapping (Fuzzy match patterns)
STANDARD_FIELDS = {
    "temperature": [r"temp", r"body_temp", r"temperature"],
    "parasitaemia": [r"parasit", r"count", r"density"],
    "age": [r"age", r"dob", r"years"],
    "weight": [r"weight", r"wt", r"kg"],
    "height": [r"height", r"ht", r"cm"],
    "sex": [r"sex", r"gender"]
}

def infer_schema(df: pd.DataFrame):
    """Maps CSV columns to standard clinical fields using fuzzy matching."""
    mapping = {}
    for standard_name, patterns in STANDARD_FIELDS.items():
        for col in df.columns:
            if any(re.search(pattern, col, re.IGNORECASE) for pattern in patterns):
                mapping[standard_name] = col
                break
    return mapping

def rule_validation(df: pd.DataFrame):
    issues = []
    
    if df.empty:
        return [{"row": "N/A", "column": "N/A", "issue": "The dataset is empty.", "severity": "Critical"}]

    mapping = infer_schema(df)

    # 1. Basic Missing Values Check
    for col in df.columns:
        missing_indices = df[df[col].isnull()].index.tolist()
        for idx in missing_indices: 
            issues.append({
                "row": idx + 2,
                "column": col,
                "issue": "Missing value detected.",
                "severity": "Critical",
                "original_value": "None",
                "corrected_value": "Missing",
                "reason": "Missing values must be distinguishable from zero."
            })

    # 2. Duplicate Rows
    duplicates = df[df.duplicated(keep=False)]
    if not duplicates.empty:
        duplicate_groups = df.groupby(list(df.columns)).size().reset_index(name='count')
        duplicate_groups = duplicate_groups[duplicate_groups['count'] > 1]
        for _, row in duplicate_groups.iterrows():
             issues.append({
                "row": "Multiple",
                "column": "All",
                "issue": f"Duplicate row detected ({row['count']} times).",
                "severity": "Warning",
                "original_value": "Duplicate Record",
                "corrected_value": "Flagged",
                "reason": "Auditability requirement: duplicates flagged for review."
            })

    # 3. Clinical Rules (DMSAP Philosophy)
    
    # Temperature: < 34°C or > 42°C → invalid
    if "temperature" in mapping:
        col = mapping["temperature"]
        invalid_temp = df[(df[col] < 34) | (df[col] > 42)]
        for idx, row in invalid_temp.iterrows():
            issues.append({
                "row": idx + 2,
                "column": col,
                "issue": "[SAFE IMPROVEMENT] Clinical temperature outlier.",
                "severity": "Critical",
                "original_value": str(row[col]),
                "corrected_value": "Missing",
                "reason": "Temp < 34 or > 42 is considered clinically invalid."
            })

    # Age: > 90 → invalid
    if "age" in mapping:
        col = mapping["age"]
        invalid_age = df[df[col] > 90]
        for idx, row in invalid_age.iterrows():
            issues.append({
                "row": idx + 2,
                "column": col,
                "issue": "[SAFE IMPROVEMENT] Age exceeds clinical protocol limit.",
                "severity": "Critical",
                "original_value": str(row[col]),
                "corrected_value": "Invalid",
                "reason": "Age > 90 is outside study parameters."
            })

    # Parasitaemia: > 500,000 → treat as missing
    if "parasitaemia" in mapping:
        col = mapping["parasitaemia"]
        high_para = df[df[col] > 500000]
        for idx, row in high_para.iterrows():
            issues.append({
                "row": idx + 2,
                "column": col,
                "issue": "[SAFE IMPROVEMENT] Parasitaemia density exceeds limit.",
                "severity": "Warning",
                "original_value": str(row[col]),
                "corrected_value": "Missing",
                "reason": "Density > 500k is treated as censored/missing per protocol."
            })

    # Weight–age mismatch: drop weight, keep age
    if "weight" in mapping and "age" in mapping:
        w_col = mapping["weight"]
        a_col = mapping["age"]
        # Simplified mismatch check: e.g., weight > 20 for age < 1
        mismatch = df[(df[a_col] < 1) & (df[w_col] > 20)]
        for idx, row in mismatch.iterrows():
            issues.append({
                "row": idx + 2,
                "column": w_col,
                "issue": "[SAFE IMPROVEMENT] Weight-Age mismatch detected.",
                "severity": "Warning",
                "original_value": f"Weight:{row[w_col]}, Age:{row[a_col]}",
                "corrected_value": "Dropped",
                "reason": "Weight unrealistic for age. Protocol: Keep age, drop weight."
            })

    # Statistical Outliers (Fallback for other numerical columns)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    mapped_cols = list(mapping.values())
    for col in numeric_cols:
        if col in mapped_cols: continue # Clinical rules already applied
        
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
        
        for idx, row in outliers.iterrows():
            issues.append({
                "row": idx + 2,
                "column": col,
                "issue": f"Value {row[col]} is a statistical outlier.",
                "severity": "Warning",
                "original_value": str(row[col]),
                "corrected_value": "Keep",
                "reason": f"Standard IQR Outlier (Range: {lower_bound:.2f} - {upper_bound:.2f})"
            })
            
    return issues

