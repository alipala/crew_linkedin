import os
from agents.linkedin_scrape_agent import LinkedInScrapeAgent
from utils.logger import logger
from config.settings import Config
import ssl
ssl._create_default_https_context = ssl._create_unverified_context


def main():
    """
    Main function to orchestrate LinkedIn scraping using LinkedInScrapeAgent.
    """
    try:
        # Initialize the scraping agent with credentials
        logger.info("Initializing LinkedInScrapeAgent...")
        scrape_agent = LinkedInScrapeAgent(
            email=os.getenv("LINKEDIN_EMAIL", Config.LINKEDIN_EMAIL),
            password=os.getenv("LINKEDIN_PASSWORD", Config.LINKEDIN_PASSWORD)
        )

        # Run the scraping agent
        logger.info("Starting LinkedIn scraping process...")
        max_posts = int(os.getenv("MAX_POSTS", 10))  # Default to 10 posts if not provided
        posts = scrape_agent.run(max_posts=max_posts)

        if posts:
            logger.success(f"Scraping completed successfully. Total posts scraped: {len(posts)}.")
        else:
            logger.warning("No posts were scraped.")
    except Exception as e:
        logger.error(f"An error occurred during the scraping process: {e}")
    finally:
        logger.info("LinkedIn scraping process finished.")

if __name__ == "__main__":
    main()
