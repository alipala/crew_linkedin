import os
import yaml
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from utils.webdriver_tool import WebDriverTool
from utils.linkedin_scrape_tool import LinkedInScrapeTool
from agents.post_create_agent import PostCreateAgent
from agents.notification_agent import NotificationAgent
from config.settings import Config
from utils.logger import logger
import ssl
from tests.verify_config import verify_configuration
import sys


ssl._create_default_https_context = ssl._create_unverified_context

def load_yaml_configs():
    """Load configurations from YAML files."""
    files = {
        'agents': 'agents/agents.yaml',
        'tasks': 'agents/tasks.yaml'
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

def main():

    # Verify configuration first
    if not verify_configuration():
        logger.error("Configuration verification failed. Exiting...")
        sys.exit(1)
        
    # If verification passes, continue with your application
    logger.info("Configuration verified. Starting application...")

    try:
        logger.info("Initializing LinkedIn Content Generation Pipeline...")

        # Load configurations
        configs = load_yaml_configs()

        # Initialize tools
        linkedin_tool = LinkedInScrapeTool()
        serper_tool = SerperDevTool()

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
        post_create_agent = PostCreateAgent(
            config=configs['agents']['post_create_agent'],
            llm="gpt-4",
            verbose=True
        )
        notification_agent = NotificationAgent(
            config=configs['agents']['notification_agent'],
            llm="gpt-3.5-turbo",
            verbose=True
        )

        # Initialize tasks
        scrape_task = Task(
            config=configs['tasks']['scrape_linkedin_posts'],
            agent=linkedin_scrape_agent
        )
        analyze_task = Task(
            config=configs['tasks']['analyze_engagement'],
            agent=linkedin_analyze_agent,
            context=[scrape_task]
        )
        brainstorm_task = Task(
            config=configs['tasks']['generate_ideas'],
            agent=brainstorm_agent,
            context=[analyze_task]
        )
        web_search_task = Task(
            config=configs['tasks']['conduct_web_search'],
            agent=web_search_agent,
            context=[brainstorm_task]
        )
        create_post_task = Task(
            config=configs['tasks']['create_post'],
            agent=post_create_agent,
            context=[web_search_task],
            output_dict=True
        )
        notify_user_task = Task(
            config=configs['tasks']['notify_user'],
            agent=notification_agent,
            context=[create_post_task],
            output_dict=True
        )

        # Create crew
        crew = Crew(
            agents=[
                linkedin_scrape_agent,
                linkedin_analyze_agent,
                brainstorm_agent,
                web_search_agent,
                post_create_agent,
                notification_agent
            ],
            tasks=[
                scrape_task,
                analyze_task,
                brainstorm_task,
                web_search_task,
                create_post_task,
                notify_user_task
            ],
            verbose=True,
            process=Process.sequential
        )

        # Log task states before kickoff
        logger.debug("Tasks initialized. Starting the execution pipeline...")

        # Execute all tasks via the crew
        result = crew.kickoff()

        # Log results of tasks
        logger.info("LinkedIn content generation process completed successfully.")
        logger.debug(f"Final result: {result}")

    except Exception as e:
        logger.error(f"An error occurred during the process: {e}")
        raise

if __name__ == "__main__":
    main()
