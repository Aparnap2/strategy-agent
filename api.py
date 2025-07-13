import os
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Optional, List
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Configure logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# Now import other modules after environment is loaded
from agent_orchestrator import AgentOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Strategy Assistant API",
    description="API for the AI Strategy Assistant that helps with project planning and architecture design.",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for request status and results
# In a production environment, use a proper database
request_store: Dict[str, Dict] = {}

# Initialize the agent orchestrator
agent_orchestrator = AgentOrchestrator()

# Request/Response Models
class ProcessRequest(BaseModel):
    """Request model for processing a new strategy request."""
    user_input: str = Field(..., description="The user's project or strategy request")
    max_iterations: int = Field(3, description="Maximum number of feedback iterations")
    context: Optional[Dict] = Field(None, description="Additional context for the request")

class ProcessResponse(BaseModel):
    """Response model for a processing request."""
    request_id: str
    status: str
    message: Optional[str] = None
    result: Optional[Dict] = None

class RequestStatus(BaseModel):
    """Model for request status."""
    request_id: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    progress: int  # 0-100
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str

# API Endpoints
@app.post("/process", response_model=ProcessResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_request(request: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Submit a new strategy request for processing.
    
    This endpoint starts an asynchronous task to process the request and returns immediately
    with a request ID that can be used to check the status and retrieve results.
    """
    # Generate a unique request ID
    request_id = str(uuid.uuid4())
    
    # Store initial request status with all required fields for RequestStatus
    now = datetime.utcnow().isoformat()
    request_store[request_id] = {
        "request_id": request_id,  # Ensure request_id is included
        "status": "pending",
        "progress": 0,
        "created_at": now,
        "updated_at": now,
        "request": request.dict(),
        "result": None,
        "error": None,
        "message": "Request received and queued for processing"
    }
    
    # Start background task to process the request
    background_tasks.add_task(process_request_background, request_id, request)
    
    return ProcessResponse(
        request_id=request_id,
        status="pending",
        message="Request accepted and is being processed"
    )

@app.get("/status/{request_id}", response_model=RequestStatus)
async def get_status(request_id: str):
    """Get the status of a processing request."""
    if request_id not in request_store:
        raise HTTPException(status_code=404, detail="Request ID not found")
    
    # Ensure all required fields are present in the response
    status_info = request_store[request_id].copy()
    
    # Ensure request_id is included in the response
    status_info["request_id"] = request_id
    
    # Ensure all required fields have default values if missing
    required_fields = {
        "status": "unknown",
        "progress": 0,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "message": "Status information available",
        "result": {},
        "error": None
    }
    
    # Set default values for any missing required fields
    for field, default in required_fields.items():
        if field not in status_info or status_info[field] is None:
            status_info[field] = default
    
    return status_info

@app.get("/results/{request_id}", response_model=RequestStatus)
async def get_results(request_id: str):
    """Get the results of a completed request."""
    if request_id not in request_store:
        raise HTTPException(status_code=404, detail="Request ID not found")
    
    # Get the current status info
    status_info = request_store[request_id].copy()
    
    # If the request is not complete, return the current status
    if status_info["status"] != "completed":
        # Return the current status with a message
        status_info["message"] = f"Request is not complete. Current status: {status_info['status']}"
        return status_info
    
    # Ensure all required fields are present in the response
    status_info["request_id"] = request_id
    
    # Ensure all required fields have default values if missing
    required_fields = {
        "status": "completed",
        "progress": 100,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "message": "Request completed successfully",
        "result": {},
        "error": None
    }
    
    # Set default values for any missing required fields
    for field, default in required_fields.items():
        if field not in status_info or status_info[field] is None:
            status_info[field] = default
    
    return status_info

# Background Task
async def process_request_background(request_id: str, request: ProcessRequest):
    """Background task to process the request using the agent workflow."""
    try:
        # Ensure the request exists in the store
        if request_id not in request_store:
            logger.error(f"Request {request_id} not found in request store")
            return
            
        # Update status to processing with all required fields
        update_request_status(
            request_id=request_id,
            status="processing",
            progress=10,
            message="Starting agent workflow...",
            result=request_store[request_id].get("result"),
            error=None
        )
        
        try:
            # Process the request using the agent orchestrator
            result = await agent_orchestrator.process_request(
                user_input=request.user_input,
                context=request.context or {},
                max_iterations=request.max_iterations
            )
            
            # Update status to completed with the result
            update_request_status(
                request_id=request_id,
                status="completed",
                progress=100,
                message="Processing completed successfully",
                result=result,
                error=None
            )
            
        except Exception as e:
            logger.error(f"Error in agent processing for request {request_id}: {str(e)}", exc_info=True)
            raise  # Re-raise to be caught by the outer try-except
            
    except Exception as e:
        logger.error(f"Critical error processing request {request_id}: {str(e)}", exc_info=True)
        update_request_status(
            request_id=request_id,
            status="failed",
            progress=100,
            message=f"Processing failed: {str(e)}",
            result=request_store[request_id].get("result"),
            error=str(e)
        )

def update_request_status(
    request_id: str,
    status: str,
    progress: int,
    message: str = None,
    result: Dict = None,
    error: str = None
):
    """Update the status of a request in the store."""
    if request_id not in request_store:
        logger.warning(f"Attempted to update non-existent request: {request_id}")
        return
    
    # Get the current request data
    request_data = request_store[request_id]
    
    # Update the request data with new status information
    updated_data = {
        "request_id": request_id,  # Ensure request_id is included in the response
        "status": status,
        "progress": progress,
        "updated_at": datetime.utcnow().isoformat(),
        "message": message or request_data.get("message"),
        "created_at": request_data.get("created_at", datetime.utcnow().isoformat()),
        "result": result if result is not None else request_data.get("result"),
        "error": error if error is not None else request_data.get("error"),
        "request": request_data.get("request")
    }
    
    # Update the stored data
    request_store[request_id].update(updated_data)
    
    # Log the status update
    logger.info(f"Request {request_id} status updated to {status} ({progress}%)")
    if error:
        logger.error(f"Error in request {request_id}: {error}")

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "requests_processed": len([r for r in request_store.values() if r["status"] == "completed"])
    }

# List All Requests (for debugging)
@app.get("/requests", include_in_schema=False)
async def list_requests():
    """List all requests (for debugging purposes)."""
    return {
        "count": len(request_store),
        "requests": [
            {
                "request_id": req_id,
                "status": req["status"],
                "progress": req["progress"],
                "created_at": req["created_at"],
                "updated_at": req["updated_at"]
            }
            for req_id, req in request_store.items()
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
