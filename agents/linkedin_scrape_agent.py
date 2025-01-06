from crewai import Agent, Task
from crewai.project import CrewBase
from utils.models import AgentConfig
from utils.logger import logger
from utils.webdriver_tool import WebDriverTool
from config.settings import Config
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime
import time
import re
import yaml
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from utils.helper import save_posts_to_json, format_post_data

class LinkedInAgentConfig(BaseModel):
    """Pydantic model for LinkedIn agent configuration"""
    ai_topics: List[str] = Field(default_factory=list)
    credentials: Dict[str, str] = Field(default_factory=dict)

class CustomLinkedInAgent(Agent):
    """Custom Agent class that extends CrewAI Agent with LinkedIn-specific functionality."""
    
    def __init__(self, *args, **kwargs):
        # Extract and validate custom attributes
        config = LinkedInAgentConfig(
            ai_topics=kwargs.pop('ai_topics', []),
            credentials=kwargs.pop('credentials', {})
        )
        
        # Initialize parent class
        super().__init__(*args, **kwargs)
        
        # Store configuration
        self._config = config

    @property
    def ai_topics(self) -> List[str]:
        return self._config.ai_topics

    @property
    def credentials(self) -> Dict[str, str]:
        return self._config.credentials

    def execute(self, task: Task):
        """Execute the given task using the agent's capabilities."""
        try:
            logger.info("Starting LinkedIn scraping task...")
            # Get the WebDriver tool
            webdriver_tool = self.tools[0]
            
            # Setup the driver
            driver = webdriver_tool._run("setup")
            
            # Fixed max_posts value
            max_posts = 10
            
            self._login(driver)
            posts = self._scrape_feed(driver, max_posts)
            
            formatted_posts = [format_post_data(post) for post in posts]
            filepath = save_posts_to_json(formatted_posts)
            
            logger.info(f"Saved {len(formatted_posts)} posts to {filepath}")
            return {"posts": formatted_posts, "filepath": filepath}
        
        finally:
            # Use teardown action
            self.tools[0]._run("teardown")

    def _login(self, driver):
        try:
            driver.get('https://www.linkedin.com/login')
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'username'))
            ).send_keys(self.credentials['email'])
            
            driver.find_element(By.ID, 'password').send_keys(self.credentials['password'])
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".feed-shared-update-v2"))
            )
            logger.info("Successfully logged in to LinkedIn.")
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise RuntimeError(f"Login failed: {str(e)}")

    def _parse_count(self, count_text):
        """Parse a count string (e.g., '1.2K', '3M') into an integer."""
        if not count_text:
            return 0
            
        try:
            match = re.search(r'([\d,.]+)([KkMm])?', count_text)
            if not match:
                return 0
                
            number = match.group(1).replace(',', '')
            suffix = match.group(2).lower() if match.group(2) else ''
            
            value = float(number)
            if suffix == 'k':
                value *= 1000
            elif suffix == 'm':
                value *= 1000000
                
            return int(value)
            
        except Exception:
            return 0

    def _extract_metrics(self, post):
        """Extract engagement metrics from a post."""
        metrics = {'reactions': 0, 'comments': 0, 'shares': 0}
        try:
            # Get reactions count
            reactions_button = post.find_element(By.CSS_SELECTOR, "button[data-reaction-details]")
            reactions_text = reactions_button.get_attribute("aria-label")
            metrics['reactions'] = self._parse_count(reactions_text)

            # Get comments and shares
            social_counts = post.find_elements(By.CSS_SELECTOR, ".social-details-social-counts__item")
            for count in social_counts:
                text = count.text.lower()
                if 'comments' in text:
                    metrics['comments'] = self._parse_count(text)
                elif 'reposts' in text:
                    metrics['shares'] = self._parse_count(text)

        except Exception as e:
            logger.debug(f"Error extracting metrics: {str(e)}")
        return metrics

    def _extract_linked_url(self, post):
        try:
            return post.find_element(By.CSS_SELECTOR, ".feed-shared-actor__container a").get_attribute("href")
        except NoSuchElementException:
            return None

    def _scrape_feed(self, driver, max_posts):
        """Scrape the LinkedIn feed for relevant posts."""
        posts_data = []
        processed_posts = set()
        scroll_attempts = 0
        max_scroll_attempts = 50
        
        while len(posts_data) < max_posts and scroll_attempts < max_scroll_attempts:
            posts = driver.find_elements(By.CSS_SELECTOR, ".feed-shared-update-v2")
            
            for post in posts:
                try:
                    # Scroll the post into view and wait for dynamic content
                    driver.execute_script("arguments[0].scrollIntoView(true);", post)
                    time.sleep(1)  # Wait for metrics to load
                    
                    text = self._extract_post_text(post)
                    if not text or hash(text) in processed_posts:
                        continue
                        
                    if self._is_relevant_topic(text):
                        post_data = {
                            "post_id": self._extract_post_id(post),
                            "text": text,
                            "date": None,
                            "metrics": self._extract_metrics(post),
                            "url": None,
                            "linked_url": self._extract_linked_url(post),
                            "scraped_at": datetime.now().isoformat(),
                            "is_ai_related": True,
                            "matched_ai_topics": [topic for topic in self.ai_topics if topic.lower() in text.lower()]
                        }
                        
                        processed_posts.add(hash(text))
                        posts_data.append(post_data)
                        logger.info(f"Saved AI post {len(posts_data)} of {max_posts}")
                        
                        if len(posts_data) >= max_posts:
                            break
                            
                except Exception as e:
                    logger.warning(f"Error processing post: {str(e)}")
                    continue
            
            # Scroll and wait for new content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            scroll_attempts += 1
            
        return posts_data

    def _extract_post_text(self, post):
        try:
            text_elements = post.find_elements(By.CSS_SELECTOR, ".break-words span[dir='ltr']")
            text_content = ' '.join([elem.text for elem in text_elements if elem.text])
            return text_content.strip()
        except Exception as e:
            logger.debug(f"Error extracting post text: {str(e)}")
            return ""

    def _extract_post_id(self, post):
        try:
            url = post.find_element(By.CSS_SELECTOR, ".feed-shared-actor__sub-description a").get_attribute("href")
            match = re.search(r'activity:(\d+)', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _is_relevant_topic(self, text):
        text_lower = text.lower()
        return any(topic in text_lower for topic in self.ai_topics)

@CrewBase
class LinkedInScrapeAgent:
    """LinkedIn scraping agent implementation using CrewAI framework."""
    
    agents_config = 'agents.yaml'
    tasks_config = 'tasks.yaml'

    def __init__(self):
        # Load agent configuration from YAML
        import os
        
        # Get the directory where the current file (linkedin_scrape_agent.py) is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # The YAML files are in the same directory as this file
        agents_yaml_path = os.path.join(current_dir, self.agents_config)
        
        # Print the path for debugging
        print(f"Looking for agents.yaml at: {agents_yaml_path}")
        
        # Load the YAML file
        try:
            with open(agents_yaml_path, 'r') as file:
                self.config = yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Could not find agents.yaml at {agents_yaml_path}. Please ensure the file exists in the correct location.")

    def linkedin_agent(self) -> CustomLinkedInAgent:
        """Create and configure the LinkedIn scraping agent."""
        if 'linkedin_scrape_agent' not in self.config:
            raise ValueError("linkedin_scrape_agent configuration not found in agents.yaml")
            
        agent_config = self.config['linkedin_scrape_agent']
        
        # Validate required fields in configuration
        required_fields = ['role', 'goal', 'backstory', 'ai_topics']
        missing_fields = [field for field in required_fields if field not in agent_config]
        if missing_fields:
            raise ValueError(f"Missing required fields in agent configuration: {', '.join(missing_fields)}")
        
        # Validate credentials
        credentials = {
            'email': Config.LINKEDIN_EMAIL,
            'password': Config.LINKEDIN_PASSWORD
        }
        
        if not credentials['email'] or not credentials['password']:
            raise ValueError("LinkedIn credentials (email and password) must be set in the environment variables.")
        
        # Validate AI topics
        ai_topics = agent_config.get('ai_topics', [])
        if not isinstance(ai_topics, list):
            raise ValueError("ai_topics must be a list in the configuration")

        # Create agent with custom attributes
        return CustomLinkedInAgent(
            role=agent_config['role'],
            goal=agent_config['goal'],
            backstory=agent_config['backstory'],
            tools=[WebDriverTool()],
            verbose=agent_config.get('verbose', True),
            ai_topics=ai_topics,
            credentials=credentials
        )