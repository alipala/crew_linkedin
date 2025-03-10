from utils.logger import logger
import os
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from utils.linkedin_google_search import LinkedInGoogleSearchTool
from utils.notification_slack_tool import NotificationSlackTool
from utils.blog_agent import HashNodePublisher
from utils.models import LinkedInPostContent
from utils.topic_manager import TopicManager
import ssl
import logging
import yaml
import requests
import json
from typing import Optional, Dict, Any, List

ssl._create_default_https_context = ssl._create_unverified_context

logging.basicConfig(level=logging.DEBUG)

class SetupConfig:
    # Define file paths for YAML configurations
    files = {
        'agents': 'config/agents.yaml',
        'tasks': 'config/tasks.yaml'
    }

    def __init__(self):
        # Load configurations from YAML files
        self.configs = {}
        for config_type, file_path in self.files.items():
            with open(file_path, 'r') as file:
                self.configs[config_type] = yaml.safe_load(file)

        # Assign loaded configurations to instance variables
        self.agents_config = self.configs['agents']
        self.tasks_config = self.configs['tasks']

def test_api():
    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': os.getenv('GOOGLE_SEARCH_API_KEY'),
        'cx': os.getenv('GOOGLE_SEARCH_CX'),
        'q': 'site:linkedin.com/posts/ LLM',
        'num': 1
    }
    
    response = requests.get(base_url, params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def create_crew(config: SetupConfig, topics: Optional[List[str]] = None) -> Crew:
    """Create and configure the CrewAI crew with agents and tasks"""
    try:
        logger.debug(f"Creating crew with topics: {topics}")
        logger.debug(f"Topics type: {type(topics)}")

        # Validate and prepare topics
        if not topics:
            logger.warning("No topics provided, using defaults from topic manager")
            topic_manager = TopicManager()
            topics = topic_manager.get_current_topics()

        # Initialize tools
        linkedin_tool = LinkedInGoogleSearchTool()
        serper_tool = SerperDevTool()
        notification_slack_tool = NotificationSlackTool()
        hashnode_publisher = HashNodePublisher()

        # Initialize agents
        linkedin_post_search_agent = Agent(
            config=config.agents_config["linkedin_post_search_agent"],
            tools=[linkedin_tool, serper_tool],
            llm="gpt-4o",
            verbose=True
        )

        linkedin_analyze_agent = Agent(
            config=config.agents_config["linkedin_interaction_analyze_agent"],
            llm="gpt-4o",
            verbose=True
        )

        brainstorm_agent = Agent(
            config=config.agents_config["brainstorm_agent"],
            llm="gpt-4o",
            verbose=True
        )

        web_search_agent = Agent(
            config=config.agents_config["web_search_agent"],
            tools=[serper_tool],
            llm="gpt-3.5-turbo",
            verbose=True
        )

        post_create_agent = Agent(
            config=config.agents_config["post_create_agent"],
            llm="gpt-4o",
            verbose=True
        )

        notification_agent = Agent(
            config=config.agents_config["notification_agent"],
            tools=[notification_slack_tool],
            llm="gpt-3.5-turbo",
            verbose=True
        )

        blog_agent = Agent(
            config=config.agents_config["blog_agent"],
            tools=[hashnode_publisher],
            llm="gpt-4o",
            verbose=True
)

        search_task = Task(
            config=config.tasks_config["search_linkedin_posts"],
            agent=linkedin_post_search_agent,
            tools=[linkedin_tool, serper_tool],
            task_kwargs={
                'topics': topics if isinstance(topics, list) else [topics]
            }
        )

        analyze_task = Task(
            config=config.tasks_config["analyze_engagement"],
            agent=linkedin_analyze_agent,
            context=[search_task]
        )

        brainstorm_task = Task(
            config=config.tasks_config["generate_ideas"],
            agent=brainstorm_agent,
            context=[analyze_task]
        )

        web_search_task = Task(
            config=config.tasks_config["conduct_web_search"],
            agent=web_search_agent,
            context=[brainstorm_task]
        )

        compose_blog_task = Task(
            config=config.tasks_config["compose_blog_content"],
            agent=blog_agent,
            context=[web_search_task],
            verbose=True
            )
        
        create_post_task = Task(
            config=config.tasks_config["create_post"],
            agent=post_create_agent,
            context=[compose_blog_task],
            output_pydantic=LinkedInPostContent,
            verbose=True
        )

        notify_user_task = Task(
            config=config.tasks_config["notify_user"],
            agent=notification_agent,
            context=[create_post_task],
            verbose=True
        )

        # Create crew
        crew = Crew(
            agents=[
                linkedin_post_search_agent,
                linkedin_analyze_agent,
                brainstorm_agent,
                web_search_agent,
                blog_agent,          
                post_create_agent,
                notification_agent
            ],
            tasks=[
                search_task,
                analyze_task,
                brainstorm_task,
                web_search_task,
                compose_blog_task, 
                create_post_task,
                notify_user_task
            ],
            process=Process.sequential,
            verbose=True
        )

        return crew

    except Exception as e:
        logger.error(f"Error creating crew: {e}")
        raise

def main(custom_topics: Optional[List[str]] = None) -> Dict[str, Any]:
    """Main function to execute the crew workflow"""
    try:
        # Initialize configuration
        config = SetupConfig()
        
        # Get topics from parameter or topic manager
        topic_manager = TopicManager()
        topics = custom_topics or topic_manager.get_current_topics()
        
        logger.info(f"Executing crew with topics: {topics}")
        
        # Create crew WITH topics
        crew = create_crew(config, topics=topics)  # Pass topics here
        
        # Pass topics in inputs
        result = crew.kickoff(inputs={
            'topics': topics,
            'task_data': {
                'search_linkedin_posts': {
                    'topics': topics
                }
            }
        })
        
        logger.info("Crew execution completed successfully.")
        return result

    except Exception as e:
        logger.exception(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    test_api()
    main()