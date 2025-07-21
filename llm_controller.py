import os
import re
import json
import logging
import os
import logging
import json
import re
from typing import Dict
from groq import Groq

class LLMController:
    """
    Manages the interaction with the Groq LLM to generate
    Selenium actions based on a given goal and web page context.
    """
    def __init__(self, api_key: str):
        """
        Initializes the Groq client with an API key.
        """
        if not api_key:
            raise ValueError("Groq API key is required.")
        self.client = Groq(api_key=api_key)
        self.model = "moonshotai/kimi-k2-instruct"

        # Setup logger with UTF-8 encoding
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        log_dir = os.path.dirname(__file__)
        log_file_path = os.path.join(log_dir, 'llm_interaction.log')
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        if not self.logger.handlers: # Avoid adding multiple handlers if already initialized
            self.logger.addHandler(file_handler)
    
    def clean_unicode_for_logging(self, text: str) -> str:
        """Clean Unicode characters that might cause encoding issues in logging."""
        try:
            # Replace common problematic Unicode characters
            text = text.replace('\u2192', '->')  # → 
            text = text.replace('\u2190', '<-')  # ←
            text = text.replace('\u2018', "'")   # '
            text = text.replace('\u2019', "'")   # '
            text = text.replace('\u201c', '"')   # "
            text = text.replace('\u201d', '"')   # "
            text = text.replace('\u2013', '-')   # –
            text = text.replace('\u2014', '--')  # —
            
            # Encode to ASCII, replacing any remaining problematic characters
            return text.encode('ascii', 'replace').decode('ascii')
        except Exception:
            # If all else fails, return a safe version
            return str(text).encode('ascii', 'replace').decode('ascii')
    def generate_action_from_page_info(self, goal: str, remaining_steps: list[str], completed_steps: list[str], page_info: Dict) -> dict:
        """
        Generates a JSON command based on the current page interactive elements and goal.
        """
        interactive_elements = page_info.get("interactive_elements", {})
        page_structure = page_info.get("page_structure", {})
        
        system_prompt = """You are a highly intelligent AI agent that specializes in web automation.
        Based on the provided page information with interactive elements, generate the next action as a JSON object.
        Your response MUST be a single, valid JSON object and nothing else.

        Available Actions:
        - "click_element": Clicks an element. Requires "selector".
        - "click_button": Clicks a relevant button automatically using page analysis. Optionally takes "keywords" array for specific button types.
        - "enter_text_no_enter": Enters text into a field WITHOUT pressing Enter. Requires "selector" and "text".
        - "enter_text": Enters text into a field and presses Enter. Requires "selector" and "text".
        - "navigate_to": Navigates to a URL. Requires "url".
        - "wait": Waits for a specified number of seconds. Requires "seconds".
        - "scroll": Scrolls the page. Requires "direction" ("up" or "down") and optionally "pixels".

        IMPORTANT SELECTOR TIPS:
        - Use the exact selectors provided in the interactive elements list
        - For text input, prefer elements with contenteditable='true' or input fields
        - For buttons, look for elements with clear action text or aria-labels
        - Always match the selector exactly as provided in the elements list
        - For common actions like submitting forms or posting, use "click_button" with relevant keywords

        Example Responses:
        {"action": "click_element", "parameters": {"selector": "#login-button"}}
        {"action": "enter_text_no_enter", "parameters": {"selector": "div[contenteditable='true']", "text": "Hello world"}}
        {"action": "click_button", "parameters": {"keywords": ["submit", "send"]}}
        {"action": "click_button", "parameters": {}}
        """

        # Format the interactive elements for the LLM (limit to first 15 most relevant elements)
        elements_info = "Available Interactive Elements:\n"
        elements_list = interactive_elements.get("elements", [])
        
        # Prioritize elements with meaningful text, inputs, and buttons
        def element_priority(element):
            priority = 0
            element_type = element.get('type', '').lower()
            element_tag = element.get('tag', '').lower()
            element_text = element.get('text', '') or ''
            
            # High priority for form inputs and buttons
            if element_type in ['submit', 'button', 'search', 'text', 'email', 'password']:
                priority += 10
            if element_tag in ['button', 'input', 'textarea']:
                priority += 8
            if 'search' in element_text.lower():
                priority += 5
            if element_text.strip():  # Has visible text
                priority += 3
            
            return priority
        
        # Sort by priority and take top 15 elements
        sorted_elements = sorted(elements_list, key=element_priority, reverse=True)[:15]
        
        for i, element in enumerate(sorted_elements):
            elements_info += f"{i+1}. {element.get('tag', 'unknown')} - Selector: {element.get('selector', 'N/A')}\n"
            elements_info += f"   Text: {element.get('text', 'N/A')}\n"
            elements_info += f"   Type: {element.get('type', 'N/A')}\n"
            elements_info += f"   Name: {element.get('name', 'N/A')}\n\n"

        user_content = (
            f"Current Goal: '{goal}'\n\n"
            f"Remaining Steps to Complete:\n"
            f"{chr(10).join(f'- {step}' for step in remaining_steps)}\n\n"
            f"Already Completed Steps:\n"
            f"{chr(10).join(f'[DONE] {step}' for step in completed_steps)}\n\n"
            f"Current Page Info:\n"
            f"URL: {interactive_elements.get('url', 'N/A')}\n"
            f"Title: {interactive_elements.get('title', 'N/A')}\n\n"
            f"{elements_info}\n"
            f"Choose the best action to accomplish the next step in the remaining steps list."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        self.logger.info(f"Sending to LLM (generate_action_from_page_info):\n{json.dumps(messages, indent=2)}")
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
            )
            action_json = chat_completion.choices[0].message.content.strip()
            self.logger.info(f"Received from LLM (generate_action_from_page_info):\n{action_json}")
            
            # Clean the JSON response
            import re
            action_json = re.sub(r'//.*\n', '\n', action_json)
            action_json = action_json.replace('\n', '')
            try:
                return json.loads(action_json)
            except json.JSONDecodeError:
                print(f"Error decoding action JSON: {action_json}")
                return {}
        except Exception as e:
            print(f"Error generating action from LLM: {e}")
            return {}
        """
        Generates a JSON command based on the user's goal, the plan, completed steps, and a summary of the current page.
        """
        system_prompt = """You are a highly intelligent AI agent that specializes in web automation.
        Based on the provided page summary, goal, and plan, generate the next action as a JSON object.
        Your response MUST be a single, valid JSON object and nothing else.

        Available Actions:
        - "click_element": Clicks an element. Requires "selector".
        - "enter_text": Enters text into a field and presses Enter. Requires "selector" and "text".
        - "enter_text_no_enter": Enters text into a field WITHOUT pressing Enter (good for composers, search boxes, forms). Requires "selector" and "text".
        - "navigate_to": Navigates to a URL. Requires "url".
        - "execute_script": Executes JavaScript for data extraction or complex interactions. Requires "script".
        - "wait": Waits for a specified number of seconds. Requires "seconds".
        - "scroll": Scrolls the page. Requires "direction" ("up" or "down") and optionally "pixels".

        IMPORTANT SELECTOR TIPS:
        - Use stable attributes like data-testid, id, aria-label when available
        - For text input areas that aren't traditional form fields, look for contenteditable='true'
        - For buttons, prefer specific aria-labels or data-testid attributes
        - Always analyze the page content to find the most reliable selectors

        Example Responses:
        {"action": "click_element", "parameters": {"selector": "#my-button"}}
        {"action": "enter_text_no_enter", "parameters": {"selector": "div[contenteditable='true']", "text": "Hello world"}}
        {"action": "wait", "parameters": {"seconds": 2}}

        IMPORTANT: If you need to enter text into a composer, text area, or any field where you don't want to immediately submit, use 'enter_text_no_enter' instead of 'enter_text'.
        """

        user_content = (
            f"Current Goal: '{goal}'\n\n"
            f"Overall Plan:\n{plan}\n\n"
            f"Completed Steps: {completed_steps}\n\n"
            f"Current Page Summary:\n---\n{page_summary}\n---\n\n"
            f"IMPORTANT: If you need to enter text into a composer or text area, use 'enter_text_no_enter' instead of 'enter_text' to avoid accidentally submitting before you're ready."
        )

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ]

        self.logger.info(f"Sending to LLM (generate_action):\n{json.dumps(messages, indent=2)}")
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
            )
            action_json = chat_completion.choices[0].message.content.strip()
            self.logger.info(f"Received from LLM (generate_action):\n{action_json}")
            # Clean the JSON response
            action_json = re.sub(r'//.*\n', '\n', action_json)
            action_json = action_json.replace('\n', '')
            try:
                return json.loads(action_json)
            except json.JSONDecodeError:
                print(f"Error decoding action JSON: {action_json}")
                return {}
        except Exception as e:
            print(f"Error generating action from LLM: {e}")
            return {}

    def generate_plan(self, goal: str) -> list[str]:
        """
        Generates a high-level plan to achieve the user's goal.
        """
        system_prompt = """
        You are a strategic AI that creates a high-level plan to achieve a user's goal on a website.
        Break down the goal into a series of simple, actionable steps.
        
        IMPORTANT RULES:
        1. DO NOT duplicate actions - if you click to open composer, don't type in the same step
        2. Be specific about what each step does - don't repeat the same action
        3. DO NOT include VERIFY steps - text entry and button clicks are successful if they execute without errors
        4. Keep steps sequential and non-redundant
        5. Only include verification for page navigation (optional)
        
        STEP SEPARATION:
        - Opening/clicking to access something = ONE step
        - Typing content = SEPARATE step  
        - Publishing/submitting = SEPARATE step (final step)
        
        NO VERIFICATION NEEDED FOR:
        - Text entry (if it types, it worked)
        - Button clicks (if it clicks, it worked)
        - Form submissions (if it submits, it worked)
        - Scrolling or waiting
        
        GOOD EXAMPLE:
        "1. Navigate to google.com"
        "2. Click the search box"
        "3. Type 'artificial intelligence'"
        "4. Click search button"
        
        BAD EXAMPLE (has verification):
        "1. Navigate to google.com"
        "2. Type 'artificial intelligence'"
        "3. Click search button"
        "4. VERIFY: Search results appear"  ← BAD: unnecessary verification
        
        Return only the numbered list of steps, and nothing else.
        Keep the plan concise and to the point.
        If there is an error and you see that there is a CAPTCHA or login form, you should return a message to the user to solve the CAPTCHA or log in.
        """

        user_prompt = f"""
        Goal: "{goal}"

        Create a high-level plan to achieve this goal.
        """

        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]
        self.logger.info(f"Sending to LLM (generate_plan):\n{json.dumps(messages, indent=2)}")
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
            )
            plan_text = chat_completion.choices[0].message.content.strip()
            self.logger.info(f"Received from LLM (generate_plan):\n{plan_text}")
            # Split the plan into a list of tasks
            return [task.strip() for task in plan_text.split('\n') if task.strip()]
        except Exception as e:
            print(f"Error generating plan from LLM: {e}")
            return []

    def verify_step_completion_with_page_info(self, task: str, page_info_before: Dict, page_info_after: Dict) -> bool:
        """
        Verifies if the current step is completed by comparing page state before and after action.
        """
        system_prompt = """You are an AI assistant that verifies if a web automation task has been successfully completed.
        Compare the page state before and after the action to determine if the task was completed successfully.
        
        Consider:
        - Changes in URL or page title
        - New elements that appeared
        - Changes in element states
        - Expected outcomes based on the task
        
        Respond with only "True" or "False".
        """
        
        before_elements = page_info_before.get("interactive_elements", {})
        after_elements = page_info_after.get("interactive_elements", {})
        
        user_prompt = f"""Task: "{task}"

        Page State BEFORE Action:
        URL: {before_elements.get('url', 'N/A')}
        Title: {before_elements.get('title', 'N/A')}
        Number of interactive elements: {len(before_elements.get('elements', []))}

        Page State AFTER Action:
        URL: {after_elements.get('url', 'N/A')}
        Title: {after_elements.get('title', 'N/A')}
        Number of interactive elements: {len(after_elements.get('elements', []))}

        Has the task been completed successfully?"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        self.logger.info(f"Sending to LLM (verify_step_completion_with_page_info):\n{json.dumps(messages, indent=2)}")
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                max_tokens=10
            )
            response = chat_completion.choices[0].message.content.strip().lower()
            self.logger.info(f"Received from LLM (verify_step_completion_with_page_info): {response}")
            return response == "true"
        except Exception as e:
            print(f"Error verifying step completion: {e}")
            return False

    def generate_alternative_plan(self, original_goal: str, failed_steps: list[str], current_page_info: Dict) -> list[str]:
        """
        Generates an alternative plan when the original approach fails.
        """
        system_prompt = """You are a strategic AI that creates alternative plans when the original approach fails.
        Based on the current page state and what has failed, create a new approach to achieve the goal.
        
        Return only a numbered list of steps, nothing else.
        Be creative and consider different approaches to reach the same goal.
        """
        
        interactive_elements = current_page_info.get("interactive_elements", {})
        
        # Limit elements for alternative plan generation (top 10 most relevant)
        elements_info = "Current Page Interactive Elements:\n"
        elements_list = interactive_elements.get("elements", [])
        
        # Prioritize elements for alternative planning
        def element_priority(element):
            priority = 0
            element_type = element.get('type', '').lower()
            element_tag = element.get('tag', '').lower()
            element_text = element.get('text', '') or ''
            
            if element_type in ['submit', 'button', 'search', 'text', 'email']:
                priority += 10
            if element_tag in ['button', 'input', 'a']:
                priority += 5
            if element_text.strip():
                priority += 3
            
            return priority
        
        sorted_elements = sorted(elements_list, key=element_priority, reverse=True)[:10]
        
        for i, element in enumerate(sorted_elements):
            elements_info += f"{i+1}. {element.get('tag', 'unknown')} - {element.get('text', 'N/A')}\n"
        
        user_prompt = f"""
        Original Goal: "{original_goal}"
        
        Failed Steps:
        {chr(10).join(f"- {step}" for step in failed_steps)}
        
        Current Page State:
        URL: {interactive_elements.get('url', 'N/A')}
        Title: {interactive_elements.get('title', 'N/A')}
        
        {elements_info}
        
        Create an alternative plan to achieve the original goal.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        self.logger.info(f"Sending to LLM (generate_alternative_plan):\n{json.dumps(messages, indent=2)}")
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
            )
            plan_text = chat_completion.choices[0].message.content.strip()
            self.logger.info(f"Received from LLM (generate_alternative_plan):\n{self.clean_unicode_for_logging(plan_text)}")
            
            # Split the plan into a list of tasks
            return [task.strip() for task in plan_text.split('\n') if task.strip()]
        except Exception as e:
            print(f"Error generating alternative plan from LLM: {e}")
            return []

    def generate_alternative_selector(self, failed_selector: str, action_type: str, page_info: Dict) -> str:
        """
        Generates a single alternative selector based on available page elements.
        """
        interactive_elements = page_info.get("interactive_elements", {})
        elements = interactive_elements.get("elements", [])
        
        # Try to find similar elements
        for element in elements:
            selector = element.get("selector", "")
            if selector and selector != failed_selector:
                # If it's for the same action type, prioritize it
                if action_type == "click_element" and element.get("tag") in ["button", "input"]:
                    return selector
                elif action_type in ["enter_text", "enter_text_no_enter"] and (
                    element.get("tag") == "input" or "contenteditable" in selector
                ):
                    return selector
        
        # Return a generic fallback
        if action_type == "click_element":
            return "button"
        elif action_type in ["enter_text", "enter_text_no_enter"]:
            return "input"
        
        return failed_selector
        """Verifies if the current step is completed based on the page title, URL, and optionally page summary."""
        system_prompt = """You are an AI assistant that verifies if a web automation task has been successfully completed.
        Based on the task, the current page title, URL, and optionally the page content summary, determine if the task is complete.
        
        Consider:
        - Has the expected navigation occurred?
        - Are the expected elements present on the page?
        - Has the expected action been completed successfully?
        
        Respond with only "True" or "False".
        """
        
        user_prompt = f"""Task: "{task}"
        Current Page Title: "{page_title}"
        Current URL: "{page_url}"
        """
        
        if page_summary:
            user_prompt += f"\nPage Content Summary:\n{page_summary}\n"
        
        user_prompt += "\nIs the task complete?"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        self.logger.info(f"Sending to LLM (verify_step_completion):\n{json.dumps(messages, indent=2)}")
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                max_tokens=10
            )
            response = chat_completion.choices[0].message.content.strip().lower()
            self.logger.info(f"Received from LLM (verify_step_completion): {response}")
            return response == "true"
        except Exception as e:
            print(f"Error verifying step completion: {e}")
            return False


    def generate_alternative_selectors(self, failed_selector: str, action_type: str, page_summary: str) -> list[str]:
        """
        Generates alternative CSS selectors when the original selector fails.
        This helps handle dynamic pages where element attributes change.
        """
        system_prompt = f"""You are an expert in CSS selectors and web automation.
        An element selector has failed to find the target element. Generate 3-5 alternative CSS selectors 
        that could target the same element based on the page content.
        
        Focus on:
        - Different attribute combinations (id, class, data-testid, aria-label, etc.)
        - Partial text matching for buttons/links
        - Structural selectors (nth-child, parent-child relationships)
        - Fallback generic selectors
        - Content-editable elements for text input
        - Role-based selectors (role='button', role='textbox', etc.)
        
        Return only a JSON array of selector strings, nothing else.
        Example: ["#submit-btn", "button[type='submit']", "input[value='Submit']", "div[contenteditable='true']"]
        """
        
        user_prompt = f"""Failed selector: "{failed_selector}"
        Action type: "{action_type}"
        
        Page content summary:
        {page_summary}
        
        Generate alternative selectors for this element."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                max_tokens=200
            )
            response = chat_completion.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            alternative_selectors = json.loads(response)
            return alternative_selectors if isinstance(alternative_selectors, list) else []
            
        except Exception as e:
            print(f"Error generating alternative selectors: {e}")
            # Return some common fallback selectors based on action type
            if action_type in ["enter_text", "enter_text_no_enter"]:
                return [
                    "input[type='text']", 
                    "textarea", 
                    "input", 
                    "div[contenteditable='true']", 
                    "[role='textbox']",
                    "[contenteditable='true']"
                ]
            elif action_type == "click_element":
                return [
                    "button", 
                    "input[type='submit']", 
                    "a", 
                    "[role='button']",
                    "input[type='button']",
                    "[type='submit']"
                ]
            else:
                return []

    def needs_manual_intervention(self, page_context: str) -> dict:
        """
        Checks if the page requires manual user intervention (e.g., CAPTCHA, login form).
        Returns a dict with 'requires_intervention' (bool) and 'message' (str) if intervention is needed.
        """
        system_prompt = """
        You are an AI assistant that detects when a webpage requires CRITICAL manual user intervention.
        Your job is to identify CAPTCHA challenges and login forms that block automation progress.
        
        DETECT and FLAG as requiring intervention:
        - CAPTCHA elements (reCAPTCHA, "I'm not a robot", image challenges, hCaptcha, etc.)
        - Login forms with username/password fields that are blocking access to main content
        - Authentication walls that prevent access to main functionality
        - Pages that ONLY show "Sign in" or "Log in" without any other interactive content
        - Account verification pages that block normal usage
        
        DO NOT flag if the user is ALREADY LOGGED IN:
        - Look for signs the user is logged in to any platform:
          * Profile pictures, usernames, or avatars visible
          * Navigation menus with typical logged-in options
          * Content creation tools (composers, post buttons, etc.)
          * User timeline or feed content
          * Settings/profile menus
          * Any indication of user account access
          * Interactive content creation elements
        - Cookie consent banners  
        - Newsletter signup popups
        - Notification permission requests
        - Age verification (unless it requires account login)
        - Simple dismissible overlays
        - Pages where main content/functionality is accessible
        
        CRITICAL: If you see any functional interface elements that suggest user interaction capabilities
        (compose areas, navigation menus, user controls), DO NOT flag for intervention.
        
        Only flag pages that show ONLY login forms with no other functional content.
        
        Respond with a JSON object:
        {"requires_intervention": true, "type": "login", "message": "Login required - manual intervention needed"}
        {"requires_intervention": true, "type": "captcha", "message": "CAPTCHA detected - manual intervention needed"}  
        {"requires_intervention": false, "type": "none", "message": ""}
        """

        user_prompt = f"""
        Simplified HTML of the current page:
        ---
        {page_context}
        ---

        Analyze this page and determine if manual intervention is required.
        
        IMPORTANT: Look carefully for signs the user is already logged in:
        - Content creation elements (composers, text areas, post buttons)
        - Navigation menus with user options
        - User profile information or avatars
        - Interactive content or feeds
        - Any functional interface elements
        
        Only flag for intervention if:
        1. There are CAPTCHA challenges, OR
        2. The page shows ONLY login forms with no other functional content accessible
        
        Focus only on situations that truly block automation progress.
        """

        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        self.logger.info(f"Sending to LLM (needs_manual_intervention):\n{json.dumps(messages, indent=2)}")
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model
            )
            response = chat_completion.choices[0].message.content.strip()
            self.logger.info(f"Received from LLM (needs_manual_intervention):\n{response}")
            
            try:
                result = json.loads(response)
                return result
            except json.JSONDecodeError:
                # Fallback parsing if JSON is malformed
                if "captcha" in response.lower():
                    return {"requires_intervention": True, "type": "captcha", "message": "CAPTCHA detected - manual intervention required"}
                elif "login" in response.lower():
                    return {"requires_intervention": True, "type": "login", "message": "Login required - manual intervention required"}
                else:
                    return {"requires_intervention": False, "type": "none", "message": ""}
        except Exception as e:
            print(f"Error checking for manual intervention: {e}")
            return {"requires_intervention": False, "type": "none", "message": ""}

    def get_popup_closing_action(self, page_context: str) -> str | None:
        """
        Generates a Selenium command to close a simple pop-up (e.g., cookie banner, notification).
        """
        system_prompt = """
        You are an AI assistant that generates Selenium code to close simple pop-ups.
        Analyze the provided HTML and identify any cookie banners, notification pop-ups, or other non-critical overlays.
        Generate a single line of Python code to click the 'accept', 'close', 'dismiss', or similar button.

        If no pop-up is detected, respond with "None".
        """

        user_prompt = f"""
        Simplified HTML of the current page:
        ---
        {page_context}
        ---

        Generate the Selenium command to close any simple pop-ups.
        """

        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        self.logger.info(f"Sending to LLM (get_popup_closing_action):\n{json.dumps(messages, indent=2)}")
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model
                # Removed max_tokens parameter
            )
            action_code = chat_completion.choices[0].message.content.strip()
            self.logger.info(f"Received from LLM (get_popup_closing_action):\n{action_code}")
            if "none" in action_code.lower():
                return None
            return action_code
        except Exception as e:
            print(f"Error generating pop-up closing action: {e}")
            return None

    def analyze_page_for_intervention(self, page_elements: list) -> dict:
        """
        Simple LLM-based analysis to determine if manual intervention is needed.
        Analyzes the JSON elements and decides based on patterns.
        """
        try:
            # Create a simplified summary of elements for the LLM
            element_summary = []
            for element in page_elements[:20]:  # Limit to first 20 elements to avoid token limits
                summary = {
                    "tag": element.get("tag"),
                    "text": element.get("text"),
                    "data-testid": element.get("data-testid"),
                    "href": element.get("href"),
                    "type": element.get("type"),
                    "role": element.get("role")
                }
                element_summary.append(summary)
            
            prompt = f"""
            Analyze these page elements and determine if MANUAL INTERVENTION is required.

            ELEMENTS FOUND:
            {element_summary}

            CRITICAL RULES FOR MANUAL INTERVENTION:
            1. ONLY require intervention if BOTH "loginButton" AND "signupButton" data-testid values are present
            2. ONLY require intervention if CAPTCHA elements are blocking functionality
            3. ONLY require intervention if the page explicitly blocks access to requested functionality

            DO NOT REQUIRE INTERVENTION FOR:
            - Pages with login/signup links in headers or sidebars (like Wikipedia, news sites)
            - Open websites that allow browsing without login
            - Sites where login is optional for basic functionality
            - Pages with search boxes, articles, or general content accessible

            REQUIRE INTERVENTION ONLY FOR:
            - Dedicated login pages that block all functionality
            - CAPTCHA challenges that prevent progression
            - Pages that explicitly require authentication for the requested action

            WEBSITE CONTEXT:
            - Wikipedia, news sites, search engines = NO INTERVENTION (open browsing)
            - Social media posting pages without content = INTERVENTION NEEDED
            - Dedicated login/signup forms = INTERVENTION NEEDED
            - E-commerce, information sites = NO INTERVENTION

            Respond in JSON format:
            {{
                "requires_intervention": true/false,
                "reason": "brief explanation",
                "type": "login/captcha/none"
            }}
            """
            
            messages = [
                {"role": "system", "content": "You are an expert web page analyzer. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ]
            
            self.logger.info(f"Sending to LLM (analyze_page_for_intervention):\n{json.dumps(messages, indent=2)}")
            
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model
            )
            
            response_text = chat_completion.choices[0].message.content.strip()
            self.logger.info(f"Received from LLM (analyze_page_for_intervention):\n{response_text}")
            
            # Parse JSON response
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse JSON from LLM response")
            
            # Ensure we have the required fields
            if not isinstance(result, dict):
                return {"requires_intervention": False, "reason": "Invalid LLM response", "type": "none"}
                
            return {
                "requires_intervention": result.get("requires_intervention", False),
                "reason": result.get("reason", "No reason provided"),
                "type": result.get("type", "none")
            }
            
        except Exception as e:
            print(f"Error in LLM intervention analysis: {e}")
            return {"requires_intervention": False, "reason": f"Analysis error: {e}", "type": "none"}

    def generate_verification_javascript(self, verification_requirement: str, context: str = "") -> str:
        """
        Generates custom JavaScript code to verify specific page conditions or text presence.
        This is used to confirm that actions were successful (e.g., text was typed, post was published).
        """
        try:
            prompt = f"""
            Generate JavaScript code to verify the following requirement on a web page:
            
            VERIFICATION REQUIREMENT: {verification_requirement}
            
            CONTEXT: {context}
            
            INSTRUCTIONS:
            - Generate ONLY executable JavaScript code
            - The code should return a boolean (true if verification passes, false if fails)
            - Use document.querySelector, getElementsByText, or similar DOM methods
            - Check for visible text, input values, or element states as needed
            - Be specific and look for exact text matches when required
            - Handle cases where elements might not exist (return false)
            
            EXAMPLES:
            - To verify "Hola mundo" was typed in an input: return document.querySelector('input[data-testid="tweetTextarea_0"]')?.value?.includes("Hola mundo") || false;
            - To verify a tweet was posted: return document.querySelector('[data-testid="tweet"]')?.textContent?.includes("Hola mundo") || false;
            - To verify text appears on page: return document.body.textContent.includes("specific text") || false;
            
            Respond with ONLY the JavaScript code, no explanations:
            """
            
            messages = [
                {"role": "system", "content": "You are a JavaScript code generator. Respond only with executable JavaScript code."},
                {"role": "user", "content": prompt}
            ]
            
            self.logger.info(f"Sending to LLM (generate_verification_javascript):\n{verification_requirement}")
            
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model
            )
            
            js_code = chat_completion.choices[0].message.content.strip()
            self.logger.info(f"Received verification JS from LLM:\n{js_code}")
            
            # Clean up the JavaScript code
            js_code = js_code.replace('```javascript', '').replace('```', '').strip()
            
            return js_code
            
        except Exception as e:
            print(f"Error generating verification JavaScript: {e}")
            # Fallback: basic text search
            return f'return document.body.textContent.includes("{verification_requirement}") || false;'


if __name__ == '__main__':
    # This block can be used for testing, but is not part of the main application logic.
    pass