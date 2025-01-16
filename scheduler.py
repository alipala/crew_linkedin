from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from utils.topic_manager import TopicManager
from utils.logger import logger
from datetime import datetime
import pytz
import asyncio
from typing import Optional, Dict, Any
from main import main

class CrewScheduler:
    """Handles scheduled and on-demand execution of the CrewAI workflow"""
    
    def __init__(self):
        self.topic_manager = TopicManager()
        self.scheduler = AsyncIOScheduler()
        self.is_job_running = False
        
    async def execute_crew_workflow(self, custom_inputs: Optional[Dict[str, Any]] = None) -> None:
        try:
            if self.is_job_running:
                logger.warning("Job already running, skipping execution")
                return
                
            self.is_job_running = True
            
            try:
                # Get topics from custom inputs or topic manager
                topics = (custom_inputs or {}).get('topics')
                
                # Execute crew workflow using the main function
                result = await asyncio.to_thread(main, custom_topics=topics)
                
                logger.info(f"Crew execution completed with topics: {topics}")
                return result
                
            finally:
                self.is_job_running = False
                
        except Exception as e:
            logger.error(f"Error executing crew workflow: {e}")
            self.is_job_running = False
            raise
            
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