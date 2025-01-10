from utils.logger import logger
import os
import yaml
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from utils.linkedin_scrape_tool import LinkedInScrapeTool
from utils.notification_slack_tool import NotificationSlackTool
import ssl
from tests.verify_config import verify_configuration
import sys
import logging

ssl._create_default_https_context = ssl._create_unverified_context

os.environ["CREWAI_LOG_LEVEL"] = "DEBUG" 
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def load_yaml_configs():
    """Load configurations from YAML files."""
    files = {
        'agents': 'config/agents.yaml',
        'tasks': 'config/tasks.yaml'
    }

    configs = {}
    for config_type, file_path in files.items():
        if not os.path.exists(file_path):
            logger.error(f"Configuration file not found: {file_path}")
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        logger.info(f"Loading configuration from {file_path}")
        try:
            with open(file_path, 'r') as file:
                configs[config_type] = yaml.safe_load(file)
                logger.debug(f"{config_type} configurations: {configs[config_type]}")
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {file_path}: {e}")
            raise
    return configs

def validate_create_post_task_output(task_output):
    """Validate output of create_post_task."""
    if not task_output or not task_output.result:
        logger.error("Create Post Task did not produce any output or result.")
        sys.exit(1)
    logger.info(f"Create Post Task output: {task_output.result}")


def prepare_notify_user_task_context(create_post_task_output):
    """Prepare context for notify_user_task."""
    notify_context = {
        "description": create_post_task_output.result.get("description")
    }
    if not notify_context["description"]:
        logger.error("Notify User Task context is invalid. Missing 'description'.")
        sys.exit(1)
    logger.info(f"Context for Notify User Task: {notify_context}")
    return notify_context

def main():

    # Verify configuration first
    if not verify_configuration():
        logger.error("Configuration verification failed. Exiting...")
        sys.exit(1)
        
    logger.info("Configuration verified. Starting application...")

    try:
        logger.info("Initializing LinkedIn Content Generation Pipeline...")

        # Load configurations
        configs = load_yaml_configs()
        logger.debug(f"Configurations loaded: {configs}")

        # Initialize tools
        linkedin_tool = LinkedInScrapeTool()
        serper_tool = SerperDevTool()
        notification_slack_tool = NotificationSlackTool()

        logger.info("Initializing agents and tasks...")
        # Initialize agents
        linkedin_scrape_agent = Agent(
            config=configs['agents']['linkedin_scrape_agent'],
            tools=[linkedin_tool],
            llm="gpt-4",
            verbose=True
        )
        linkedin_analyze_agent = Agent(
            config=configs['agents']['linkedin_interaction_analyze_agent'],
            llm="gpt-4",
            verbose=True
        )
        brainstorm_agent = Agent(
            config=configs['agents']['brainstorm_agent'],
            llm="gpt-4",
            verbose=True
        )
        web_search_agent = Agent(
            config=configs['agents']['web_search_agent'],
            tools=[serper_tool],
            llm="gpt-3.5-turbo",
            verbose=True
        )
        post_create_agent = Agent(
            config=configs['agents']['post_create_agent'],
            llm="gpt-4",
            verbose=True
        )
        notification_agent = Agent(
            config=configs['agents']['notification_agent'],
            tools=[notification_slack_tool],
            llm="gpt-3.5-turbo",
            verbose=True
        )

        # Initialize tasks
        scrape_task = Task(
            config=configs['tasks']['scrape_linkedin_posts'],
            agent=linkedin_scrape_agent,
            verbose=True 
        )
        analyze_task = Task(
            config=configs['tasks']['analyze_engagement'],
            agent=linkedin_analyze_agent,
            context=[scrape_task],
            verbose=True 
        )
        brainstorm_task = Task(
            config=configs['tasks']['generate_ideas'],
            agent=brainstorm_agent,
            context=[analyze_task]
        )
        web_search_task = Task(
            config=configs['tasks']['conduct_web_search'],
            agent=web_search_agent,
            context=[brainstorm_task],
            verbose=True 
        )
        create_post_task = Task(
            config=configs['tasks']['create_post'],
            agent=post_create_agent,
            context=[web_search_task],
            verbose=True
        )
        notify_user_task = Task(
            config=configs['tasks']['notify_user'],
            agent=notification_agent,
            context=[create_post_task],
            verbose=True
        )

        # Create crew
        crew = Crew(
            tasks=[
                scrape_task,
                analyze_task,
                brainstorm_task,
                web_search_task,
                create_post_task,
                notify_user_task
            ],
            process=Process.sequential
        )

        # Execute Crew
        logger.info("Starting Crew execution...")
        crew_output = crew.kickoff()

        # Extract Create Post Task Output
        create_post_task_output = next((task for task in crew_output.tasks_output if task.description == "Create Post"), None)

        # Validate Create Post Task Output
        validate_create_post_task_output(create_post_task_output)

        # Prepare Notify User Task Context
        notify_context = prepare_notify_user_task_context(create_post_task_output)
        logging.info(f"Notify Context: {notify_context}")
        notify_user_task(context=notify_context)

        logger.info("Crew execution completed successfully.")

    except Exception as e:
        logger.exception(f"An error occurred during the process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception("Unhandled exception occurred.")
        raise
