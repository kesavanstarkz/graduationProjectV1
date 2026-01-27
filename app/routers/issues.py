from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db, list_all_issue_tables, get_dynamic_table
from sqlalchemy import select
from app.services.vector_db import store_explanation

router = APIRouter(prefix="/issues")

@router.get("/")
def get_issues(db: Session = Depends(get_db)):
    # Returns all issues (not recommended for large datasets, but keeping for legacy compatibility if needed)
    all_issues = []
    tables = list_all_issue_tables()
    for table_name in tables:
        table = get_dynamic_table(table_name)
        result = db.execute(select(table)).mappings().all()
        for row in result:
            all_issues.append(dict(row))
    return all_issues

@router.get("/{table_name}")
def get_file_issues(table_name: str, db: Session = Depends(get_db)):
    # Verify the table exists and starts with "issues_"
    if not table_name.startswith("issues_"):
        return {"error": "Invalid table requested"}
    
    table = get_dynamic_table(table_name)
    result = db.execute(select(table)).mappings().all()
    # Add table_name to each issue for easier UI tracking
    return [{**dict(row), "table_name": table_name} for row in result]

@router.put("/{table_name}/{issue_id}")
def update_issue(table_name: str, issue_id: int, update_data: dict, db: Session = Depends(get_db)):
    if not table_name.startswith("issues_"):
        return {"error": "Invalid table"}
    
    table = get_dynamic_table(table_name)
    
    # Fetch current state to get context for Vector DB sync if needed
    if 'ai_explanation' in update_data and update_data.get('edited_by') == 'Manual':
        current = db.execute(select(table).where(table.c.id == issue_id)).mappings().first()
        if current:
             # Sync the manual edit to ChromaDB for future intelligence
             # We use the updated explanation and the current row's context
             try:
                 store_explanation(
                     issue_type=current['issue'], 
                     column=current['column_name'], 
                     row_context={}, # We don't have full row data here, but issue+col is usually unique enough for semantic matching in this context
                     explanation=update_data['ai_explanation'],
                     edited_by="Manual"
                 )
                 print(f"🧠 [VECTOR] Learned manual correction for '{current['issue']}'")
             except Exception as ve:
                 print(f"⚠️ Vector DB Learning Error: {ve}")

    db.execute(
        table.update().where(table.c.id == issue_id).values(**update_data)
    )
    db.commit()
    return {"message": "Issue updated successfully"}

@router.delete("/{table_name}/{issue_id}")
def delete_issue(table_name: str, issue_id: int, db: Session = Depends(get_db)):
    if not table_name.startswith("issues_"):
        return {"error": "Invalid table"}
    
    table = get_dynamic_table(table_name)
    db.execute(
        table.delete().where(table.c.id == issue_id)
    )
    db.commit()
    return {"message": "Issue deleted successfully"}
