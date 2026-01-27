from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db, list_all_issue_tables, get_dynamic_table
from sqlalchemy import select
from app.services.vector_db import store_explanation
import json

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

@router.post("/chat")
async def chat_with_assistant(query_data: dict, db: Session = Depends(get_db)):
    table_name = query_data.get("table_name")
    query = query_data.get("query")
    
    if not table_name or not table_name.startswith("issues_"):
        return {"response": "Please select a dataset first so I can provide accurate clinical insights."}
    
    table = get_dynamic_table(table_name)
    
    # 1. Authoritative SQLite Facts
    issues_result = db.execute(select(table)).mappings().all()
    issues_list = [dict(row) for row in issues_result]
    
    total_issues = len(issues_list)
    affected_records = len(set(i['row_number'] for i in issues_list))
    severity_counts = {}
    for i in issues_list:
        sev = i['severity']
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    
    # 2. Expert Context Retrieval (RAG)
    from app.services.vector_db import collection
    # Retrieve top similarity match for surgical focus
    vector_results = collection.query(query_texts=[query], n_results=1)
    expert_context = vector_results['documents'][0][0] if (vector_results['documents'] and vector_results['documents'][0]) else "No specific context."
    
    # 3. Optimized Prompt for Local Intelligence
    prompt = f"""
    [STATS] Dataset: {table_name}, Total issues: {total_issues}, Severity distribution: {severity_counts}
    [KNOWLEDGE] {expert_context}
    
    [USER QUERY]
    {query}
    
    [INSTRUCTION]
    Provide a factual clinical answer. If the data shows specific issues like high body temperature, explain the clinical risk and how to validate it.
    Keep the response under 150 words.
    Format clearly with headers: ### 1. Factual Answer, ### 2. Supporting Details, ### 3. Expert Interpretation.
    """
    
    from app.services.ai_explainer import ollama_chat, LOCAL_MODEL_NAME
    
    try:
        ai_response = await ollama_chat(prompt)
        if ai_response:
            return {"response": ai_response}
    except Exception as e:
        print(f"❌ [ROUTER] Chat local intelligence error: {e}")
    
    # Fallback if local model fails or is not running
    fallback_msg = (
        f"### 1. Factual Answer\nThere are {total_issues} issues in this dataset.\n\n"
        f"### 2. Supporting Details\nSeverity: {severity_counts}. Issues were detected in fields like Body_Temperature, Age, or Weight.\n\n"
        f"### 3. Expert Interpretation\n[LOCAL OFFLINE] I'm currently unable to connect to the local clinical intelligence engine (Ollama). Please ensure the Ollama server is running and the {LOCAL_MODEL_NAME} model is pulled."
    )
    return {"response": fallback_msg}
