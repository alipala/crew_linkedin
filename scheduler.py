from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from utils.topic_manager import TopicManager
from utils.logger import logger
from datetime import datetime
import pytz
import asyncio
import time
from typing import Optional, Dict, Any, List
from main import main

class CrewScheduler:
    """Handles scheduled and on-demand execution of the CrewAI workflow"""
    
    def __init__(self):
        self.topic_manager = TopicManager()
        self.scheduler = AsyncIOScheduler()
        self.is_job_running = False
        self._last_execution_time = None
        self._execution_lock = asyncio.Lock()
        self._cooldown_period = 300  # 5 minutes in seconds
        
    async def execute_crew_workflow(self, custom_inputs: Optional[Dict[str, Any]] = None) -> None:
        """
        Execute the crew workflow with cooldown and locking
        
        Args:
            custom_inputs: Optional dictionary containing custom configuration
            
        Returns:
            None
        """
        try:
            # Check if execution is already in progress
            if self.is_job_running:
                logger.warning("Job already running, skipping execution")
                return
                
            # Check cooldown period
            current_time = time.time()
            if self._last_execution_time and (current_time - self._last_execution_time < self._cooldown_period):
                cooldown_remaining = self._cooldown_period - (current_time - self._last_execution_time)
                logger.warning(f"Cooldown period active. Please wait {cooldown_remaining:.0f} seconds")
                return
                
            # Acquire execution lock
            async with self._execution_lock:
                self.is_job_running = True
                self._last_execution_time = current_time
                
                try:
                    # Extract topics from custom inputs
                    topics = None
                    if custom_inputs and 'topics' in custom_inputs:
                        if isinstance(custom_inputs['topics'], (list, str)):
                            topics = custom_inputs['topics']
                            logger.info(f"Received topics for execution: {topics}")
                        else:
                            logger.warning(f"Invalid topics format received: {type(custom_inputs['topics'])}")
                    
                    # Execute crew workflow
                    logger.info(f"Executing crew with topics: {topics}")
                    result = await asyncio.to_thread(
                        main,
                        custom_topics=topics
                    )
                    
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
            replace_existing=True,
            coalesce=True,  # Prevents multiple executions if previous job is still running
            misfire_grace_time=3600  # 1 hour grace time for missed executions
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
            
    async def get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time"""
        job = self.scheduler.get_job('daily_crew_job')
        return job.next_run_time if job else None
        
    async def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        return {
            "is_running": self.is_job_running,
            "last_execution": self._last_execution_time,
            "next_scheduled_run": await self.get_next_run_time(),
            "cooldown_active": bool(
                self._last_execution_time and 
                (time.time() - self._last_execution_time < self._cooldown_period)
            )
        }