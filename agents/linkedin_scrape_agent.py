import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

import time
from datetime import datetime, timedelta
import re
from utils.helper import save_posts_to_json
from utils.logger import logger
from config.settings import Config

class LinkedInScrapeAgent:
    def __init__(self, email=None, password=None):
        """Initialize the agent with optional dynamic inputs."""
        self.email = email or Config.LINKEDIN_EMAIL
        self.password = password or Config.LINKEDIN_PASSWORD
        self.driver = None
        self.ai_topics = [
            'llm', 'genai', 'rag', 'agent', 'openai', 'anthropic', 'llama',
            'gpt', 'claude', 'gemini', 'vector db', 'embedding', 'semantic search',
            'autogpt', 'babyagi', 'mlops', 'ai safety', 'ai ethics', 'machine learning',
            'deep learning', 'neural network', 'artificial intelligence', 'transformer',
            'large language model', 'foundation model', 'fine-tuning', 'prompt engineering',
            'hugging face', 'stable diffusion', 'dall-e', 'midjourney', 'langchain'
        ]

    def setup_driver(self):
        """Set up the Selenium driver with options."""
        try:
            options = uc.ChromeOptions()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-notifications')
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--allow-insecure-localhost')

            self.driver = uc.Chrome(options=options)
            self.driver.maximize_window()
            logger.info("Driver setup completed successfully.")
        except Exception as e:
            logger.error(f"Failed to set up the driver: {e}")
            raise

    def login(self):
        """Log in to LinkedIn with retry mechanism."""
        for attempt in range(Config.MAX_RETRIES):
            try:
                logger.info("Attempting LinkedIn login.")
                self.driver.get('https://www.linkedin.com/login')
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'username'))
                ).send_keys(self.email)

                self.driver.find_element(By.ID, 'password').send_keys(self.password)
                self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".feed-shared-update-v2"))
                )
                logger.success("Successfully logged in to LinkedIn.")
                return True
            except Exception as e:
                logger.warning(f"Login attempt {attempt + 1} failed: {e}")
                if attempt == Config.MAX_RETRIES - 1:
                    logger.error("All login attempts failed.")
                    raise
                time.sleep(2 ** attempt)

    def scrape_feed(self, max_posts=100):
        """Scrape LinkedIn feed for posts."""
        posts_data = []
        processed_ids = set()  # Track processed post IDs
        try:
            while len(posts_data) < max_posts:
                posts = self.driver.find_elements(By.CSS_SELECTOR, ".feed-shared-update-v2")
                for post in posts:
                    try:
                        post_id = self._extract_post_id(post) or hash(self._extract_post_text(post))
                        if post_id in processed_ids:
                            continue

                        text = self._extract_post_text(post)
                        if not text:
                            continue

                        is_ai_related = self._is_relevant_topic(text)
                        post_data = self._process_post_data(post, text, is_ai_related)

                        if post_data['is_ai_related']:
                            posts_data.append(post_data)
                            processed_ids.add(post_id)  # Mark this post as processed
                            if len(posts_data) >= max_posts:
                                break
                    except Exception as e:
                        logger.debug(f"Error processing post: {e}")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(Config.SCROLL_PAUSE_TIME)
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        finally:
            logger.info(f"Scraping completed. Total posts collected: {len(posts_data)}")
            return posts_data


    def run(self, max_posts=10):
        """Run the agent to scrape LinkedIn posts."""
        try:
            self.setup_driver()
            if self.login():
                posts = self.scrape_feed(max_posts=max_posts)
                save_posts_to_json(posts)
                logger.info("Scraping and saving completed successfully.")
                return posts
        except Exception as e:
            logger.error(f"Agent run failed: {e}")
        finally:
            self.close()

    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed successfully.")

    # Helper Methods
    def _is_relevant_topic(self, text):
        """Check if a post is related to AI topics."""
        text_lower = text.lower()
        return any(topic in text_lower for topic in self.ai_topics)

    def _extract_post_text(self, post):
        """Extract text content from a post."""
        try:
            text_elements = post.find_elements(By.CSS_SELECTOR, ".break-words span[dir='ltr']")
            return ' '.join([elem.text for elem in text_elements if elem.text]).strip()
        except Exception as e:
            logger.debug(f"Error extracting post text: {e}")
            return ""

    def _process_post_data(self, post, text, is_ai_related):
        """Process and structure post data."""
        try:
            post_id = self._extract_post_id(post)
            post_date = self._extract_post_date(post)
            metrics = self._extract_engagement_metrics(post)
            post_url = self._extract_post_url(post)
            linked_url = self._extract_linked_url(post)
            matched_topics = [
                topic for topic in self.ai_topics if topic.lower() in text.lower()
            ] if is_ai_related else []

            return {
                'post_id': post_id,
                'text': text,
                'date': post_date.isoformat() if post_date else None,
                'metrics': metrics,
                'url': post_url,
                'linked_url': linked_url,
                'scraped_at': datetime.now().isoformat(),
                'is_ai_related': is_ai_related,
                'matched_ai_topics': matched_topics,
            }
        except Exception as e:
            logger.debug(f"Error processing post data: {e}")
            return {}

    def _extract_post_id(self, post):
        """Extract post ID."""
        try:
            url = post.find_element(By.CSS_SELECTOR, ".feed-shared-actor__sub-description a").get_attribute("href")
            match = re.search(r'activity:(\d+)', url)
            return match.group(1) if match else None
        except Exception:
            return None

    def _extract_post_date(self, post):
        """Extract post date from LinkedIn post."""
        try:
            date_element = post.find_element(By.CSS_SELECTOR, "span.relative-time")
            date_text = date_element.text.lower()

            # Calculate the date based on relative time
            current_date = datetime.now()
            if 'h' in date_text:
                hours = int(date_text.replace('h', ''))
                return current_date - timedelta(hours=hours)
            elif 'd' in date_text:
                days = int(date_text.replace('d', ''))
                return current_date - timedelta(days=days)
            elif 'm' in date_text and 'mo' not in date_text:
                minutes = int(date_text.replace('m', ''))
                return current_date - timedelta(minutes=minutes)
            elif 's' in date_text:
                seconds = int(date_text.replace('s', ''))
                return current_date - timedelta(seconds=seconds)

            # Default fallback for unexpected formats
            return None
        except Exception as e:
            logger.debug(f"Error extracting post date: {e}")
            return None
        
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


    def _extract_engagement_metrics(self, post):
        """Extract engagement metrics (reactions, comments, shares) from the post."""
        metrics = {'reactions': 0, 'comments': 0, 'shares': 0}
        try:
            # Extract reactions
            try:
                reactions_button = post.find_element(By.CSS_SELECTOR, "button[data-reaction-details]")
                reactions_text = reactions_button.get_attribute("aria-label")
                metrics['reactions'] = self._parse_count(reactions_text)
            except NoSuchElementException:
                metrics['reactions'] = 0

            # Extract comments and shares
            social_counts = post.find_elements(By.CSS_SELECTOR, ".social-details-social-counts__item")
            for count in social_counts:
                text = count.text.lower()
                if 'comment' in text:
                    metrics['comments'] = self._parse_count(text)
                elif 'repost' in text or 'share' in text:
                    metrics['shares'] = self._parse_count(text)

            return metrics
        except Exception as e:
            logger.debug(f"Error extracting metrics: {e}")
            return metrics


    def _extract_post_url(self, post):
        """Extract post URL."""
        try:
            return post.find_element(By.CSS_SELECTOR, ".feed-shared-actor__sub-description a").get_attribute("href")
        except Exception:
            return None

    def _extract_linked_url(self, post):
        """Extract linked content URL."""
        try:
            return post.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
        except Exception:
            return None
