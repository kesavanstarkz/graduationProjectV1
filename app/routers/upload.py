from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
import pandas as pd
import os
import shutil
from typing import List

router = APIRouter(prefix="/upload")

import uuid

UPLOAD_DIR = "data"

@router.post("/")
async def upload_files(files: List[UploadFile] = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    results = []
    
    for file in files:
        file_uuid = str(uuid.uuid4())
        filename = f"{file_uuid}.csv" # Forcing .csv extension as per the new logic
        file_path = os.path.join(UPLOAD_DIR, filename)

        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Quick validation check: read just the header to verify CSV
            # Reset file pointer or just read from disk
            df = pd.read_csv(file_path, nrows=5) 
            
            results.append({
                "original_name": file.filename,
                "filename": filename,
                "rows": "Ready", # Don't count all rows yet for speed on upload
                "columns": df.columns.tolist()
            })
            
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": f"Failed to upload {file.filename}: {str(e)}"})

    return {"uploaded_files": results, "message": f"Successfully uploaded {len(results)} files."}
