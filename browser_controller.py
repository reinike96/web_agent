import time
import os
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
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
from selenium.webdriver.edge.options import Options as EdgeOptions

class BrowserController:
    def __init__(self):
        try:
            options = EdgeOptions()
            
            driver_path = r"C:\Users\ALEXR\OneDrive\Desktop\Browser\web_agent\msedgedriver.exe"
            print(f"Using local driver at: {driver_path}")

            if not os.path.exists(driver_path):
                print(f"ERROR! Driver not found at specified path: {driver_path}")
                self.driver = None
                return

            service = EdgeService(executable_path=driver_path)
            
            print("Initializing new Edge browser session...")
            self.driver = webdriver.Edge(service=service, options=options)
            
            # Verify the browser is responsive
            if not self.is_browser_responsive():
                raise Exception("Browser is not responding after initialization.")

            print("WebDriver initialized successfully with user profile.")
            self.handled_popups = set()

        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            print("\nPOSSIBLE SOLUTIONS:")
            print("1. Ensure your msedgedriver.exe version matches your Edge browser version.")
            print("2. Check if your antivirus or firewall is blocking msedgedriver.exe.")
            self.driver = None

    def is_browser_responsive(self, timeout=10):
        if not self.driver:
            return False
        try:
            # A lightweight command to check responsiveness
            self.driver.execute(webdriver.remote.command.Command.GET_TITLE)
            return True
        except Exception:
            return False

    def open_url(self, url: str):
        if self.driver:
            self.driver.get(url)
            time.sleep(2)

    def get(self, url: str):
        self.open_url(url)

    def get_page_source(self) -> str:
        if self.driver:
            return self.driver.page_source
        return ""

    def safe_find_element(self, by: By, value: str, timeout: int = 10) -> WebElement | None:
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

    def safe_click(self, by: By, value: str, timeout: int = 10, retries: int = 1) -> bool:
        for i in range(retries):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((by, value))
                )
                element.click()
                return True
            except StaleElementReferenceException:
                print("Stale element reference, retrying click...")
                time.sleep(1)
                continue
            except ElementClickInterceptedException:
                print("Element click intercepted, trying JavaScript click...")
                try:
                    element = self.driver.find_element(by, value)
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception as e_js:
                    print(f"JavaScript click also failed: {e_js}")
            except TimeoutException:
                print(f"Timeout waiting for element to be clickable: {value}")
            except Exception as e:
                print(f"An unexpected error occurred during click: {e}")

            if i < retries - 1:
                time.sleep(1)
        
        return False

    def safe_send_keys(self, by: By, value: str, text: str, timeout: int = 10, retries: int = 1, press_enter: bool = True) -> bool:
        for i in range(retries):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((by, value))
                )
                element.clear()
                element.send_keys(text)
                if press_enter:
                    element.send_keys(Keys.ENTER)
                return True
            except StaleElementReferenceException:
                print("Stale element reference, retrying send_keys...")
                time.sleep(1)
            except Exception as e:
                print(f"Error sending keys: {e}")
                return False
        return False

    def handle_popup(self, selectors: list[tuple[By, str]], timeout: int = 2) -> bool:
        popup_key = str(selectors)
        if popup_key in self.handled_popups:
            return False

        for by, value in selectors:
            try:
                if self.safe_click(by, value, timeout=timeout):
                    self.handled_popups.add(popup_key)
                    time.sleep(1)
                    return True
            except Exception:
                continue
        return False

    def find_element(self, by: By, value: str) -> WebElement | None:
        return self.safe_find_element(by, value)

    def close_browser(self):
        if self.driver:
            self.driver.quit()

    def execute_script(self, script: str) -> any:
        if self.driver:
            try:
                return self.driver.execute_script(script)
            except Exception as e:
                print(f"Error executing JavaScript: {e}")
                return None
        return None

    def execute_js_download(self, selector: str, filename: str, content_type: str = 'text/plain') -> bool:
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
        if self.driver:
            return self.driver.title
        return ""

    def get_title(self) -> str:
        return self.get_page_title()

    def get_current_url(self) -> str:
        if self.driver:
            return self.driver.current_url
        return ""

    def wait_for_download(self, filename: str, timeout: int = 30) -> bool:
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        file_path = os.path.join(download_dir, filename)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if os.path.exists(file_path):
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
        
        result["completed"] = result["title_match"] or result["url_match"]
        
        return result

    def click_element(self, selector: str) -> bool:
        return self.safe_click(By.CSS_SELECTOR, selector)

    def enter_text(self, selector: str, text: str, press_enter: bool = False) -> bool:
        return self.safe_send_keys_rich_text(By.CSS_SELECTOR, selector, text, press_enter=press_enter)

    def enter_text_without_enter(self, selector: str, text: str) -> bool:
        """Enters text without pressing Enter - useful for composers, forms, etc."""
        return self.safe_send_keys_rich_text(By.CSS_SELECTOR, selector, text, press_enter=False)

    def safe_send_keys_rich_text(self, by: By, value: str, text: str, timeout: int = 10, retries: int = 1, press_enter: bool = True) -> bool:
        """
        Enhanced text entry method specifically for rich text editors like X.com.
        Uses multiple strategies including simulated typing to ensure X.com detects the input.
        """
        for i in range(retries):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((by, value))
                )
                
                # Strategy 1: For contenteditable elements (X.com), simulate real typing
                if element.get_attribute("contenteditable") == "true":
                    print(f"Using rich text strategy for contenteditable element...")
                    
                    # Step 1: Clear existing content
                    element.click()  # Focus the element
                    time.sleep(0.2)
                    
                    # Select all and delete
                    element.send_keys(Keys.CONTROL + "a")
                    time.sleep(0.1)
                    element.send_keys(Keys.DELETE)
                    time.sleep(0.2)
                    
                    # Step 2: Type character by character to simulate real typing
                    for char in text:
                        element.send_keys(char)
                        time.sleep(0.05)  # Small delay between characters
                    
                    # Step 3: Trigger additional events that X.com might be listening for
                    self.driver.execute_script("""
                        var element = arguments[0];
                        var text = arguments[1];
                        
                        // Ensure the text is set
                        element.textContent = text;
                        
                        // Trigger all possible events that X.com might be listening for
                        var events = ['input', 'change', 'keyup', 'keydown', 'textInput', 'paste'];
                        events.forEach(function(eventType) {
                            var event = new Event(eventType, { 
                                bubbles: true, 
                                cancelable: true,
                                composed: true 
                            });
                            element.dispatchEvent(event);
                        });
                        
                        // Special handling for React/modern frameworks
                        if (element._valueTracker) {
                            element._valueTracker.setValue('');
                        }
                        
                        // Trigger focus events
                        element.focus();
                        var focusEvent = new Event('focus', { bubbles: true });
                        element.dispatchEvent(focusEvent);
                        
                    """, element, text)
                    
                    time.sleep(0.3)  # Give X.com time to process
                    
                else:
                    # Strategy 2: Traditional method for regular inputs
                    print(f"Using traditional strategy for input element...")
                    element.clear()
                    element.send_keys(text)
                
                # Verify the text was entered
                current_content = element.get_attribute("textContent") or element.get_attribute("value") or ""
                print(f"Text verification - Expected: '{text}', Found: '{current_content}'")
                
                if text not in current_content:
                    print(f"[WARNING] Text verification failed on attempt {i+1}")
                    if i < retries - 1:
                        continue
                
                if press_enter:
                    element.send_keys(Keys.ENTER)
                
                return True
                
            except StaleElementReferenceException:
                print(f"Stale element reference on attempt {i+1}, retrying...")
                time.sleep(1)
            except Exception as e:
                print(f"Error sending keys on attempt {i+1}: {e}")
                if i == retries - 1:  # Last attempt
                    return False
                time.sleep(1)
        
        return False

    def wait_for_button_enabled(self, button_keywords: list = None, timeout: int = 10) -> bool:
        """
        Wait for a button to become enabled after text entry.
        This helps verify that the page detected the text input correctly.
        
        Args:
            button_keywords: List of keywords to search for in button text/labels
            timeout: Maximum time to wait
        """
        if button_keywords is None:
            button_keywords = ["submit", "send", "post", "publish", "search", "login", "sign in", "continue"]
        
        # Generic button selectors
        button_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:not([disabled])',
            '[role="button"]:not([aria-disabled="true"])'
        ]
        
        for selector in button_selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for button in buttons:
                    try:
                        button_text = (button.text or "").lower()
                        aria_label = (button.get_attribute("aria-label") or "").lower()
                        
                        # Check if button matches our keywords
                        text_matches = any(keyword.lower() in button_text for keyword in button_keywords)
                        label_matches = any(keyword.lower() in aria_label for keyword in button_keywords)
                        
                        if text_matches or label_matches:
                            is_enabled = button.is_enabled() and not button.get_attribute("disabled")
                            aria_disabled = button.get_attribute("aria-disabled")
                            
                            if is_enabled and aria_disabled != "true":
                                print(f"[OK] Found enabled button: '{button_text or aria_label}'")
                                return True
                                
                    except Exception:
                        continue
                        
            except Exception as e:
                print(f"Could not check buttons with selector {selector}: {e}")
                continue
        
        print(f"[WARNING] No enabled button found with keywords: {button_keywords}")
        return False

    def click_button_from_json(self, page_info: dict, button_keywords: list = None) -> bool:
        """
        Click a button using selectors from the JSON data.
        This uses the actual elements found in the page analysis.
        
        Args:
            page_info: Page information containing interactive elements
            button_keywords: Keywords to search for in button text/labels
        """
        if button_keywords is None:
            button_keywords = ["submit", "send", "post", "publish", "search", "login", "sign in", "continue", "next"]
        
        interactive_elements = page_info.get("interactive_elements", {})
        
        # Look for buttons matching keywords in the JSON data
        for element_id, element_data in interactive_elements.items():
            element_text = (element_data.get("text", "") or "").lower()
            element_aria = (element_data.get("aria_label", "") or "").lower()
            element_type = element_data.get("type", "")
            selector = element_data.get("selector", "")
            
            # Check if this looks like a relevant button
            is_target_button = (
                element_type == "button" and
                (any(keyword.lower() in element_text for keyword in button_keywords) or
                 any(keyword.lower() in element_aria for keyword in button_keywords))
            )
            
            if is_target_button and selector:
                print(f"Found target button in JSON: '{element_text or element_aria}' with selector: {selector}")
                
                try:
                    success = self.safe_click(By.CSS_SELECTOR, selector, timeout=5)
                    if success:
                        print(f"[OK] Successfully clicked button: {selector}")
                        return True
                    else:
                        print(f"[WARNING] Failed to click button: {selector}")
                        
                except Exception as e:
                    print(f"Error clicking button {selector}: {e}")
                    continue
        
        print(f"[ERROR] No button found in JSON data with keywords: {button_keywords}")
        return False

    def navigate_to(self, url: str):
        self.open_url(url)

    def handle_initial_page_load(self, timeout: int = 2):
        """
        Handles the initial page load, dealing with cookie pop-ups and other dynamic elements.
        """
        # Common selectors for cookie consent buttons
        consent_selectors = [
            (By.XPATH, "//*[contains(text(), 'Accept all')]"),
            (By.XPATH, "//*[contains(text(), 'Accept')]"),
            (By.XPATH, "//*[contains(text(), 'I agree')]"),
            (By.ID, "L2AGLb"),
            (By.CSS_SELECTOR, ".fc-cta-consent"),
            (By.XPATH, "//button[normalize-space()='Aceptar todo']"),
            (By.XPATH, "//button[normalize-space()='Rechazar todo']"),
        ]

        for by, value in consent_selectors:
            try:
                if self.safe_click(by, value, timeout=timeout):
                    print(f"Clicked consent button: {value}")
                    time.sleep(2)  # Wait for the banner to disappear
                    return # Exit after the first successful click
            except Exception as e:
                # This is to avoid spamming the log if elements are not found
                pass


if __name__ == '__main__':
    controller = BrowserController()
    if controller.driver:
        controller.open_url("https://www.bing.com/")
        print("Page Title:", controller.driver.title)
        print("Page URL:", controller.driver.current_url)
        controller.close_browser()
    else:
        print("WebDriver not initialized.")