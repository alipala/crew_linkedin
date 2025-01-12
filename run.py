import asyncio
from hypercorn.config import Config as HypercornConfig
from hypercorn.asyncio import serve
from fastapi import FastAPI, Request
from api.slack_callback_handler import router as slack_router
from api.endpoints import router as api_router
from scheduler import CrewScheduler
from utils.logger import logger
import signal
import os
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Create FastAPI app
app = FastAPI(title="CrewAI LinkedIn Bot")

# Include routers
app.include_router(slack_router, prefix="/slack", tags=["slack"])
app.include_router(api_router, prefix="/api", tags=["api"])

@app.on_event("startup")
async def startup_event():
    """Initialize scheduler and schedule daily job on startup"""
    try:
        scheduler = CrewScheduler()
        scheduler.schedule_daily_job()
        scheduler.start()
        
        # Store scheduler in app state
        app.state.scheduler = scheduler
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
    config.bind = ["0.0.0.0:8000"]
    config.worker_class = "asyncio"
    config.use_reloader = True if os.getenv("ENVIRONMENT") == "development" else False
    
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