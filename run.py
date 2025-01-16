import asyncio
from hypercorn.config import Config as HypercornConfig
from hypercorn.asyncio import serve
from fastapi import FastAPI, Request
from api.slack_callback_handler import router as slack_callback_router
from api.slack_message_handler import router as slack_message_router
from api.endpoints import router as api_router
from scheduler import CrewScheduler
from utils.logger import logger
from utils.notification_slack_tool import NotificationSlackTool
import signal
import sys
import os

# Create FastAPI app
app = FastAPI(title="CrewAI LinkedIn Agent")

app.include_router(slack_message_router, prefix="/slack", tags=["slack"])  # Changed this line
app.include_router(slack_callback_router, prefix="/slack/interactive", tags=["slack"])
app.include_router(api_router, prefix="/api", tags=["api"])

# Create Slack notification tool for state
notification_tool = NotificationSlackTool()

@app.on_event("startup")
async def startup_event():
    """Initialize scheduler and state on startup"""
    try:
        # Initialize scheduler
        scheduler = CrewScheduler()
        scheduler.schedule_daily_job()
        scheduler.start()
        
        # Store in app state
        app.state.scheduler = scheduler
        app.state.notification_tool = notification_tool
        
        logger.info("Application started successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        if hasattr(app.state, 'scheduler'):
            app.state.scheduler.shutdown()
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "scheduler_running": app.state.scheduler.scheduler.running if hasattr(app.state, 'scheduler') else False
    }

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