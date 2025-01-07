from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from utils.models import LinkedInPost, PostMetrics
from utils.logger import logger
from utils.helper import save_posts_to_json
from config.settings import Config
from datetime import datetime
import re
import time
from typing import List, Dict, Optional, Any

class LinkedInScraper:
    """LinkedIn scraping functionality implementation."""
    
    def __init__(self, driver):
        self.driver = driver

    def execute_scraping(self, max_posts: int = 10) -> Dict[str, Any]:
        """Execute LinkedIn scraping process."""
        try:
            self._login()
            posts = self._scrape_posts(max_posts)
            
            # Format posts keeping full text and URLs
            formatted_posts = []
            for post in posts:
                post_dict = {
                    'post_id': post.post_id,
                    'text': post.text,
                    'date': post.date,
                    'metrics': {
                        'reactions': post.metrics.reactions,
                        'comments': post.metrics.comments,
                        'shares': post.metrics.shares
                    },
                    'url': post.url,
                    'scraped_at': datetime.now().isoformat()
                }
                formatted_posts.append(post_dict)
            
            # Generate timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_posts_{timestamp}.json"
            
            # Save to JSON with proper formatting
            filepath = save_posts_to_json(formatted_posts, filename)
            
            logger.info(f"Successfully saved {len(formatted_posts)} posts to {filepath}")
            return {
                "status": "success",
                "posts": formatted_posts,
                "filepath": filepath,
                "post_count": len(formatted_posts)
            }
            
        except Exception as e:
            logger.error(f"Error during LinkedIn scraping: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _login(self) -> None:
        """Handle LinkedIn login process."""
        try:
            self.driver.get('https://www.linkedin.com/login')
            
            username_elem = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'username'))
            )
            username_elem.send_keys(Config.LINKEDIN_EMAIL)
            
            password_elem = self.driver.find_element(By.ID, 'password')
            password_elem.send_keys(Config.LINKEDIN_PASSWORD)
            
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            
            # Wait for feed to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".feed-shared-update-v2"))
            )
            logger.info("Successfully logged in to LinkedIn")
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise

    def _scrape_posts(self, max_posts: int) -> List[LinkedInPost]:
        """Scrape LinkedIn posts and return structured data."""
        posts_data = []
        processed_posts = set()
        scroll_attempts = 0
        max_scroll_attempts = 50
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while len(posts_data) < max_posts and scroll_attempts < max_scroll_attempts:
            # Find all posts in the current view
            posts = self.driver.find_elements(By.CSS_SELECTOR, ".feed-shared-update-v2")
            
            for post in posts:
                try:
                    # Scroll post into view for better interaction
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", post)
                    time.sleep(1)  # Wait for dynamic content to load

                    # Click "see more" if present
                    try:
                        see_more = post.find_element(By.CSS_SELECTOR, ".feed-shared-inline-show-more-text__see-more-less-toggle")
                        see_more.click()
                        time.sleep(0.5)
                    except NoSuchElementException:
                        pass

                    # Extract post data
                    text = self._extract_post_text(post)
                    if not text or hash(text) in processed_posts:
                        continue

                    url = self._extract_post_url(post)
                    metrics = self._extract_metrics(post)
                    post_id = self._extract_post_id(post)
                    
                    post_data = LinkedInPost(
                        post_id=post_id,
                        text=text,
                        date=None,
                        metrics=PostMetrics(**metrics),
                        url=url,
                        scraped_at=datetime.now()
                    )

                    posts_data.append(post_data)
                    processed_posts.add(hash(text))
                    
                    if len(posts_data) >= max_posts:
                        break

                except Exception as e:
                    logger.warning(f"Error processing post: {str(e)}")
                    continue

            # Scroll down to load more posts
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(Config.SCROLL_PAUSE_TIME)
            
            # Check if page has loaded new content
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
            else:
                last_height = new_height
                scroll_attempts = 0

        return posts_data

    def _extract_post_text(self, post) -> str:
        """Extract full text content from a post."""
        try:
            # Get all text elements including see more content
            text_elements = post.find_elements(By.CSS_SELECTOR, ".feed-shared-update-v2__description-wrapper > span[dir='ltr'], .feed-shared-inline-show-more-text span[dir='ltr']")
            # Keep original formatting
            full_text = '\n'.join([elem.text for elem in text_elements if elem.text])
            return full_text
        except Exception as e:
            logger.warning(f"Error extracting post text: {str(e)}")
            return ""

    def _extract_post_url(self, post) -> Optional[str]:
        """Extract the URL of the post."""
        try:
            # First try to get the main post URL
            url_selectors = [
                ".feed-shared-update-v2__meta-container a",
                ".feed-shared-actor__container a",
                ".feed-shared-actor__meta a",
                ".feed-shared-update-v2__content a"
            ]
            
            for selector in url_selectors:
                try:
                    element = post.find_element(By.CSS_SELECTOR, selector)
                    url = element.get_attribute("href")
                    if url and "linkedin.com/posts" in url:
                        return url
                except NoSuchElementException:
                    continue
                    
            return None
        except Exception as e:
            logger.warning(f"Error extracting post URL: {str(e)}")
            return None

    def _extract_post_id(self, post) -> Optional[str]:
        """Extract post ID from post URL."""
        try:
            url = self._extract_post_url(post)
            if url:
                match = re.search(r'activity:(\d+)', url)
                return match.group(1) if match else None
        except Exception:
            return None
        return None

    def _extract_metrics(self, post) -> Dict[str, int]:
        """Extract engagement metrics from a post."""
        metrics = {'reactions': 0, 'comments': 0, 'shares': 0}
        try:
            # Extract reactions
            reactions_elem = post.find_element(By.CSS_SELECTOR, "button[data-reaction-details]")
            metrics['reactions'] = self._parse_count(reactions_elem.get_attribute("aria-label"))

            # Extract comments and shares
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

    def _parse_count(self, count_text: str) -> int:
        """Parse numeric values from text (e.g., '1.2K' -> 1200)."""
        if not count_text:
            return 0
            
        try:
            match = re.search(r'([\d,.]+)([KkMm])?', count_text)
            if not match:
                return 0
                
            number = float(match.group(1).replace(',', ''))
            suffix = match.group(2).lower() if match.group(2) else ''
            
            if suffix == 'k':
                number *= 1000
            elif suffix == 'm':
                number *= 1000000
                
            return int(number)
            
        except Exception:
            return 0