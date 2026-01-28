from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Dict, Any, Optional
from app.services.langsmith_service import LangSmithService

router = APIRouter(
    prefix="/api/langsmith",
    tags=["langsmith"],
)

langsmith_service = LangSmithService()

@router.get("/runs", response_model=List[Dict[str, Any]])
async def get_langsmith_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    project_name: Optional[str] = None
):
    try:
        runs = await langsmith_service.get_runs(limit=limit, offset=offset, project_name=project_name)
        return runs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runs/{run_id}", response_model=Dict[str, Any])
async def get_langsmith_run_details(run_id: str):
    try:
        run_details = await langsmith_service.get_run_details(run_id)
        return run_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=Dict[str, Any])
async def get_langsmith_stats(project_name: Optional[str] = None):
    try:
        stats = await langsmith_service.get_stats(project_name=project_name)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
