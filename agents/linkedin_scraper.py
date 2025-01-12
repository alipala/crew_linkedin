import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
import time
from datetime import datetime, timedelta
import re
from utils.logger import logger
from config.settings import Config
from twocaptcha import TwoCaptcha

class LinkedInFeedScraper:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.driver = None
        self.posts_scraped = 0
        self.solver = TwoCaptcha(Config.TWOCAPTCHA_API_KEY)
        self.ai_topics = [
            'llm', 'genai', 'rag', 'agent', 'openai', 'anthropic', 'llama',
            'gpt', 'claude', 'gemini', 'vector db', 'embedding', 'semantic search',
            'autogpt', 'babyagi', 'mlops', 'ai safety', 'ai ethics', 'machine learning',
            'deep learning', 'neural network', 'artificial intelligence', 'transformer',
            'large language model', 'foundation model', 'fine-tuning', 'prompt engineering',
            'hugging face', 'stable diffusion', 'dall-e', 'midjourney', 'langchain'
        ]
        
    def setup_driver(self):
        """Initialize undetected-chromedriver with enhanced anti-detection"""
        try:
            options = uc.ChromeOptions()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-notifications')
            
            # Enhanced anti-detection settings
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-dev-shm-usage')
            
            # Random user agent
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            options.add_argument(f'user-agent={user_agent}')
            
            self.driver = uc.Chrome(options=options)
            self.driver.maximize_window()
            
            # Additional stealth settings
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": user_agent,
                "platform": "Windows"
            })
            
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                """
            })
            
            logger.info("Browser setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup browser: {str(e)}")
            raise
            
    def handle_captcha(self):
        """Handle CAPTCHA if encountered during login"""
        try:
            # Check for reCAPTCHA iframe
            captcha_frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
            if not captcha_frames:
                return True
                
            logger.info("CAPTCHA detected, initiating solving process")
            
            # Switch to reCAPTCHA iframe
            self.driver.switch_to.frame(captcha_frames[0])
            
            # Get the site key
            site_key = self.driver.find_element(
                By.CSS_SELECTOR, 
                ".recaptcha-checkbox-border"
            ).get_attribute("data-sitekey")
            
            if not site_key:
                logger.warning("Could not find reCAPTCHA site key")
                return False
            
            # Solve CAPTCHA using 2captcha
            try:
                result = self.solver.recaptcha(
                    sitekey=site_key,
                    url=self.driver.current_url,
                    invisible=1,
                    enterprise=0
                )
                
                # Switch back to default content
                self.driver.switch_to.default_content()
                
                # Insert the solution
                self.driver.execute_script(
                    f'document.getElementById("g-recaptcha-response").innerHTML = "{result["code"]}";'
                )
                
                # Trigger the callback
                self.driver.execute_script(
                    'document.querySelector("form").submit();'
                )
                
                logger.info("CAPTCHA solved successfully")
                return True
                
            except Exception as e:
                logger.error(f"CAPTCHA solving failed: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error in CAPTCHA handling: {str(e)}")
            return False
        finally:
            # Ensure we're back to default content
            try:
                self.driver.switch_to.default_content()
            except:
                pass
                
    def login(self):
        """Enhanced login method with CAPTCHA handling and retry mechanism"""
        logger.debug("Entering login method")
        
        for attempt in range(Config.MAX_RETRIES):
            try:
                logger.info(f"Attempting LinkedIn login (Attempt {attempt + 1})")
                self.driver.get('https://www.linkedin.com/login')
                time.sleep(3)
                
                # Clear cookies and storage before login
                self.driver.delete_all_cookies()
                self.driver.execute_script("window.localStorage.clear();")
                self.driver.execute_script("window.sessionStorage.clear();")
                
                # Fill login form
                email_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'username'))
                )
                email_field.clear()
                email_field.send_keys(self.email)
                time.sleep(1)
                
                password_field = self.driver.find_element(By.ID, 'password')
                password_field.clear()
                password_field.send_keys(self.password)
                time.sleep(1)
                
                # Submit login form
                login_button = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    "button[type='submit']"
                )
                login_button.click()
                
                # Check for CAPTCHA
                if self.handle_captcha():
                    logger.info("CAPTCHA handled successfully")
                
                # Wait for successful login
                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".feed-shared-update-v2"))
                    )
                    logger.info("Successfully logged in to LinkedIn")
                    return True
                    
                except TimeoutException:
                    # Check for security verification
                    if "security verification" in self.driver.page_source.lower():
                        logger.warning("Security verification page detected")
                        raise Exception("Security verification required")
                        
                    # Check for CAPTCHA again
                    if self.handle_captcha():
                        continue
                        
            except Exception as e:
                logger.warning(f"Login attempt {attempt + 1} failed: {str(e)}")
                if attempt == Config.MAX_RETRIES - 1:
                    logger.exception("All login attempts failed")
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
                
            finally:
                # Clear sensitive data
                if 'email_field' in locals():
                    self.driver.execute_script(
                        "arguments[0].value = '';", 
                        email_field
                    )
                if 'password_field' in locals():
                    self.driver.execute_script(
                        "arguments[0].value = '';", 
                        password_field
                    )
                    
        return False

    def extract_post_id(self, post):
            """Extract unique identifier for the LinkedIn post"""
            try:
                post_url = post.find_element(By.CSS_SELECTOR, ".feed-shared-actor__sub-description a").get_attribute("href")
                match = re.search(r'activity:(\d+)', post_url)
                return match.group(1) if match else None
            except Exception:
                return None

    def extract_post_date(self, post):
        """Extract and parse the post date"""
        try:
            date_element = post.find_element(By.CSS_SELECTOR, "span.relative-time")
            date_text = date_element.text.lower()
            
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
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting post date: {str(e)}")
            return None
            
    def extract_engagement_metrics(self, post):
        """Extract engagement metrics (reactions, comments, shares)"""
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
        
    def _parse_count(self, count_text):
        """Parse and convert engagement count text to numbers"""
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
            
    def extract_post_text(self, post):
        """Extract the main text content from the post"""
        try:
            text_elements = post.find_elements(By.CSS_SELECTOR, ".break-words span[dir='ltr']")
            text_content = ' '.join([elem.text for elem in text_elements if elem.text])
            return text_content.strip()
        except Exception as e:
            logger.debug(f"Error extracting post text: {str(e)}")
            return ""
            
    def is_relevant_topic(self, text):
        """Check if the post contains relevant AI topics"""
        text_lower = text.lower()
        return any(topic in text_lower for topic in self.ai_topics)

    def process_post_data(self, post, text, is_ai_related):
        """Process and structure the post data"""
        matched_topics = []
        if is_ai_related:
            matched_topics = [topic for topic in self.ai_topics if topic.lower() in text.lower()]
        
        post_url = None
        try:
            # Try different selectors for post URL
            selectors = [
                "a[data-test-app-aware-link]",  # General post links
                ".feed-shared-actor__container a",  # Author/post container links
                ".feed-shared-update-v2__content a",  # Content links
                ".feed-shared-actor__meta a"  # Post metadata links
            ]
            
            for selector in selectors:
                elements = post.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    url = element.get_attribute("href")
                    if url and 'activity' in url:
                        post_url = url
                        break
                if post_url:
                    break
                    
        except Exception as e:
            logger.debug(f"Error extracting post URL: {e}")

        return {
            'post_id': self.extract_post_id(post),
            'text': text,
            'date': self.extract_post_date(post),
            'metrics': self.extract_engagement_metrics(post),
            'url': post_url,
            'linked_url': post.find_element(By.CSS_SELECTOR, "a").get_attribute("href"),
            'scraped_at': datetime.now().isoformat(),
            'is_ai_related': is_ai_related,
            'matched_ai_topics': matched_topics
        }
    
    def scrape_feed(self, max_posts=100, days_limit=4, timeout_seconds=120):
        """Scrape LinkedIn feed for AI-related posts"""
        posts_data = []
        processed_texts = set()  # Track unique post texts
        start_time = time.time()
        last_post_time = start_time
        
        logger.info("Starting feed scrape")
        
        try:
            while len(posts_data) < max_posts:
                # Check timeout
                if time.time() - last_post_time > timeout_seconds:
                    logger.warning(f"Timeout after {timeout_seconds}s without new posts")
                    break
                    
                # Scroll and get posts
                posts = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".feed-shared-update-v2"))
                )
                
                for post in posts:
                    try:
                        # Extract and validate text
                        text = self.extract_post_text(post)
                        if not text or text in processed_texts:
                            continue
                            
                        logger.debug(f"Found post text: {text[:200]}...")
                        is_ai_related = self.is_relevant_topic(text)
                        
                        if is_ai_related:
                            logger.info("AI-related post found!")
                            processed_texts.add(text)  # Add to processed set
                            post_data = self.process_post_data(post, text, is_ai_related)
                            
                            if post_data['is_ai_related']:
                                posts_data.append(post_data)
                                last_post_time = time.time()
                                logger.info(f"Saved AI post {len(posts_data)} of {max_posts}")
                                
                                # Check if we've reached the limit
                                if len(posts_data) >= max_posts:
                                    logger.info(f"Reached maximum posts limit: {max_posts}")
                                    return posts_data
                                
                    except StaleElementReferenceException:
                        continue
                    except Exception as e:
                        logger.debug(f"Error processing post: {e}")
                        continue
                        
                # Scroll with JavaScript
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                time.sleep(Config.SCROLL_PAUSE_TIME)
                
        except TimeoutException:
            logger.warning(f"Operation timed out after {timeout_seconds} seconds")
        except Exception as e:
            logger.error(f"Scraping error: {e}")
        finally:
            logger.info(f"Completed in {time.time() - start_time:.2f}s. Found {len(posts_data)} AI posts")
            return posts_data
            
    def close(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            
    def run(self, max_posts=100):
        """Execute the complete scraping workflow"""
        try:
            self.setup_driver()
            if self.login():
                posts = self.scrape_feed(max_posts=max_posts)
                return posts[:max_posts]  # Ensure we don't return more than max_posts
        except Exception as e:
            logger.error(f"Scraping failed: {str(e)}")
            return []
        finally:
            self.close()