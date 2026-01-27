from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, select, union_all, literal_column
from app.database import get_db, list_all_issue_tables, get_dynamic_table
from typing import Dict, Any

router = APIRouter(
    prefix="/stats",
    tags=["stats"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=Dict[str, Any])
def get_stats(db: Session = Depends(get_db)):
    tables = list_all_issue_tables()
    
    if not tables:
        return {
            "summary": {
                "total_datasets": 0,
                "total_issues": 0,
                "critical_rate": 0
            },
            "severity_distribution": {
                "Critical": 0,
                "Warning": 0,
                "Info": 0
            },
            "top_columns": []
        }

    # Create a union of all stats-relevant columns from all tables
    # We select: id (for count), severity, column_name, dataset_name
    selects = []
    for t_name in tables:
        t = get_dynamic_table(t_name)
        s = select(
            t.c.id, 
            t.c.severity, 
            t.c.column_name, 
            t.c.dataset_name
        )
        selects.append(s)

    # Combine into a Common Table Expression (CTE) for querying
    combined_query = union_all(*selects).cte(name="all_issues_cte")

    # 1. Summary Cards Data
    
    # Total Issues
    total_issues = db.query(func.count(combined_query.c.id)).scalar()
    
    # Total Datasets (distinct names)
    total_datasets = db.query(func.count(func.distinct(combined_query.c.dataset_name))).scalar()
    
    # Critical Issues
    critical_issues = db.query(func.count(combined_query.c.id)).filter(combined_query.c.severity == "Critical").scalar()
    
    critical_rate = 0
    if total_issues and total_issues > 0:
        critical_rate = round((critical_issues / total_issues) * 100, 1)

    # 2. Charts Data
    
    # Severity Distribution
    severity_counts = db.query(
        combined_query.c.severity, 
        func.count(combined_query.c.id)
    ).group_by(combined_query.c.severity).all()
    
    severity_data = {sev: count for sev, count in severity_counts}
    
    # Top Problematic Columns
    top_columns = db.query(
        combined_query.c.column_name, 
        func.count(combined_query.c.id).label('count')
    ).group_by(combined_query.c.column_name).order_by(desc('count')).limit(5).all()
    
    column_data = [{"column": col, "count": count} for col, count in top_columns]

    return {
        "summary": {
            "total_datasets": total_datasets or 0,
            "total_issues": total_issues or 0,
            "critical_rate": critical_rate
        },
        "severity_distribution": severity_data,
        "top_columns": column_data
    }
