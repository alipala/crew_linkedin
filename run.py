import asyncio
from hypercorn.config import Config as HypercornConfig
from hypercorn.asyncio import serve
from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from api.slack_callback_handler import router as slack_router
from api.endpoints import router as api_router
from scheduler import CrewScheduler
from utils.logger import logger
from utils.notification_slack_tool import NotificationSlackTool
import signal
import sys
import os

# Get deployment URL from environment
RAILWAY_STATIC_URL = os.getenv('RAILWAY_STATIC_URL', 'http://localhost:8000')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# Create FastAPI app
app = FastAPI(
    title="CrewAI LinkedIn Bot",
    root_path="" if ENVIRONMENT == 'development' else RAILWAY_STATIC_URL
)

# Add middleware for production deployment
if ENVIRONMENT == 'production':
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # In production, you might want to restrict this
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(slack_router, prefix="/slack", tags=["slack"])
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
        
        logger.info(f"Application started successfully in {ENVIRONMENT} environment")
        logger.info(f"Application URL: {RAILWAY_STATIC_URL}")
        
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
        "environment": ENVIRONMENT,
        "url": RAILWAY_STATIC_URL,
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
    config.bind = [f"0.0.0.0:{os.getenv('PORT', '8000')}"]
    config.worker_class = "asyncio"
    config.proxies_count = 1  # Tell Hypercorn we're behind a proxy
    config.forwarded_allow_ips = "*"  # Allow forwarded headers from Railway's proxy
    
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