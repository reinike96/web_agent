import time
import os
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)

class BrowserController:
    """
    Manages the Selenium WebDriver for Edge, including initialization,
    navigation, and interaction with web pages.
    """
    def __init__(self):
        """Initializes the Edge WebDriver."""
        try:
            # Try to use webdriver-manager first
            print("Attempting to initialize WebDriver with webdriver-manager...")
            service = EdgeService(EdgeChromiumDriverManager().install())
            self.driver = webdriver.Edge(service=service)
            print("WebDriver initialized successfully with webdriver-manager.")
            self.handled_popups = set()
        except Exception as e:
            print(f"webdriver-manager failed: {e}")
            print("Falling back to local msedgedriver.exe...")
            try:
                # Fallback to the local driver
                driver_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'msedgedriver.exe'))
                if not os.path.exists(driver_path):
                    print(f"Local driver not found at: {driver_path}")
                    self.driver = None
                    return

                service = EdgeService(executable_path=driver_path)
                self.driver = webdriver.Edge(service=service)
                print("WebDriver initialized successfully with local driver.")
                self.handled_popups = set()
            except Exception as e2:
                print(f"Error initializing WebDriver with local driver: {e2}")
                self.driver = None

    def open_url(self, url: str):
        """Navigates to a specific URL."""
        if self.driver:
            self.driver.get(url)
            time.sleep(2) # Wait for the page to load

    def get(self, url: str):
        """Alias for open_url to be more compatible with standard Selenium syntax."""
        self.open_url(url)

    def get_page_source(self) -> str:
        """Returns the HTML source of the current page."""
        if self.driver:
            return self.driver.page_source
        return ""

    def safe_find_element(self, by: By, value: str, timeout: int = 10) -> WebElement | None:
        """Safely finds an element with explicit wait."""
        if not self.driver:
            return None
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Element not found ({by}={value}): {e}")
            return None

    def safe_click(self, by: By, value: str, timeout: int = 10, retries: int = 3) -> bool:
        """
        Safely clicks an element with retries, handling stale elements and interceptions.
        """
        for i in range(retries):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((by, value))
                )
                element.click()
                return True
            except StaleElementReferenceException:
                print("Stale element reference, retrying click...")
                time.sleep(1) # Wait a moment before retrying
                continue # Retry finding the element
            except ElementClickInterceptedException:
                print("Element click intercepted, trying JavaScript click...")
                try:
                    # Re-find the element before JS click
                    element = self.driver.find_element(by, value)
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception as e_js:
                    print(f"JavaScript click also failed: {e_js}")
            except Exception as e:
                print(f"An unexpected error occurred during click: {e}")

            if i < retries - 1:
                time.sleep(1)
        
        return False

    def safe_send_keys(self, by: By, value: str, text: str, timeout: int = 10, retries: int = 3) -> bool:
        """
        Safely sends keys to an element, handling stale elements.
        """
        for i in range(retries):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((by, value))
                )
                element.clear()
                element.send_keys(text)
                element.send_keys(Keys.ENTER)
                return True
            except StaleElementReferenceException:
                print("Stale element reference, retrying send_keys...")
                time.sleep(1) # Wait and retry
            except Exception as e:
                print(f"Error sending keys: {e}")
                return False
        return False

    def handle_popup(self, selectors: list[tuple[By, str]], timeout: int = 5) -> bool:
        """Attempts to handle popups using multiple selector strategies."""
        popup_key = str(selectors)  # Create a unique key for this set of selectors
        if popup_key in self.handled_popups:
            return False  # Skip if already handled

        for by, value in selectors:
            try:
                if self.safe_click(by, value, timeout=timeout):
                    self.handled_popups.add(popup_key)  # Mark as handled
                    time.sleep(1)  # Wait for popup to disappear
                    return True
            except Exception:
                continue
        return False

    def find_element(self, by: By, value: str) -> WebElement | None:
        """Finds a single web element with improved error handling."""
        return self.safe_find_element(by, value)

    def close_browser(self):
        """Closes the browser."""
        if self.driver:
            self.driver.quit()

    def execute_script(self, script: str) -> any:
        """Executes JavaScript in the browser and returns the result."""
        if self.driver:
            try:
                return self.driver.execute_script(script)
            except Exception as e:
                print(f"Error executing JavaScript: {e}")
                return None
        return None

    def execute_js_download(self, selector: str, filename: str, content_type: str = 'text/plain') -> bool:
        """
        Executes JavaScript to extract content and trigger download.
        Args:
            selector: CSS selector for the element containing content
            filename: Name of the file to save
            content_type: MIME type for the content (default: text/plain)
        """
        js_code = f"""
        const element = document.querySelector('{selector}');
        if (!element) return false;
        const text = element.textContent;
        const blob = new Blob([text], {{type: '{content_type}'}});
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = '{filename}';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
        return true;
        """
        return self.execute_script(js_code)

    def get_page_title(self) -> str:
        """Returns the current page title."""
        if self.driver:
            return self.driver.title
        return ""

    def get_title(self) -> str:
        """Alias for get_page_title."""
        return self.get_page_title()

    def get_current_url(self) -> str:
        """Returns the current page URL."""
        if self.driver:
            return self.driver.current_url
        return ""

    def wait_for_download(self, filename: str, timeout: int = 30) -> bool:
        """
        Waits for a file to appear in the default download directory.
        Args:
            filename: Name of the file to wait for
            timeout: Maximum time to wait in seconds
        Returns:
            True if file appears, False otherwise
        """
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        file_path = os.path.join(download_dir, filename)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if os.path.exists(file_path):
                # Check if file is complete (not still downloading)
                try:
                    with open(file_path, 'rb') as f:
                        f.seek(-1, 2)
                        return True
                except:
                    pass
            time.sleep(1)
        return False

    def check_step_completion(self, expected_title_keywords: list[str] = None,
                            expected_url_keywords: list[str] = None) -> dict:
        """
        Checks if the current step has been completed by verifying page title and URL.
        
        Args:
            expected_title_keywords: List of keywords expected in the page title
            expected_url_keywords: List of keywords expected in the URL
            
        Returns:
            Dictionary with completion status and details
        """
        result = {
            "completed": False,
            "page_title": self.get_page_title(),
            "current_url": self.get_current_url(),
            "title_match": False,
            "url_match": False,
            "details": []
        }
        
        if expected_title_keywords:
            title = result["page_title"].lower()
            result["title_match"] = any(keyword.lower() in title
                                      for keyword in expected_title_keywords)
            
        if expected_url_keywords:
            url = result["current_url"].lower()
            result["url_match"] = any(keyword.lower() in url
                                    for keyword in expected_url_keywords)
        
        # Step is considered completed if we have the expected title or URL
        result["completed"] = result["title_match"] or result["url_match"]
        
        return result

    def click_element(self, selector: str) -> bool:
        """Clicks an element using a CSS selector."""
        return self.safe_click(By.CSS_SELECTOR, selector)

    def enter_text(self, selector: str, text: str) -> bool:
        """Enters text into an element using a CSS selector."""
        return self.safe_send_keys(By.CSS_SELECTOR, selector, text)

    def navigate_to(self, url: str):
        """Navigates to a specific URL."""
        self.open_url(url)


if __name__ == '__main__':
    # Example usage:
    controller = BrowserController()
    if controller.driver:
        controller.open_url("https://www.bing.com/")
        print("Page Title:", controller.driver.title)
        print("Page URL:", controller.driver.current_url)
        controller.close_browser()
    else:
        print("WebDriver not initialized.")
