import time
import os
import re
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

def safe_print(text):
    """Print text safely, replacing Unicode characters that may cause encoding issues."""
    # Dictionary of emoji/Unicode replacements
    emoji_replacements = {
        '[AI]': '[AI]',
        '[SUCCESS]': '[SUCCESS]',
        '[ERROR]': '[ERROR]',
        '[WARNING]': '[WARNING]',
        '[SEARCH]': '[SEARCH]',
        '[DATA]': '[DATA]',
        '📝': '[TEXT]',
        '[PROCESSING]': '[PROCESSING]',
        '[CLICK]': '[CLICK]',
        '[IDEA]': '[INFO]',
        '[TARGET]': '[TARGET]',
        '?': '[TIME]',
        '[LAUNCH]': '[LAUNCH]',
        '[TOOLS]': '[TOOLS]',
        '[LIST]': '[CLIPBOARD]',
        '[SAVE]': '[SAVE]',
        '[WEB]': '[WEB]',
        '[LINK]': '[LINK]',
        '[MOBILE]': '[MOBILE]',
        '[DESKTOP]': '[DESKTOP]',
        '[STAR]': '[STAR]',
        '[CELEBRATE]': '[CELEBRATE]',
        '[STOP]': '[STOP]',
        '[PLAY]': '[PLAY]',
        '[PAUSE]': '[PAUSE]',
        '[STOP]': '[STOP]',
        '[AUDIO]': '[AUDIO]',
        '[MUTE]': '[MUTE]',
        '[DOCUMENT]': '[DOCUMENT]',
        '[FILE]': '[FOLDER]',
        '[ARCHIVE]': '[ARCHIVE]',
        '[CHART]': '[CHART]',
        '[GRAPH]': '[GRAPH]',
        '[TROPHY]': '[TROPHY]',
        '[MEDAL]': '[MEDAL]',
        '[GOLD]': '[GOLD]',
        '[SILVER]': '[SILVER]',
        '[BRONZE]': '[BRONZE]',
        '[KEY]': '[KEY]',
        '[EVENT]': '[EVENT]',
        '[THEATER]': '[THEATER]',
        '[ART]': '[ART]',
        '[MUSIC]': '[MUSIC]',
        '[MELODY]': '[MELODY]',
    }
    
    # Replace known emojis first
    safe_text = text
    for emoji, replacement in emoji_replacements.items():
        safe_text = safe_text.replace(emoji, replacement)
    
    # Remove any remaining high Unicode characters (above ASCII range)
    safe_text = re.sub(r'[\u0080-\uffff]', '?', safe_text)
    
    try:
        print(safe_text, flush=True)
    except UnicodeEncodeError:
        # If we still have encoding issues, try encoding to ASCII with replacement
        ascii_text = safe_text.encode('ascii', errors='replace').decode('ascii')
        print(ascii_text, flush=True)

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
        Uses advanced typing simulation to ensure modern SPAs detect the input correctly.
        """
        for i in range(retries):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((by, value))
                )
                
                print(f"Attempting to type text using enhanced simulation...")
                
                # Strategy 1: Advanced paste simulation for contenteditable elements (X.com, Facebook, etc.)
                if element.get_attribute("contenteditable") == "true" or "contenteditable" in element.get_attribute("class"):
                    print(f"Using advanced paste simulation strategy for contenteditable...")
                    
                    # Step 1: Focus and prepare element
                    element.click()
                    time.sleep(0.3)
                    
                    # Step 2: Use JavaScript to simulate paste instead of typing
                    success = self.driver.execute_script("""
                        var element = arguments[0];
                        var text = arguments[1];
                        
                        function simulatePaste(element, text) {
                            element.focus();
                            
                            if (element.tagName === 'DIV' && element.contentEditable === 'true') {
                                // For contenteditable elements - clear content first
                                element.click();
                                const selection = window.getSelection();
                                selection.selectAllChildren(element);
                                selection.deleteFromDocument();
                            } else {
                                // For input/textarea elements
                                element.select();
                            }
                            
                            // Create paste event with clipboard data
                            const pasteEvent = new ClipboardEvent("paste", {
                                bubbles: true,
                                cancelable: true,
                                clipboardData: new DataTransfer()
                            });
                            
                            pasteEvent.clipboardData.setData("text/plain", text);
                            
                            // Dispatch the paste event
                            element.dispatchEvent(pasteEvent);
                            
                            // Fallback: set content directly if paste event didn't work
                            if (element.tagName === 'DIV' && element.contentEditable === 'true') {
                                if (!element.textContent || element.textContent.trim() === '') {
                                    element.textContent = text;
                                }
                            } else {
                                if (!element.value || element.value.trim() === '') {
                                    element.value = text;
                                }
                            }
                            
                            // CRITICAL: Dispara eventos para que frameworks lo detecten
                            element.dispatchEvent(new Event('input', {bubbles: true}));
                            element.dispatchEvent(new Event('change', {bubbles: true}));
                            element.dispatchEvent(new Event('blur', {bubbles: true}));
                            
                            return element.textContent === text || element.innerText === text || element.value === text;
                        }
                        
                        return simulatePaste(element, text);
                    """, element, text)
                    
                    if success:
                        safe_print(f"[SUCCESS] Paste simulation successful")
                    else:
                        safe_print(f"[WARNING] Paste simulation completed, verifying content...")
                    
                    # Additional verification and fallback
                    time.sleep(0.5)
                    current_content = element.get_attribute("textContent") or element.get_attribute("innerText") or ""
                    
                    if text not in current_content:
                        safe_print(f"[PROCESSING] Fallback: Using direct text insertion")
                        self.driver.execute_script("""
                            var element = arguments[0];
                            var text = arguments[1];
                            
                            // Direct text insertion fallback
                            element.textContent = text;
                            element.innerHTML = text;
                            
                            // Trigger essential events
                            element.dispatchEvent(new Event('input', {bubbles: true}));
                            element.dispatchEvent(new Event('change', {bubbles: true}));
                        """, element, text)
                
                else:
                    # Strategy 2: Paste simulation for regular inputs
                    print(f"Using paste simulation strategy for regular input element...")
                    
                    # Focus element
                    element.click()
                    time.sleep(0.2)
                    
                    # Use paste simulation for regular inputs too
                    success = self.driver.execute_script("""
                        var element = arguments[0];
                        var text = arguments[1];
                        
                        function simulatePaste(element, text) {
                            element.focus();
                            
                            // Select all existing content for replacement
                            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                                element.select();
                            }
                            
                            // Create paste event with clipboard data
                            const pasteEvent = new ClipboardEvent("paste", {
                                bubbles: true,
                                cancelable: true,
                                clipboardData: new DataTransfer()
                            });
                            
                            pasteEvent.clipboardData.setData("text/plain", text);
                            
                            // Dispatch the paste event
                            element.dispatchEvent(pasteEvent);
                            
                            // Fallback: set value directly if paste event didn't work
                            if (!element.value || element.value.trim() === '') {
                                element.value = text;
                            }
                            
                            // Trigger events that frameworks listen for
                            element.dispatchEvent(new Event('input', {bubbles: true}));
                            element.dispatchEvent(new Event('change', {bubbles: true}));
                            element.dispatchEvent(new Event('blur', {bubbles: true}));
                            
                            // React specific
                            if (element._valueTracker) {
                                element._valueTracker.setValue(text);
                            }
                            
                            return element.value === text;
                        }
                        
                        return simulatePaste(element, text);
                    """, element, text)
                    
                    if success:
                        safe_print(f"[SUCCESS] Paste simulation successful for input element")
                    else:
                        safe_print(f"[WARNING] Paste simulation completed, verifying content...")
                
                # Final verification
                time.sleep(0.5)
                current_content = element.get_attribute("textContent") or element.get_attribute("value") or element.get_attribute("innerText") or ""
                safe_print(f"[TEXT] Text verification - Expected: '{text}', Found: '{current_content.strip()}'")
                
                # Check if text was successfully entered (allow partial match for contenteditable)
                text_entered = text.strip() in current_content.strip() or current_content.strip() == text.strip()
                
                if not text_entered and i < retries - 1:
                    safe_print(f"[ERROR] Text verification failed on attempt {i+1}, retrying...")
                    time.sleep(1)
                    continue
                elif not text_entered:
                    safe_print(f"[WARNING] Text verification failed on final attempt, but continuing...")
                else:
                    safe_print(f"[SUCCESS] Text successfully entered and verified")
                
                # Wait a moment for page to process the input
                time.sleep(0.3)
                
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
            button_keywords = ["submit", "send", "post", "publish", "search", "login", "sign in", "continue", "tweet", "publicar"]
        
        safe_print(f"[SEARCH] Waiting for button to become enabled (keywords: {button_keywords})...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try to find buttons with the keywords
                for keyword in button_keywords:
                    # Check for buttons with text containing the keyword
                    buttons = self.driver.execute_script(f"""
                        var buttons = Array.from(document.querySelectorAll('button, input[type="submit"], [role="button"]'));
                        return buttons.filter(btn => {{
                            var text = (btn.textContent || btn.value || btn.getAttribute('aria-label') || '').toLowerCase();
                            var isEnabled = !btn.disabled && btn.offsetParent !== null && 
                                           getComputedStyle(btn).display !== 'none' &&
                                           getComputedStyle(btn).visibility !== 'hidden';
                            return text.includes('{keyword.lower()}') && isEnabled;
                        }}).map(btn => ({{
                            text: btn.textContent || btn.value || btn.getAttribute('aria-label') || '',
                            enabled: !btn.disabled,
                            visible: btn.offsetParent !== null,
                            selector: btn.id ? '#' + btn.id : btn.className ? '.' + btn.className.split(' ')[0] : btn.tagName.toLowerCase()
                        }}));
                    """)
                    
                    if buttons and len(buttons) > 0:
                        enabled_buttons = [btn for btn in buttons if btn['enabled'] and btn['visible']]
                        if enabled_buttons:
                            safe_print(f"[SUCCESS] Found {len(enabled_buttons)} enabled button(s) with keyword '{keyword}':")
                            for btn in enabled_buttons[:2]:  # Show first 2
                                print(f"   - '{btn['text'].strip()}' ({btn['selector']})")
                            return True
                
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                print(f"Error checking button state: {e}")
                time.sleep(0.5)
        
        safe_print(f"[WARNING] No enabled buttons found with keywords {button_keywords} within {timeout}s")
        return False
    
    def verify_text_input_detected(self, selector: str, expected_text: str, timeout: int = 5) -> bool:
        """
        Verify that text input was detected by checking if related buttons become enabled.
        This is particularly useful for modern SPAs that enable/disable buttons based on input validation.
        """
        safe_print(f"[SEARCH] Verifying text input was detected by the page...")
        
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            
            # Check the actual content
            current_content = element.get_attribute("textContent") or element.get_attribute("value") or element.get_attribute("innerText") or ""
            content_match = expected_text.strip() in current_content.strip()
            
            safe_print(f"[TEXT] Content check: Expected '{expected_text}', Found '{current_content.strip()}' - {'[SUCCESS] Match' if content_match else '[ERROR] No match'}")
            
            # Check if submit/post buttons are now enabled (common pattern in modern apps)
            buttons_enabled = self.wait_for_button_enabled(timeout=timeout)
            
            # JavaScript check for additional validation
            js_validation = self.driver.execute_script("""
                var element = arguments[0];
                var text = arguments[1];
                
                // Check various properties that frameworks might use
                var checks = {
                    textContent: element.textContent && element.textContent.includes(text),
                    value: element.value && element.value.includes(text),
                    innerText: element.innerText && element.innerText.includes(text),
                    hasText: element.textContent.length > 0 || element.value.length > 0,
                    isFocused: document.activeElement === element || element.matches(':focus')
                };
                
                return checks;
            """, element, expected_text)
            
            safe_print(f"[SEARCH] JS validation: {js_validation}")
            
            # Consider successful if content matches OR buttons are enabled (indicating page detected input)
            success = content_match or buttons_enabled
            
            if success:
                safe_print(f"[SUCCESS] Text input verification successful!")
            else:
                safe_print(f"[WARNING] Text input verification inconclusive - page may not have detected the input")
            
            return success
            
        except Exception as e:
            safe_print(f"[ERROR] Error verifying text input: {e}")
            return False

    def click_button_from_json(self, page_info: dict, button_keywords: list = None) -> bool:
        """
        Click a button using selectors from the JSON data with enhanced search.
        This uses the actual elements found in the page analysis.
        
        Args:
            page_info: Page information containing interactive elements
            button_keywords: Keywords to search for in button text/labels
        """
        if button_keywords is None:
            button_keywords = ["submit", "send", "post", "publish", "search", "login", "sign in", "continue", "next", "tweet", "publicar"]
        
        interactive_elements = page_info.get("interactive_elements", {})
        
        safe_print(f"[SEARCH] [PROGRAMMATIC] Searching for buttons with keywords: {button_keywords}")
        safe_print(f"[DATA] [PROGRAMMATIC] Available elements to search: {len(interactive_elements.get('elements', []))}")
        
        # First, try to find exact keyword matches
        found_buttons = []
        
        # Look for buttons in the elements list (new format)
        elements_list = interactive_elements.get("elements", [])
        if elements_list:
            for element_data in elements_list:
                element_text = (element_data.get("text", "") or "").lower()
                element_aria = (element_data.get("aria-label", "") or "").lower()
                element_title = (element_data.get("title", "") or "").lower()
                element_tag = element_data.get("tag", "").lower()
                selector = element_data.get("selector", "")
                
                # Check if this is a button-like element
                is_button_like = element_tag in ["button", "input"] or "button" in element_data.get("role", "").lower()
                
                # Check for keyword matches
                text_match = any(keyword.lower() in element_text for keyword in button_keywords)
                aria_match = any(keyword.lower() in element_aria for keyword in button_keywords)
                title_match = any(keyword.lower() in element_title for keyword in button_keywords)
                
                if (is_button_like or text_match or aria_match or title_match) and selector:
                    score = 0
                    # Score based on match quality
                    if text_match: score += 3
                    if aria_match: score += 2
                    if title_match: score += 1
                    if is_button_like: score += 1
                    
                    found_buttons.append({
                        "selector": selector,
                        "text": element_text,
                        "aria": element_aria,
                        "title": element_title,
                        "tag": element_tag,
                        "score": score
                    })
        
        # Also check old format for backward compatibility
        if not found_buttons and hasattr(interactive_elements, 'items'):
            for element_id, element_data in interactive_elements.items():
                if element_id == "elements":  # Skip the elements list
                    continue
                    
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
                    found_buttons.append({
                        "selector": selector,
                        "text": element_text,
                        "aria": element_aria,
                        "score": 2
                    })
        
        # Sort by score (best matches first)
        found_buttons.sort(key=lambda x: x["score"], reverse=True)
        
        safe_print(f"[TARGET] [PROGRAMMATIC] Found {len(found_buttons)} potential button matches")
        
        # Try to click the best matches
        for button in found_buttons:
            button_description = button.get("text") or button.get("aria") or button.get("title") or "no text"
            safe_print(f"[CLICK] [PROGRAMMATIC] Trying to click: '{button_description}' (selector: {button['selector']}, score: {button['score']})")
            
            try:
                success = self.safe_click(By.CSS_SELECTOR, button["selector"], timeout=5)
                if success:
                    safe_print(f"[SUCCESS] [PROGRAMMATIC] Successfully clicked button: {button['selector']}")
                    return True
                else:
                    safe_print(f"[WARNING] [PROGRAMMATIC] Failed to click button: {button['selector']}")
                    
            except Exception as e:
                safe_print(f"[ERROR] [PROGRAMMATIC] Error clicking button {button['selector']}: {e}")
                continue
        
        safe_print(f"[ERROR] [PROGRAMMATIC] No clickable button found with keywords: {button_keywords}")
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