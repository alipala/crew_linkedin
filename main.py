from agents.linkedin_scrape_agent import LinkedInScrapeAgent
from crewai import Task
from utils.logger import logger
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

def main():
    try:
        logger.info("Initializing LinkedInScrapeAgent as a CrewAI agent...")
        agent_crew = LinkedInScrapeAgent()
        agent = agent_crew.linkedin_agent()

        logger.info("Creating task for scraping LinkedIn posts...")
        task = Task(
            description="Scrape LinkedIn posts related to AI topics and save the most engaging ones. Max posts: 10",
            expected_output="A collection of relevant LinkedIn posts with engagement metrics",
            agent=agent,
            context=None  # Optional: context from other tasks if needed
        )

        logger.info("Executing the LinkedIn scraping task...")
        output = agent.execute(task)

        if output.get("posts"):
            logger.success(f"Scraping completed successfully. Total posts scraped: {len(output['posts'])}.")
        else:
            logger.warning("No posts were scraped.")
            
    except Exception as e:
        logger.error(f"An error occurred during the scraping process: {str(e)}")
    finally:
        logger.info("LinkedIn scraping process finished.")

if __name__ == "__main__":
    main()