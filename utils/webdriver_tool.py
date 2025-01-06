from crewai.tools import BaseTool
import undetected_chromedriver as uc
from typing import Optional, ClassVar

class WebDriverTool(BaseTool):
    name: str = "WebDriver Tool"
    description: str = "Manages WebDriver setup and teardown for web scraping tasks."
    driver: ClassVar[Optional[uc.Chrome]] = None

    def _run(self, action: str) -> Optional[uc.Chrome]:
        if action == "setup":
            return self.setup_driver()
        elif action == "teardown":
            self.teardown_driver()
            return None
        else:
            raise ValueError(f"Unknown action: {action}")

    def setup_driver(self) -> uc.Chrome:
        """Set up and return a new Chrome WebDriver instance."""
        options = uc.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-notifications')
        
        WebDriverTool.driver = uc.Chrome(options=options)
        WebDriverTool.driver.maximize_window()
        return WebDriverTool.driver

    def teardown_driver(self) -> None:
        """Clean up the WebDriver instance."""
        if WebDriverTool.driver:
            try:
                WebDriverTool.driver.quit()
            except Exception:
                pass  # Ignore errors during cleanup
            finally:
                WebDriverTool.driver = None