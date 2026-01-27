from fastapi import APIRouter, Depends
import pandas as pd
import os
import time
import asyncio
from datetime import datetime
from app.services.validator import rule_validation
from app.services.ai_explainer import explain_issue, _get_fallback_explanation, LOCAL_MODEL_NAME
from app.database import get_db, sanitize_table_name, create_dynamic_table
from sqlalchemy.orm import Session
from typing import Optional
from fastapi.responses import JSONResponse
from pydantic import BaseModel


router = APIRouter(prefix="/validate")

class ValidationRequest(BaseModel):
    filename: str
    original_name: Optional[str] = "Unknown Dataset"
    clear_previous: Optional[bool] = False # Ignored now as we use dynamic tables

# Global cache for AI explanations to avoid redundant API calls during bulk uploads
GLOBAL_ISSUE_CACHE = {}
MAX_UNIQUE_EXPLANATIONS = 500

from fastapi.responses import StreamingResponse
import json

@router.post("/")
async def validate_data(request: ValidationRequest, db: Session = Depends(get_db)):
    file_path = f"data/{request.filename}"
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "File not found"})

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Invalid CSV: {str(e)}"})
    
    async def validation_generator():
        try:
            # Create a dynamic table for this specific file
            table_name = sanitize_table_name(request.filename)
            table = create_dynamic_table(table_name)
            
            db.execute(table.delete())
            db.commit()

            print(f"🚀 [START] Validation for: {request.original_name}")
            yield json.dumps({"status": "starting", "message": f"Analyzing {request.original_name}..."}) + "\n"
            
            issues = rule_validation(df)
            total_issues = len(issues)
            print(f"📊 [RULES] Rule validation complete. Found {total_issues} issues.")
            
            yield json.dumps({"status": "rules_done", "total": total_issues, "message": f"Rule check complete. Found {total_issues} issues."}) + "\n"
            
            issues_to_insert = []
            processed_count = 0

            async def process_one_issue(idx, i):
                nonlocal processed_count
                row_num = i.get('row', 'N/A')
                col_name = i.get('column', 'N/A')
                issue_sig = f"{i['column']}_{i['issue'].split()[0]}" 
                
                print(f"🧠 [AI] Row {row_num} | Col {col_name} | Issue {idx+1}/{total_issues}...")
                
                # Small delay for local model stability
                await asyncio.sleep(idx * 0.1) 
                
                explanation = ""
                if issue_sig in GLOBAL_ISSUE_CACHE:
                    explanation = GLOBAL_ISSUE_CACHE[issue_sig]
                elif len(GLOBAL_ISSUE_CACHE) < MAX_UNIQUE_EXPLANATIONS:
                    row_data = {}
                    if isinstance(i["row"], int):
                         df_idx = i["row"] - 2
                         if 0 <= df_idx < len(df):
                              row_data = df.iloc[df_idx].to_dict()
                    
                    explanation = await explain_issue(i, row_data)
                    if "DETAILED OBSERVATION" not in explanation:
                        explanation = _get_fallback_explanation(i)
                    GLOBAL_ISSUE_CACHE[issue_sig] = explanation
                else:
                     explanation = _get_fallback_explanation(i)

                processed_count += 1
                return {
                    "row_number": str(i["row"]),
                    "column_name": i["column"],
                    "issue": i["issue"],
                    "ai_explanation": explanation,
                    "severity": i["severity"],
                    "dataset_name": request.original_name,
                    "edited_by": "AI",
                    "created_at": datetime.utcnow()
                }, {"row": row_num, "col": col_name, "count": processed_count}

            # We process in small chunks of 5 for parallel but responsive feedback
            for chunk_start in range(0, total_issues, 5):
                chunk = issues[chunk_start:chunk_start+5]
                tasks = [process_one_issue(chunk_start + idx, i) for idx, i in enumerate(chunk)]
                results = await asyncio.gather(*tasks)
                
                for issue_dict, progress in results:
                    issues_to_insert.append(issue_dict)
                    print(f"✅ [DONE] Processed Row {progress['row']} ({progress['count']}/{total_issues})")
                    yield json.dumps({
                        "status": "progress", 
                        "current_row": progress['row'], 
                        "processed": progress['count'], 
                        "total": total_issues,
                        "remaining": total_issues - progress['count']
                    }) + "\n"

            if issues_to_insert:
                print(f"💾 [SAVE] Writing {len(issues_to_insert)} records to database...")
                db.execute(table.insert(), issues_to_insert)
                db.commit()
            
            print(f"🎉 [FINISH] Validation complete for {request.original_name}.")
            yield json.dumps({"status": "complete", "table": table_name, "message": "Validation finished!"}) + "\n"
                
        except Exception as e:
            db.rollback()
            yield json.dumps({"status": "error", "message": str(e)}) + "\n"

    return StreamingResponse(validation_generator(), media_type="application/x-ndjson")
