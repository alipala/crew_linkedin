from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from main import main as crew_main
from utils.logger import logger
from datetime import datetime
import pytz
import asyncio
import functools

class CrewScheduler:
    """Handles scheduled and on-demand execution of the CrewAI workflow"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_job_running = False
        
    async def execute_crew_workflow(self):
        """Execute the CrewAI workflow"""
        if self.is_job_running:
            logger.warning("Job already running, skipping execution")
            return
            
        try:
            self.is_job_running = True
            logger.info("Starting CrewAI workflow execution")
            
            # Run crew_main in a thread pool since it's not async
            loop = asyncio.get_running_loop()
            partial_crew = functools.partial(crew_main)
            await loop.run_in_executor(None, partial_crew)
            
        except Exception as e:
            logger.error(f"Error in workflow execution: {str(e)}")
            raise
            
        finally:
            self.is_job_running = False
            
    def schedule_daily_job(self):
        """Schedule daily job at 8 AM CET"""
        trigger = CronTrigger(
            hour=8,
            minute=0,
            timezone=pytz.timezone('Europe/Paris')
        )
        
        self.scheduler.add_job(
            self.execute_crew_workflow,
            trigger=trigger,
            id='daily_crew_job',
            name='Daily CrewAI Workflow',
            replace_existing=True
        )
        
        logger.info("Scheduled daily job for 8 AM CET")
        
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
            
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shutdown complete")