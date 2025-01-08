import os
import yaml
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from utils.webdriver_tool import WebDriverTool
from utils.linkedin_scrape_tool import LinkedInScrapeTool
from utils.post_create_agent import PostCreateAgent
from utils.logger import logger
from config.settings import Config
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

def load_yaml_configs():
    """Load configurations from YAML files."""
    files = {
        'agents': 'agents/agents.yaml',
        'tasks': 'agents/tasks.yaml'
    }
    
    configs = {}
    for config_type, file_path in files.items():
        with open(file_path, 'r') as file:
            configs[config_type] = yaml.safe_load(file)
    return configs

def main():
    try:
        logger.info("Initializing LinkedIn Content Generation Pipeline...")
        
        # Load configurations
        configs = load_yaml_configs()
        
        # Initialize tools
        linkedin_tool = LinkedInScrapeTool()
        serper_tool = SerperDevTool()
        
        # Create agents with their respective tools and LLMs
        linkedin_scrape_agent = Agent(
            config=configs['agents']['linkedin_scrape_agent'],
            tools=[linkedin_tool],
            llm="gpt-4",  # Using GPT-4 for complex pattern recognition
            verbose=True
        )
        
        linkedin_analyze_agent = Agent(
            config=configs['agents']['linkedin_interaction_analyze_agent'],
            llm="gpt-4",  # Using GPT-4 for analysis
            verbose=True
        )
        
        brainstorm_agent = Agent(
            config=configs['agents']['brainstorm_agent'],
            llm="gpt-4",  # Using GPT-4 for creative tasks
            verbose=True
        )
        
        web_search_agent = Agent(
            config=configs['agents']['web_search_agent'],
            tools=[serper_tool],
            llm="gpt-3.5-turbo",  # Using GPT-3.5 for simpler search tasks
            verbose=True
        )

        post_create_agent = PostCreateAgent(
            config=configs['agents']['post_create_agent'],
            llm="gpt-4",
            verbose=True
        )
        
        # Create tasks
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
            context=[web_search_task]
        )
        
        # Create crew
        crew = Crew(
            agents=[
                linkedin_scrape_agent,
                linkedin_analyze_agent,
                brainstorm_agent,
                web_search_agent,
                post_create_agent
            ],
            tasks=[
                scrape_task,
                analyze_task,
                brainstorm_task,
                web_search_task,
                create_post_task
            ],
            verbose=True,
            process=Process.sequential
        )
        
        # Kickoff the crew
        result = crew.kickoff()
        logger.info("LinkedIn content generation process completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"An error occurred during the process: {str(e)}")
        raise

if __name__ == "__main__":
    main()