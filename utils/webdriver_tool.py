from crewai.tools import BaseTool
import undetected_chromedriver as uc
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class WebDriverTool(BaseTool):
    name: str = "WebDriver Tool"
    description: str = "Manages Chrome WebDriver sessions for web automation tasks."
    driver: Optional[uc.Chrome] = None
    
    # Allow arbitrary types
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, args: Optional[Dict[str, Any]] = None) -> Optional[uc.Chrome]:
        """Execute the WebDriver tool."""
        # Validate args if provided
        if args and 'action' in args:
            action = args['action']
        else:
            action = 'setup'  # Default action
            
        if action == "setup":
            return self._setup_driver()
        elif action == "teardown":
            self._teardown_driver()
            return None
        else:
            raise ValueError(f"Unknown action: {action}")

    def _setup_driver(self) -> uc.Chrome:
        """Initialize and configure a new Chrome WebDriver instance."""
        if self.driver is not None:
            self._teardown_driver()

        options = uc.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-notifications')
        
        self.driver = uc.Chrome(options=options)
        self.driver.maximize_window()
        return self.driver

    def _teardown_driver(self) -> None:
        """Safely close and cleanup the WebDriver instance."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None

    def __del__(self):
        """Cleanup method to ensure resources are properly closed"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()