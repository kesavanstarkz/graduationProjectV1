import pandas as pd
import numpy as np

def rule_validation(df: pd.DataFrame):
    issues = []
    
    # Check for empty dataframe
    if df.empty:
        return [{"row": "N/A", "column": "N/A", "issue": "The dataset is empty.", "severity": "High"}]

    # 1. Missing Values
    for col in df.columns:
        missing_count = df[col].isnull().sum()
        if missing_count > 0:
            # Get indices of missing values
            missing_indices = df[df[col].isnull()].index.tolist()
            # Limit to first 5 for brevity in report, or report aggregate
            for idx in missing_indices: 
                issues.append({
                    "row": idx + 2, # 1-based index + header
                    "column": col,
                    "issue": "Missing value detected.",
                    "severity": "High"
                })

    # 2. Duplicate Rows
    duplicates = df[df.duplicated(keep=False)]
    if not duplicates.empty:
        # Group by all columns to identify sets of duplicates
        duplicate_groups = df.groupby(list(df.columns)).size().reset_index(name='count')
        duplicate_groups = duplicate_groups[duplicate_groups['count'] > 1]
        
        for _, row in duplicate_groups.iterrows():
             issues.append({
                "row": "Multiple",
                "column": "All",
                "issue": f"Duplicate row detected (appears {row['count']} times).",
                "severity": "Medium"
            })

    # 3. Outliers (Numerical columns only) - using IQR
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        
        # Define bounds
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
        
        for idx, row in outliers.iterrows():
            issues.append({
                "row": idx + 2,
                "column": col,
                "issue": f"Value {row[col]} is a potential statistical outlier (Range: {lower_bound:.2f} - {upper_bound:.2f}).",
                "severity": "Medium"
            })
            
    return issues

