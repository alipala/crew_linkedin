import asyncio
from contextlib import asynccontextmanager
from hypercorn.config import Config as HypercornConfig
from hypercorn.asyncio import serve
from fastapi import FastAPI, Request, Response
from api.slack_callback_handler import router as slack_callback_router
from api.slack_message_handler import router as slack_message_router
from api.endpoints import router as api_router
from scheduler import CrewScheduler
from utils.logger import logger
from utils.notification_slack_tool import NotificationSlackTool
import signal
import sys
import os
import time
from typing import Dict

# Create Slack notification tool for state
notification_tool = NotificationSlackTool()

# Add state for request tracking
request_tracking: Dict[str, float] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    try:
        # Startup
        logger.info("Starting up application...")
        
        # Initialize scheduler
        scheduler = CrewScheduler()
        scheduler.schedule_daily_job()
        scheduler.start()
        
        # Initialize state
        app.state.scheduler = scheduler
        app.state.notification_tool = notification_tool
        app.state.processed_events = set()
        app.state.request_tracking = request_tracking
        
        logger.info("Application started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise
        
    finally:
        # Shutdown
        try:
            if hasattr(app.state, 'scheduler'):
                app.state.scheduler.shutdown()
            logger.info("Application shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")

# Create FastAPI app with lifespan
app = FastAPI(
    title="CrewAI LinkedIn Agent",
    lifespan=lifespan
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log and track all HTTP requests"""
    request_id = request.headers.get("x-request-id", "unknown")
    start_time = time.time()
    
    try:
        # Store request start time
        request_tracking[request_id] = start_time
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log request details
        logger.info(
            f"Request completed | ID: {request_id} | "
            f"Method: {request.method} | "
            f"Path: {request.url.path} | "
            f"Status: {response.status_code} | "
            f"Duration: {duration:.3f}s"
        )
        
        if response.status_code == 404:
            logger.error(f"404 Error for path: {request.url.path}")
            
        return response
        
    except Exception as e:
        logger.error(f"Request error: {str(e)}")
        raise
        
    finally:
        # Cleanup request tracking
        request_tracking.pop(request_id, None)

# Register routers
app.include_router(slack_message_router, prefix="/slack", tags=["slack"])
app.include_router(
    slack_callback_router, 
    prefix="/slack/interactive",  # The prefix already includes the full path
    tags=["slack"]
)
app.include_router(api_router, prefix="/api", tags=["api"])

@app.get("/health")
async def health_check():
    """Health check endpoint with enhanced status information"""
    try:
        scheduler_status = await app.state.scheduler.get_status() if hasattr(app.state, 'scheduler') else None
        
        return {
            "status": "healthy",
            "scheduler": scheduler_status,
            "active_requests": len(request_tracking),
            "processed_events": len(app.state.processed_events) if hasattr(app.state, 'processed_events') else 0,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return Response(
            status_code=500,
            content={"status": "unhealthy", "error": str(e)}
        )

async def shutdown(sig, loop):
    """Graceful shutdown handler"""
    logger.info(f"Received exit signal {sig.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    logger.info(f"Cancelling {len(tasks)} tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

async def main():
    """Main application entry point"""
    loop = asyncio.get_running_loop()
    
    # Set up signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig, 
            lambda s=sig: asyncio.create_task(shutdown(s, loop))
        )

    # Configure Hypercorn
    config = HypercornConfig()
    port = int(os.getenv("PORT", "8000"))
    config.bind = [f"0.0.0.0:{port}"]
    config.worker_class = "asyncio"
    config.keepalive_timeout = 300
    config.graceful_timeout = 300
    config.read_timeout = 300
    logger.info(f"Starting server on port {port}")
    
    try:
        await serve(app, config)
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        sys.exit(0)