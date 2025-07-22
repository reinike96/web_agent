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
            
            # Enhanced login/signup detection patterns
            login_patterns = [
                # Direct testid patterns
                "loginbutton", "login_button", "sign_in_button", "signin_button",
                # Google/Apple/Social login patterns
                "google_placeholder_button", "google_sign_in", "google_login",
                "apple_sign_in_button", "apple_login", "facebook_login",
                # Generic patterns in testid
                "login", "signin", "sign_in"
            ]
            
            signup_patterns = [
                # Direct testid patterns  
                "signupbutton", "signup_button", "sign_up_button", "register_button",
                # Social signup patterns
                "google_placeholder_button", "google_sign_up", "apple_sign_in_button",
                # Generic patterns
                "signup", "sign_up", "register", "create_account"
            ]
            
            # Check text content for login/signup indicators
            login_text_patterns = [
                "iniciar sesi?n", "log in", "sign in", "entrar", "acceder",
                "ingresar", "login", "conectarse"
            ]
            
            signup_text_patterns = [
                "registrarse", "sign up", "crear cuenta", "register", "unirse",
                "crear perfil", "new account", "join"
            ]
            
            # Check for login indicators
            is_login = (
                any(pattern in data_testid for pattern in login_patterns) or
                any(pattern in text for pattern in login_text_patterns) or
                ("google" in text and any(word in text for word in ["sign", "login", "inicia"])) or
                ("apple" in text and any(word in text for word in ["sign", "login", "inicia"]))
            )
            
            # Check for signup indicators
            is_signup = (
                any(pattern in data_testid for pattern in signup_patterns) or
                any(pattern in text for pattern in signup_text_patterns) or
                ("google" in text and any(word in text for word in ["registr", "crear", "sign up"])) or
                ("apple" in text and any(word in text for word in ["registr", "crear", "sign up"]))
            )
            
            if is_login:
                login_buttons.append(element)
            if is_signup:
                signup_buttons.append(element)
            
            # Check for CAPTCHA indicators
            if any(indicator in text for indicator in ["captcha", "verify you're human", "i'm not a robot", "verificar que eres humano"]):
                captcha_indicators.append(element)
            
            # Check for functional elements that indicate the site is usable
            if (element_type in ["input", "button", "link"] and 
                any(keyword in text for keyword in ["search", "article", "read", "browse", "explore", "menu", "buscar", "explorar", "leer"])):
                functional_elements.append(element)
        
        # Decision logic - enhanced detection
        if captcha_indicators:
            return {
                "requires_intervention": True,
                "type": "captcha", 
                "message": "CAPTCHA detected - manual intervention needed",
                "details": f"Found {len(captcha_indicators)} CAPTCHA indicators",
                "source": "rule_based"
            }
        
        # Check if this looks like a dedicated login/signup page
        total_login_signup = len(login_buttons) + len(signup_buttons)
        has_social_login = any(
            any(social in elem.get("text", "").lower() for social in ["google", "apple", "facebook", "twitter"])
            for elem in login_buttons + signup_buttons
        )
        
        # More sophisticated login page detection
        is_login_page = (
            # Has multiple login/signup options
            total_login_signup >= 2 or
            # Has social login options (common pattern for dedicated login pages)
            has_social_login or
            # Has login buttons but very few functional elements
            (login_buttons and len(functional_elements) <= 1) or
            # Has signup buttons but very few functional elements
            (signup_buttons and len(functional_elements) <= 1)
        )
        
        if is_login_page:
            login_types = []
            if login_buttons:
                login_types.append(f"{len(login_buttons)} login buttons")
            if signup_buttons:
                login_types.append(f"{len(signup_buttons)} signup buttons")
            
            return {
                "requires_intervention": True,
                "type": "login",
                "message": "Login/signup page detected - manual intervention needed",
                "details": f"Found: {', '.join(login_types)}. Social login: {'Yes' if has_social_login else 'No'}. Functional elements: {len(functional_elements)}",
                "source": "enhanced_rule_based"
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
