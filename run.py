import asyncio
from hypercorn.config import Config as HypercornConfig
from hypercorn.asyncio import serve
from main import main as crew_main
from api.slack_callback_handler import app
from utils.logger import logger
import signal
import sys
from dotenv import load_dotenv
import os


# Load environment variables from .env file
load_dotenv()

async def shutdown(sig, loop):
    """Graceful shutdown handler"""
    logger.info(f"Received exit signal {sig.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    logger.info(f"Cancelling {len(tasks)} tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

async def run_crew():
    """Run CrewAI workflow in a loop"""
    while True:
        try:
            await asyncio.get_event_loop().run_in_executor(None, crew_main)
            await asyncio.sleep(300)  # Run every 5 minutes
        except Exception as e:
            logger.error(f"CrewAI workflow error: {str(e)}")
            await asyncio.sleep(60)  # Wait before retry

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
    
    # Create and run tasks
    server = serve(app, config)
    crew_runner = run_crew()
    
    try:
        await asyncio.gather(server, crew_runner)
    except asyncio.CancelledError:
        logger.info("Shutdown initiated")
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        sys.exit(1)
    finally:
        logger.info("Shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        sys.exit(0)