from typing import Dict

class PageAnalyzer:
    """
    Analyzes web pages by injecting JavaScript to extract interactive elements and page structure.
    """
    
    def __init__(self, browser_controller, llm_controller=None):
        self.browser = browser_controller
        self.llm_controller = llm_controller
        
    def get_interactive_elements(self) -> Dict:
        """
        Injects extractJsonInteractive.js to get clickable and input elements with their selectors.
        """
        try:
            # Read the JavaScript file
            js_file_path = r"c:\Users\ALEXR\OneDrive\Desktop\Browser\web_agent\extractJsonInteractive_simple.js"
            with open(js_file_path, 'r', encoding='utf-8') as file:
                js_code = file.read()
            
            # Execute the script and get the result
            result = self.browser.execute_script(js_code)
            
            if result:
                return result
            else:
                # Fallback minimal structure
                return {
                    "url": self.browser.get_current_url(),
                    "title": self.browser.get_page_title(),
                    "elements": []
                }
                
        except FileNotFoundError as e:
            print(f"JavaScript file not found: {e}")
            return {
                "url": self.browser.get_current_url(),
                "title": self.browser.get_page_title(),
                "elements": []
            }
        except Exception as e:
            print(f"Error extracting interactive elements: {e}")
            return {
                "url": self.browser.get_current_url(),
                "title": self.browser.get_page_title(),
                "elements": []
            }
    
    def get_page_structure(self) -> Dict:
        """
        Injects extractJsonStructure.js to get page headings and structure information.
        """
        try:
            # Read the JavaScript file
            js_file_path = r"c:\Users\ALEXR\OneDrive\Desktop\Browser\web_agent\extractJsonStructure.js"
            with open(js_file_path, 'r', encoding='utf-8') as file:
                js_code = file.read()
            
            # Execute the script and get the result
            result = self.browser.execute_script(js_code)
            
            if result:
                return result
            else:
                # Fallback minimal structure
                return {
                    "url": self.browser.get_current_url(),
                    "title": self.browser.get_page_title(),
                    "headings": [],
                    "repeatedBlocks": []
                }
                
        except Exception as e:
            print(f"Error extracting page structure: {e}")
            return {
                "url": self.browser.get_current_url(),
                "title": self.browser.get_page_title(),
                "headings": [],
                "repeatedBlocks": []
            }
    
    def get_comprehensive_page_info(self) -> Dict:
        """
        Gets both interactive elements and page structure in one call.
        """
        interactive = self.get_interactive_elements()
        structure = self.get_page_structure()
        
        return {
            "interactive_elements": interactive,
            "page_structure": structure,
            "current_url": self.browser.get_current_url(),
            "page_title": self.browser.get_page_title()
        }
    
    def detect_login_or_captcha(self, page_info: Dict) -> Dict:
        """
        Analyzes page info to detect if login or CAPTCHA intervention is needed.
        Uses LLM-based analysis if available, falls back to simple rule-based detection.
        """
        elements = page_info.get("interactive_elements", {}).get("elements", [])
        
        # If we have an LLM controller, use the smart analysis
        if self.llm_controller:
            try:
                result = self.llm_controller.analyze_page_for_intervention(elements)
                return {
                    "requires_intervention": result.get("requires_intervention", False),
                    "type": result.get("type", "none"),
                    "message": result.get("reason", "LLM analysis completed"),
                    "source": "llm_analysis"
                }
            except Exception as e:
                print(f"LLM analysis failed, falling back to rule-based: {e}")
        
        # Fallback to simple rule-based detection
        login_buttons = []
        signup_buttons = []
        captcha_indicators = []
        functional_elements = []
        
        for element in elements:
            data_testid = (element.get("data-testid", "") or "").lower()
            text = (element.get("text", "") or "").lower()
            element_type = element.get("type", "")
            
            # Check for specific TestID patterns (confirmed working)
            if "loginbutton" in data_testid:
                login_buttons.append(element)
            elif "signupbutton" in data_testid:
                signup_buttons.append(element)
            
            # Check for CAPTCHA indicators
            if any(indicator in text for indicator in ["captcha", "verify you're human", "i'm not a robot"]):
                captcha_indicators.append(element)
            
            # Check for functional elements that indicate the site is usable
            if (element_type in ["input", "button", "link"] and 
                any(keyword in text for keyword in ["search", "article", "read", "browse", "explore", "menu"])):
                functional_elements.append(element)
        
        # Decision logic - be more conservative about requiring intervention
        if captcha_indicators:
            return {
                "requires_intervention": True,
                "type": "captcha", 
                "message": "CAPTCHA detected - manual intervention needed",
                "source": "rule_based"
            }
        
        # Only require intervention if we have dedicated login/signup AND no functional elements
        if login_buttons and signup_buttons and len(functional_elements) == 0:
            return {
                "requires_intervention": True,
                "type": "login",
                "message": "Dedicated login page detected - no functional elements available",
                "source": "rule_based"
            }
        
        return {
            "requires_intervention": False,
            "type": "none",
            "message": "No intervention required",
            "source": "rule_based"
        }

    def verify_page_condition(self, verification_requirement: str, context: str = "") -> Dict:
        """
        Uses LLM to generate custom JavaScript for verifying specific page conditions.
        This is used to confirm that actions were successful.
        """
        try:
            if not self.llm_controller:
                print("No LLM controller available for verification")
                return {"verified": False, "reason": "No LLM available", "method": "none"}
            
            # Generate custom JavaScript for verification
            js_code = self.llm_controller.generate_verification_javascript(verification_requirement, context)
            
            print(f"Generated verification JS: {js_code}")
            
            # Execute the verification JavaScript
            try:
                result = self.browser.execute_script(js_code)
                print(f"Verification result: {result}")
                
                return {
                    "verified": bool(result),
                    "reason": f"Verification {'passed' if result else 'failed'}: {verification_requirement}",
                    "method": "llm_generated_js",
                    "javascript_used": js_code
                }
                
            except Exception as js_error:
                print(f"Error executing verification JavaScript: {js_error}")
                return {
                    "verified": False,
                    "reason": f"JavaScript execution failed: {js_error}",
                    "method": "llm_generated_js",
                    "javascript_used": js_code
                }
                
        except Exception as e:
            print(f"Error in verification: {e}")
            return {"verified": False, "reason": f"Verification error: {e}", "method": "error"}
