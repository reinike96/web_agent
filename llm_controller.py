import os
import re
import json
import logging
from typing import Dict, List
from datetime import datetime
from groq import Groq
from data_extraction_agent import DataExtractionAgent

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
        
        # Initialize data extraction agent
        self.data_extraction_agent = DataExtractionAgent(self.client)

        # Setup simplified daily logger 
        self.log_dir = os.path.dirname(__file__)
        self.log_file_path = os.path.join(self.log_dir, 'llm_interaction.log')
        self._setup_daily_logger()
        
        # Track session info
        self.current_goal = None
        self.current_plan = None
    
    def _setup_daily_logger(self):
        """Setup logger that resets daily and only logs essential info"""
        # Check if we need to reset the log file (daily reset)
        self._reset_log_if_new_day()
        
        # Setup basic logging without timestamp/level (simplified format)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Add new file handler with simplified format
        file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
        formatter = logging.Formatter('%(message)s')  # Only the message, no timestamp
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def _reset_log_if_new_day(self):
        """Reset log file if it's a new day"""
        try:
            if os.path.exists(self.log_file_path):
                # Get file creation time
                file_time = datetime.fromtimestamp(os.path.getctime(self.log_file_path))
                current_time = datetime.now()
                
                # If file is from a different day, reset it
                if file_time.date() != current_time.date():
                    with open(self.log_file_path, 'w', encoding='utf-8') as f:
                        f.write(f"=== LOG RESET - {current_time.strftime('%Y-%m-%d')} ===\n\n")
            else:
                # Create new log file
                with open(self.log_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"=== NEW LOG - {datetime.now().strftime('%Y-%m-%d')} ===\n\n")
        except Exception as e:
            print(f"Warning: Could not reset log file: {e}")
    
    def log_goal_and_plan(self, goal: str, plan: List[str]):
        """Log only the goal and plan at the start of session"""
        self.current_goal = goal
        self.current_plan = plan
        
        log_entry = f"""
=== SESSION START ===
GOAL: {goal}

PLAN:
"""
        for i, step in enumerate(plan, 1):
            log_entry += f"{i}. {step}\n"
        
        log_entry += "\n" + "="*50 + "\n"
        self.logger.info(log_entry)
    
    def log_action_code(self, action_type: str, method_used: str, code_used: str, success: bool):
        """Log only the essential code information for each action"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        status = "✅ SUCCESS" if success else "❌ FAILED"
        
        log_entry = f"""
[{timestamp}] ACTION: {action_type} ({method_used}) - {status}
CODE USED:
{code_used}

---
"""
        self.logger.info(log_entry)
    
    def clean_unicode_for_logging(self, text: str) -> str:
        """Clean Unicode characters that might cause encoding issues in logging."""
        try:
            # Replace common problematic Unicode characters
            text = text.replace('\u2192', '->')  # ? 
            text = text.replace('\u2190', '<-')  # ?
            text = text.replace('\u2018', "'")   # '
            text = text.replace('\u2019', "'")   # '
            text = text.replace('\u201c', '"')   # "
            text = text.replace('\u201d', '"')   # "
            text = text.replace('\u2013', '-')   # ?
            text = text.replace('\u2014', '--')  # ?
            
            # Encode to ASCII, replacing any remaining problematic characters
            return text.encode('ascii', 'replace').decode('ascii')
        except Exception:
            # If all else fails, return a safe version
            return str(text).encode('ascii', 'replace').decode('ascii')

    def ask_llm_with_context(self, prompt: str, page_context: dict = None) -> str:
        """
        Generic method to ask the LLM with a prompt and optional page context.
        Used by fallback systems and other generic LLM interactions.
        NO TOKEN LIMITS - allows full response generation.
        """
        try:
            system_prompt = "You are an expert web automation assistant. Generate precise JavaScript code for web interactions."
            
            if page_context:
                # Include ALL context data without limits
                context_info = f"\nPage Context: {json.dumps(page_context, indent=2)}\n"
                user_content = context_info + prompt
            else:
                user_content = prompt
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            # No detailed logging here - will be handled by the action controller
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model
                # NO max_tokens restriction - allow full generation
            )
            
            response = chat_completion.choices[0].message.content.strip()
            
            return response
            
        except Exception as e:
            # Only log errors, not regular interactions
            print(f"Error in ask_llm_with_context: {e}")
            return ""
            
    def generate_action_from_page_info(self, goal: str, remaining_steps: list[str], completed_steps: list[str], page_info: Dict) -> dict:
        """
        Generates a JSON command based on the current page interactive elements and goal.
        """
        # Check if the current step mentions data_extraction_agent
        if remaining_steps:
            current_step = remaining_steps[0].lower()
            if "data_extraction_agent" in current_step:
                # This is an extraction step - use the DataExtractionAgent
                print(f"[DEBUG] Detected extraction step: {current_step}")
                return self._generate_extraction_action(goal, current_step, page_info)
        
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
        
        # Sort by priority and provide ALL elements without limit
        sorted_elements = sorted(elements_list, key=element_priority, reverse=True)
        # NO LIMIT - provide all elements to LLM
        
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
        Automatically detects data extraction tasks and creates appropriate plans.
        """
        
        # For all tasks, use the regular planning approach but instruct LLM to mention data_extraction_agent when needed
        system_prompt = """
        You are a strategic AI that creates a high-level plan to achieve a user's goal on a website.
        Break down the goal into a series of simple, actionable steps.
        
        IMPORTANT RULES:
        1. DO NOT duplicate actions - if you click to open composer, don't type in the same step
        2. Be specific about what each step does - don't repeat the same action
        3. DO NOT include VERIFY steps - text entry and button clicks are successful if they execute without errors
        4. Keep steps sequential and non-redundant
        5. Only include verification for page navigation (optional)
        6. NEVER suggest copy/paste or print actions for data extraction.
        
        LOGIN/AUTH DETECTION:
        If the goal requires accessing a service that typically needs authentication (Twitter/X, Facebook, Instagram, LinkedIn, private accounts, user dashboards), 
        include a manual intervention step FIRST:
        - "Navigate to [website]"  
        - "MANUAL_INTERVENTION: Complete login process if required"
        - Then continue with main goal steps
        
        Common sites requiring auth: x.com, twitter.com, facebook.com, instagram.com, linkedin.com, gmail.com, outlook.com, etc.
        
        DATA EXTRACTION TASKS:
        When the goal involves extracting data, getting information, downloading content to files (Excel, Word, TXT), 
        collecting results, or saving website content to documents, include steps with these EXACT phrases:
        - "Extract product data using data_extraction_agent"
        - "Use data_extraction_agent to collect search results" 
        - "Execute data_extraction_agent to save content to Excel"
        - "Run data_extraction_agent to download page content"
        
        WRITE CLEARLY: Use simple, clear language. Do NOT repeat words or create corrupted text like "Data Ex Ex Ex".
        
        STEP SEPARATION:
        - Opening/clicking to access something = ONE step
        - Typing content = SEPARATE step  
        - Publishing/submitting = SEPARATE step (final step)
        
        SPECIFIC ACTION WORDING:
        For content creation (posts, messages, comments):
        - Use "Open the content composer" or "Access the posting interface" instead of generic "click post button"
        - Be specific: "Click the main compose button to open text editor" vs "Click on any message field"
        - Avoid ambiguous terms like "post button" that could match multiple elements
        - Focus on the ACTION (opening composer) not the UI element name
        
        NO VERIFICATION NEEDED FOR:
        - Text entry (if it types, it worked)
        - Button clicks (if it clicks, it worked)
        - Form submissions (if it submits, it worked)
        - Scrolling or waiting
        - Checking if the text in the inputbox was sent (if it was pressed send, it was sent)

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

    def _generate_extraction_plan(self, extraction_intent: dict) -> list[str]:
        """
        Generates a specialized plan for data extraction tasks using JavaScript execution.
        """
        target = extraction_intent.get("target", "information")
        format_type = extraction_intent.get("format", "txt")
        needs_scrolling = extraction_intent.get("needs_scrolling", False)
        
        # Use the DataExtractionAgent to create a proper extraction plan
        plan_steps = []
        
        # Step 1: Navigate to target page (if URL is in goal)
        goal_lower = target.lower()
        if any(url_indicator in goal_lower for url_indicator in ["http", "www.", ".com", ".org", ".net"]):
            plan_steps.append("1. Navigate to the specified URL")
        else:
            plan_steps.append("1. Navigate to the target page")
        
        # Step 2: Wait for page load
        current_step = len(plan_steps) + 1
        plan_steps.append(f"{current_step}. Wait for page content to fully load")
        
        # Step 3: Optional scrolling if needed
        if needs_scrolling:
            current_step += 1
            plan_steps.append(f"{current_step}. Scroll slowly through the page to load all content")
        
        # Step 4: Execute JavaScript extraction - make this step very clear
        current_step += 1
        plan_steps.append(f"{current_step}. Execute data extraction JavaScript to collect content and automatically download as {format_type.upper()} file")
        
        self.logger.info(f"Generated extraction plan for {target} -> {format_type}: {plan_steps}")
        return plan_steps
    
    def _generate_extraction_action(self, goal: str, current_step: str, page_info: Dict) -> dict:
        """
        Generates a JavaScript execution action for data extraction using the DataExtractionAgent.
        """
        print(f"[DEBUG] Generating extraction action for goal: {goal}")
        
        # Use the current step (from the plan) to detect extraction details instead of the original goal
        is_extraction, extraction_details = self.data_extraction_agent.detect_extraction_intent(current_step)
        print(f"[DEBUG] Extraction details: is_extraction={is_extraction}, details={extraction_details}")
        
        if not is_extraction:
            # Fallback to regular action generation
            print("[DEBUG] No extraction detected, using wait action as fallback")
            return {"action": "wait", "parameters": {"seconds": 2}}
        
        # Override format detection if Excel is mentioned in the goal
        if 'excel' in goal.lower() and extraction_details.get('format') == 'txt':
            print("[DEBUG] Overriding format to Excel based on goal")
            extraction_details['format'] = 'excel'
        
        try:
            # Use simple text extraction instead of complex JavaScript generation
            print("[DEBUG] Using simple page content extraction...")
            
            result_action = {
                "action": "extract_simple",
                "parameters": {
                    "format": extraction_details.get('format', 'txt'),
                    "goal": extraction_details.get('goal', goal)
                }
            }
            print(f"[DEBUG] Returning simple extraction action: {result_action['action']}")
            return result_action
        except Exception as e:
            print(f"[ERROR] Error generating extraction action: {e}")
            # Fallback to wait action
            return {"action": "wait", "parameters": {"seconds": 2}}

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
                model=self.model
                # Removed max_tokens to allow full response
            )
            response = chat_completion.choices[0].message.content.strip().lower()
            self.logger.info(f"Received from LLM (verify_step_completion_with_page_info): {response}")
            return response == "true"
        except Exception as e:
            print(f"Error verifying step completion: {e}")
            return False

    def generate_alternative_plan(self, original_goal: str, failed_steps: list[str], current_page_info: Dict, completed_steps: list[str] = None) -> list[str]:
        """
        Generates an alternative plan when the original approach fails.
        """
        system_prompt = """You are a strategic AI that creates SMART alternative plans when the original approach fails.
        
        CRITICAL ANTI-DUPLICATION RULES:
        1. ANALYZE what core objectives may have ALREADY been completed
        2. DO NOT recreate steps for objectives that are likely already achieved
        3. FOCUS ONLY on the specific failed steps, not the entire original goal
        4. If posting/publishing goals: Check if posts were already made successfully in earlier steps
        5. If extraction goals: Check if data was already extracted in earlier steps

        FOR POSTING/PUBLISHING OBJECTIVES:
        - If previous steps show successful posting actions, DO NOT create new posting steps
        - Focus only on navigation or technical issues, not content recreation
        - AVOID duplicating: "Type message", "Click post", "Enter text" if posts were already made
        
        FOR DATA EXTRACTION GOALS:
        1. Navigate to target URL
        2. Use data_extraction_agent to extract page content (this ALWAYS works)
        3. If multiple pages needed, try simple navigation:
           - Look for "Next" or "Weiter" buttons
           - If navigation fails, try URL modification (add ?page=2, &page=2, etc.)
        4. Use data_extraction_agent on each page
        5. System will automatically consolidate results

        AVOID:
        - Recreating content that was already posted/published
        - Complex JavaScript snippets
        - Browser console commands  
        - Specific CSS selectors that might not exist
        - Duplicating core objectives that were already completed

        PREFER:
        - Simple navigation fixes
        - Technical troubleshooting steps
        - Generic button clicking for navigation only
        - URL manipulation for pagination
        - Let data_extraction_agent handle the extraction details

        SMART ANALYSIS: Before creating new steps, consider if the main goal was already achieved
        and only create steps to resolve specific technical issues.

        Return only a numbered list of simple steps, nothing else.
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
        
        sorted_elements = sorted(elements_list, key=element_priority, reverse=True)
        # NO LIMIT - provide all elements for complete alternative planning
        
        for i, element in enumerate(sorted_elements):
            elements_info += f"{i+1}. {element.get('tag', 'unknown')} - {element.get('text', 'N/A')}\n"
        
        user_prompt = f"""
        Original Goal: "{original_goal}"
        
        ALREADY COMPLETED STEPS (DO NOT DUPLICATE):
        {chr(10).join(f"✅ {step}" for step in (completed_steps or []))}
        
        Failed Steps (need alternatives for):
        {chr(10).join(f"❌ {step}" for step in failed_steps)}
        
        Current Page State:
        URL: {interactive_elements.get('url', 'N/A')}
        Title: {interactive_elements.get('title', 'N/A')}
        
        {elements_info}
        
        IMPORTANT: Analyze the completed steps above. If core posting/publishing objectives were 
        already achieved successfully, DO NOT create new steps that would duplicate content.
        Only create steps to resolve specific technical issues or navigation problems.
        
        Create a smart alternative plan that avoids duplicating completed objectives.
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

    def verify_step_completion(self, task: str, page_title: str, page_url: str, page_summary: str = None) -> bool:
        """
        Verifies if a step has been completed successfully by analyzing page changes.
        """
        system_prompt = """You are an expert at verifying task completion in web automation.
        Analyze the current page state to determine if the specified task has been completed.
        
        Return only 'true' if the task is completed, 'false' if not completed.
        Consider:
        - Page title changes that indicate success
        - URL changes that show navigation occurred
        - Content that suggests the task was successful
        """
        
        user_prompt = f"""
        Task to verify: {task}
        Current page title: {page_title}
        Current page URL: {page_url}
        Page summary: {page_summary or 'No summary available'}
        
        Has this task been completed successfully? Answer only 'true' or 'false'.
        """
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model
                # Removed max_tokens to allow full response
            )
            
            response = chat_completion.choices[0].message.content.strip().lower()
            return response == "true"
            
        except Exception as e:
            print(f"Error verifying step completion: {e}")
            return False

    def generate_alternative_selectors(self, failed_selector: str, action_type: str, page_summary: str) -> List[str]:
        """
        Generates alternative CSS selectors when the original selector fails.
        This helps handle dynamic pages where element attributes change.
        """
        system_prompt = """You are an expert in CSS selectors and web automation.
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
                model=self.model
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
            # Create a complete summary of ALL elements for the LLM
            element_summary = []
            for element in page_elements:  # NO LIMIT - provide all elements
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

    def generate_data_extraction_script(self, extraction_goal: str, output_format: str, page_context: str) -> str:
        """
        Generates JavaScript code to extract specific information from a webpage and create downloadable files.
        This agent specializes in data extraction with progressive scrolling and file generation.
        """
        system_prompt = f"""You are an expert JavaScript code generator specialized in web data extraction.
        Your task is to generate JavaScript code that:
        
        1. EXTRACTS specific information from the current webpage
        2. HANDLES progressive scrolling to capture all available data
        3. GENERATES a downloadable file in the specified format
        4. NEVER attempts to use copy/paste or print functionality
        
        OUTPUT FORMATS SUPPORTED:
        - "txt": Plain text file with structured data
        - "excel": CSV format that can be opened in Excel
        - "word": HTML format that can be opened in Word
        
        EXTRACTION PATTERNS:
        - Use document.querySelectorAll() to find data elements
        - Implement gradual scrolling with window.scrollBy() and waiting
        - Check for "Load More" buttons and click them automatically
        - Detect when scrolling reaches the end (no new content loaded)
        - Extract text content, links, images, tables, lists, etc.
        
        PROGRESSIVE SCROLLING TEMPLATE:
        ```javascript
        async function scrollAndExtract() {{
            let allData = [];
            let lastHeight = 0;
            let scrollAttempts = 0;
            const maxScrolls = 50; // Prevent infinite scrolling
            
            while (scrollAttempts < maxScrolls) {{
                // Extract current visible data
                const currentData = document.querySelectorAll('SELECTOR').forEach(el => /* extract logic */);
                allData.push(...currentData);
                
                // Scroll down
                window.scrollBy(0, 1000);
                await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds
                
                // Check if new content loaded
                const newHeight = document.body.scrollHeight;
                if (newHeight === lastHeight) {{
                    break; // No new content, stop scrolling
                }}
                lastHeight = newHeight;
                scrollAttempts++;
            }}
            
            return allData;
        }}
        ```
        
        FILE GENERATION TEMPLATE:
        ```javascript
        function downloadFile(content, filename, mimeType) {{
            const blob = new Blob([content], {{ type: mimeType }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}
        ```
        
        IMPORTANT RULES:
        - Generate COMPLETE, executable JavaScript code
        - Include error handling for missing elements
        - Use descriptive variable names
        - Add comments explaining each step
        - Ensure the code is self-contained and doesn't require external libraries
        - Handle dynamic content loading gracefully
        - Generate appropriate file names with timestamps
        
        Return ONLY the JavaScript code, no explanations.
        """
        
        user_prompt = f"""
        EXTRACTION GOAL: {extraction_goal}
        OUTPUT FORMAT: {output_format}
        
        PAGE CONTEXT (for selector guidance):
        {page_context[:1000]}  # Limit context to avoid token limits
        
        Generate JavaScript code that:
        1. Progressively scrolls through the page to capture all data
        2. Extracts the requested information
        3. Creates a downloadable {output_format} file with the extracted data
        4. Handles dynamic content loading automatically
        
        Focus on finding the most relevant selectors based on the page structure shown above.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        self.logger.info(f"Sending to LLM (generate_data_extraction_script): {extraction_goal} -> {output_format}")
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model
                # Removed max_tokens to allow unlimited response generation
            )
            js_code = chat_completion.choices[0].message.content.strip()
            self.logger.info(f"Received extraction script from LLM (length: {len(js_code)} chars)")
            
            # Clean up the JavaScript code
            js_code = js_code.replace('```javascript', '').replace('```', '').strip()
            
            return js_code
            
        except Exception as e:
            print(f"Error generating data extraction script: {e}")
            return self._generate_fallback_extraction_script(extraction_goal, output_format)
    
    def _generate_fallback_extraction_script(self, extraction_goal: str, output_format: str) -> str:
        """
        Generates a basic fallback extraction script when the LLM fails.
        """
        if output_format == "txt":
            return """
            // Fallback data extraction script for TXT format
            async function extractData() {
                console.log('Starting data extraction for TXT format...');
                let allText = [];
                let scrollAttempts = 0;
                let lastHeight = document.body.scrollHeight;
                
                // Progressive scrolling and extraction
                while (scrollAttempts < 20) {
                    // Extract text from common content selectors
                    const elements = document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, td, span[data-text="true"], div[role="article"]');
                    elements.forEach(el => {
                        const text = el.textContent.trim();
                        if (text && text.length > 10 && !allText.includes(text)) {
                            allText.push(text);
                        }
                    });
                    
                    console.log(`Scroll attempt ${scrollAttempts + 1}, found ${allText.length} text elements`);
                    window.scrollBy(0, 1000);
                    await new Promise(resolve => setTimeout(resolve, 1500));
                    
                    const newHeight = document.body.scrollHeight;
                    if (newHeight === lastHeight) break;
                    lastHeight = newHeight;
                    scrollAttempts++;
                }
                
                // Generate file
                const content = allText.join('\\n\\n');
                const filename = `extracted_data_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.txt`;
                const blob = new Blob([content], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                console.log(`Data extracted to ${filename}`);
                return `Data extracted to ${filename}`;
            }
            
            extractData().then(console.log).catch(console.error);
            """
        elif output_format == "excel":
            return """
            // Fallback data extraction script for Excel/CSV format
            async function extractDataToCSV() {
                console.log('Starting data extraction for CSV format...');
                let allData = [];
                let scrollAttempts = 0;
                let lastHeight = document.body.scrollHeight;
                
                // Add header row
                allData.push('"Content","Type","Source"');
                
                // Progressive scrolling and extraction
                while (scrollAttempts < 20) {
                    // Extract structured data
                    const rows = document.querySelectorAll('tr, div[role="row"], li, p, h1, h2, h3');
                    rows.forEach((row, index) => {
                        const text = row.textContent.trim().replace(/"/g, '""');
                        if (text && text.length > 5) {
                            const rowData = `"${text}","${row.tagName}","Row ${index + 1}"`;
                            if (!allData.includes(rowData)) {
                                allData.push(rowData);
                            }
                        }
                    });
                    
                    console.log(`Scroll attempt ${scrollAttempts + 1}, found ${allData.length} data rows`);
                    window.scrollBy(0, 1000);
                    await new Promise(resolve => setTimeout(resolve, 1500));
                    
                    const newHeight = document.body.scrollHeight;
                    if (newHeight === lastHeight) break;
                    lastHeight = newHeight;
                    scrollAttempts++;
                }
                
                // Generate CSV file
                const csvContent = allData.join('\\n');
                const filename = `extracted_data_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.csv`;
                const blob = new Blob([csvContent], { type: 'text/csv' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                console.log(`CSV data extracted to ${filename}`);
                return `CSV data extracted to ${filename}`;
            }
            
            extractDataToCSV().then(console.log).catch(console.error);
            """
        else:  # word format
            return """
            // Fallback data extraction script for Word/HTML format
            async function extractDataToWord() {
                console.log('Starting data extraction for Word format...');
                let allContent = [];
                let scrollAttempts = 0;
                let lastHeight = document.body.scrollHeight;
                
                // Progressive scrolling and extraction
                while (scrollAttempts < 20) {
                    // Extract formatted content
                    const elements = document.querySelectorAll('h1, h2, h3, h4, h5, h6, p, ul, ol, table, blockquote');
                    elements.forEach(el => {
                        const content = el.outerHTML;
                        if (!allContent.some(item => item.includes(el.textContent.trim().substring(0, 50)))) {
                            allContent.push(content);
                        }
                    });
                    
                    console.log(`Scroll attempt ${scrollAttempts + 1}, found ${allContent.length} formatted elements`);
                    window.scrollBy(0, 1000);
                    await new Promise(resolve => setTimeout(resolve, 1500));
                    
                    const newHeight = document.body.scrollHeight;
                    if (newHeight === lastHeight) break;
                    lastHeight = newHeight;
                    scrollAttempts++;
                }
                
                // Generate Word-compatible HTML file
                const htmlContent = `
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>Extracted Data</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
                        h1, h2, h3 { color: #333; margin-top: 20px; }
                        table { border-collapse: collapse; width: 100%; margin: 10px 0; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                        th { background-color: #f2f2f2; }
                        blockquote { border-left: 4px solid #ccc; margin: 10px 0; padding-left: 10px; }
                    </style>
                </head>
                <body>
                    <h1>Extracted Data Report</h1>
                    <p><strong>Generated:</strong> ${new Date().toLocaleString()}</p>
                    <p><strong>Source:</strong> ${window.location.href}</p>
                    <hr>
                    ${allContent.join('\\n')}
                </body>
                </html>
                `;
                
                const filename = `extracted_data_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.html`;
                const blob = new Blob([htmlContent], { type: 'text/html' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                console.log(`Word-compatible data extracted to ${filename}`);
                return `Word-compatible data extracted to ${filename}`;
            }
            
            extractDataToWord().then(console.log).catch(console.error);
            """

    def detect_extraction_intent(self, goal: str) -> dict:
        """
        Detects if the user's goal involves data extraction using the DataExtractionAgent.
        Returns extraction details or None if not an extraction task.
        """
        # Use the specialized DataExtractionAgent for detection
        is_extraction, extraction_details = self.data_extraction_agent.detect_extraction_intent(goal)
        
        if not is_extraction:
            return {"is_extraction": False}
        
        # Convert to the expected format for the plan generator
        return {
            "is_extraction": True,
            "format": extraction_details.get("format", "txt"),
            "target": extraction_details.get("goal", goal),
            "original_goal": goal,
            "needs_scrolling": extraction_details.get("needs_scrolling", False)
        }


if __name__ == '__main__':
    # This block can be used for testing, but is not part of the main application logic.
    pass