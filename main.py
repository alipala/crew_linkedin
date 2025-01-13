from utils.logger import logger
import os
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from utils.linkedin_scrape_tool import LinkedInScrapeTool
from utils.notification_slack_tool import NotificationSlackTool
from utils.models import LinkedInPostContent
import ssl
import logging
import yaml

ssl._create_default_https_context = ssl._create_unverified_context

logging.basicConfig(level=logging.DEBUG)

class setupConfig():
    # Define file paths for YAML configurations
    files = {
        'agents': 'config/agents.yaml',
        'tasks': 'config/tasks.yaml'
    }

    # Load configurations from YAML files
    configs = {}
    for config_type, file_path in files.items():
        with open(file_path, 'r') as file:
            configs[config_type] = yaml.safe_load(file)

    # Assign loaded configurations to specific variables
    agents_config = configs['agents']
    tasks_config = configs['tasks']

def main():
    try:
        # Initialize tools
        linkedin_tool = LinkedInScrapeTool()
        serper_tool = SerperDevTool()
        notification_slack_tool = NotificationSlackTool()

        # Initialize agents
        linkedin_scrape_agent = Agent(
            config=setupConfig.agents_config["linkedin_scrape_agent"],
            tools=[linkedin_tool],
            llm="gpt-4",
            verbose=True
        )

        linkedin_analyze_agent = Agent(
            config=setupConfig.agents_config["linkedin_interaction_analyze_agent"],
            llm="gpt-4",
            verbose=True
        )

        brainstorm_agent = Agent(
            config=setupConfig.agents_config["brainstorm_agent"],
            llm="gpt-4",
            verbose=True
        )

        web_search_agent = Agent(
            config=setupConfig.agents_config["web_search_agent"],
            tools=[serper_tool],
            llm="gpt-3.5-turbo",
            verbose=True
        )

        post_create_agent = Agent(
            config=setupConfig.agents_config["post_create_agent"],
            llm="gpt-4",
            verbose=True
        )

        notification_agent = Agent(
            config=setupConfig.agents_config["notification_agent"],
            tools=[notification_slack_tool],
            llm="gpt-3.5-turbo",
            verbose=True
        )

        # Initialize tasks
        scrape_task = Task(
            config=setupConfig.tasks_config["scrape_linkedin_posts"],
            agent=linkedin_scrape_agent
        )

        analyze_task = Task(
            config=setupConfig.tasks_config["analyze_engagement"],
            agent=linkedin_analyze_agent,
            context=[scrape_task]
        )

        brainstorm_task = Task(
            config=setupConfig.tasks_config["generate_ideas"],
            agent=brainstorm_agent,
            context=[analyze_task]
        )

        web_search_task = Task(
            config=setupConfig.tasks_config["conduct_web_search"],
            agent=web_search_agent,
            context=[brainstorm_task]
        )

        create_post_task = Task(
            config=setupConfig.tasks_config["create_post"],
            agent=post_create_agent,
            context=[web_search_task],
            output_pydantic=LinkedInPostContent,
            verbose=True
        )

        notify_user_task = Task(
            config=setupConfig.tasks_config["notify_user"],
            agent=notification_agent,
            context=[create_post_task],
            verbose=True
            )

        # Create and execute crew
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
            process=Process.sequential,
            verbose=True
        )

        result = crew.kickoff()
        logger.info("Crew execution completed successfully.")
        return result

    except Exception as e:
        logger.exception(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    main()