from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime
from utils.logger import logger
from config.settings import Config

router = APIRouter()
security = HTTPBearer()

class ExecutionResponse(BaseModel):
    status: str
    message: str
    timestamp: datetime
    execution_id: str

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key for protected endpoints"""
    if credentials.credentials != Config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials

@router.post("/execute", response_model=ExecutionResponse)
async def execute_workflow(request: Request, credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)):
    """Endpoint to trigger workflow execution on demand"""
    try:
        # Get scheduler instance from app state
        scheduler = request.app.state.scheduler
        
        if scheduler.is_job_running:
            raise HTTPException(
                status_code=409,
                detail="Workflow already running"
            )
        
        # Execute the workflow
        execution_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        logger.info(f"Starting on-demand execution {execution_id}")
        
        # Schedule the execution
        await scheduler.execute_crew_workflow()
        
        return ExecutionResponse(
            status="success",
            message="Workflow execution initiated",
            timestamp=datetime.utcnow(),
            execution_id=execution_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_status(request: Request, credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)):
    """Get current workflow status"""
    try:
        scheduler = request.app.state.scheduler
        next_run = None
        
        job = scheduler.scheduler.get_job('daily_crew_job')
        if job:
            next_run = job.next_run_time
            
        return {
            "is_running": scheduler.is_job_running,
            "next_scheduled_run": next_run,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))