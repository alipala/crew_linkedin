from utils.logger import logger
import os
import yaml
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from utils.linkedin_scrape_tool import LinkedInScrapeTool
from agents.post_create_agent import PostCreateAgent
from agents.notification_agent import NotificationAgent
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

def test_notification_agent(configs):
    # Create a mock task result as context
    test_context = [{
        'description': 'Previous task description',
        'expected_output': 'Previous task expected output',
        'raw': {
            'content': 'This is a test LinkedIn post about AI and technology.',
            'image_url': 'https://example.com/test-image.jpg',
            'status': 'success',
            'title': 'Test LinkedIn Post: AI Technology Trends 2025',
            'require_approval': True
        }
    }]

    # Initialize notification agent
    notification_agent = NotificationAgent(
        config=configs['agents']['notification_agent'],
        llm="gpt-3.5-turbo",
        verbose=True
    )

    # Create test task 
    test_notify_task = Task(
        description="Send email notification for post review",
        expected_output="Email notification sent successfully with post content",
        agent=notification_agent,
        context=test_context,
        output_dict={
            "email_sent": bool,
            "recipient": str,
            "status": str
        }
    )

    try:
        logger.info("Executing test notification task...")
        result = test_notify_task.execute_sync()
        logger.info(f"Test notification result: {result}")
        return result

    except Exception as e:
        logger.error(f"Test notification failed: {e}", exc_info=True)
        return None
    
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
        logger.debug(f"Configurations loaded: {configs}")

        # Initialize tools
        linkedin_tool = LinkedInScrapeTool()
        serper_tool = SerperDevTool()

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
            output_dict={
                "content": str,
                "image_url": str,
                "status": str,
                "title": str,
                "require_approval": bool
            }
        )
        
        notify_user_task = Task(
            config=configs['tasks']['notify_user'],
            agent=notification_agent,
            context=[create_post_task],
            output_dict={
                "email_sent": bool,
                "recipient": str,
                "status": str
            }
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

        logger.info("Running notification agent test...")
        test_result = test_notification_agent(configs)  # Pass configs to the test function
        logger.info(f"Notification test completed with result: {test_result}")

        # Log results of tasks
        logger.info("LinkedIn content generation process completed successfully.")
        return result

    except Exception as e:
        logger.exception(f"An error occurred during the process: {e}")
        raise

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception("Unhandled exception occurred.")
        raise

