import time
import os
from browser_controller import BrowserController
from perception import Perception
from llm_controller import LLMController
from memory import Memory
from manual_intervention import ManualInterventionDialog

class Orchestrator:
    """
    Manages the entire workflow of the web agent, including planning,
    perception, and execution of tasks.
    """
    def __init__(self, goal: str, message_callback: callable = None):
        """
        Initializes the orchestrator with a user-defined goal and an optional callback for messages.
        """
        self.goal = goal
        self.message_callback = message_callback
        self.browser = BrowserController()
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key or groq_api_key == "YOUR_API_KEY_HERE":
            raise ValueError("GROQ_API_KEY not found or not set.")
        self.llm = LLMController(api_key=groq_api_key)
        self.memory = Memory()
        self.manual_intervention = ManualInterventionDialog()
        self.plan = []
        self.completed_steps = set()

    def run(self):
        """Starts the agent's main execution loop, now using URL and title for verification."""
        if not self.browser.driver:
            print("Browser initialization failed. Aborting.")
            return

        print("Generating a plan...")
        self.plan = self.llm.generate_plan(self.goal)
        if not self.plan:
            print("Failed to generate a plan. Aborting.")
            return

        print("Plan generated:")
        for task in self.plan:
            print(f"- {task}")

        for i, task in enumerate(self.plan):
            max_retries = 3  # Maximum retries for failed steps
            retry_count = 0
            
            while retry_count <= max_retries:
                print(f"--- Executing Step {i+1}: {task} (Attempt {retry_count + 1}) ---")
                
                # Always get fresh page information before each attempt
                print("Extracting current page information...")
                page_source = self.browser.get_page_source()
                perception = Perception(page_source)
                page_summary = perception.get_page_summary()

                # Check if manual intervention is needed BEFORE trying to generate actions
                print("Checking if manual intervention is required...")
                
                # First, do a quick check if we're already logged in to common social platforms
                current_url = self.browser.get_current_url()
                if any(domain in current_url.lower() for domain in ["x.com", "twitter.com", "facebook.com", "instagram.com", "linkedin.com"]):
                    # Look for common logged-in indicators across social platforms
                    logged_in_indicators = [
                        'data-testid',                     # Common in modern web apps
                        'aria-label',                      # Accessibility labels for user actions
                        '[role="textbox"]',                # Text input areas
                        'contenteditable="true"',          # Rich text editors/composers
                        'navigation',                      # Navigation menus
                        'profile',                         # Profile-related elements
                        'compose',                         # Compose/create content buttons
                        'post',                           # Post/submit buttons
                        'timeline',                       # Content feeds
                        'menu'                            # User menus
                    ]
                    
                    page_source_lower = page_source.lower()
                    logged_in_detected = any(indicator.lower() in page_source_lower for indicator in logged_in_indicators)
                    
                    if logged_in_detected:
                        print("Detected user is already logged in to social platform. Skipping intervention check.")
                        intervention_result = {"requires_intervention": False, "type": "none", "message": ""}
                    else:
                        intervention_result = self.llm.needs_manual_intervention(page_summary)
                else:
                    intervention_result = self.llm.needs_manual_intervention(page_summary)
                
                if intervention_result.get("requires_intervention", False):
                    intervention_type = intervention_result.get("type", "unknown")
                    intervention_message = intervention_result.get("message", "Manual intervention required")
                    
                    print(f"Manual intervention detected: {intervention_message}")
                    
                    # Show popup and wait for user response
                    user_wants_to_continue = self.manual_intervention.show_intervention_popup(
                        intervention_message, intervention_type
                    )
                    
                    if user_wants_to_continue:
                        print("User completed manual intervention. Continuing with fresh page analysis...")
                        # After manual intervention, continue with fresh page information
                        continue  # This will restart the loop with fresh page data
                    else:
                        print("User chose to abort. Stopping automation.")
                        return

                # Think and get an action based on current page state
                action = self.llm.generate_action(
                    goal=f"Current Task: {task}",
                    plan=self.plan,
                    completed_steps=self.completed_steps,
                    page_summary=page_summary
                )

                if not action or "action" not in action:
                    print("LLM failed to provide a valid action. Skipping step.")
                    break

                action_name = action.get("action")
                if action_name == "skip":
                    print("LLM decided to skip this step. Marking as complete.")
                    self.completed_steps.add(i)
                    break
                
                # Execute the action
                print(f"Executing: {action}")
                execution_success = self.execute_action(action)
                self.memory.add_entry({"action": action, "step": i+1, "success": execution_success})

                # If action was successful, wait for page to update and re-extract info
                if execution_success:
                    print("Action executed successfully. Waiting for page updates...")
                    time.sleep(2)  # Give page time to update after action
                    
                    # Get fresh page information after successful action
                    print("Re-extracting page information after action...")
                    updated_page_source = self.browser.get_page_source()
                    updated_perception = Perception(updated_page_source)
                    verification_page_summary = updated_perception.get_page_summary()
                else:
                    verification_page_summary = page_summary  # Use original if action failed
                
                # Get current page info for verification
                page_title = self.browser.get_page_title()
                page_url = self.browser.get_current_url()
                
                # Verify step completion with updated information
                is_complete = self.llm.verify_step_completion(task, page_title, page_url, verification_page_summary)

                if is_complete:
                    print("Step verification successful. Marking as complete.")
                    self.completed_steps.add(i)
                    break
                else:
                    print(f"Step verification failed for step {i+1}.")
                    # Regular failure - increment retry count and try again
                    retry_count += 1
                    if retry_count <= max_retries:
                        print(f"Retrying step {i+1} (attempt {retry_count + 1})...")
                    else:
                        print(f"Step {i+1} failed after {max_retries} attempts. Moving to next step.")
                        break

        completion_message = "--- All Tasks Completed ---"
        print(completion_message)
        if self.message_callback:
            self.message_callback(completion_message)

    def execute_action(self, action: dict) -> bool:
        """Executes the generated action safely and returns success status."""
        action_name = action.get("action")
        params = action.get("parameters", {})

        if not action_name:
            print("No action specified.")
            return False

        try:
            if action_name == "click_element":
                selector = params.get("selector", "")
                success = self.browser.click_element(selector)
                
                # If main selector fails, try alternative selectors
                if not success and selector:
                    print(f"Main selector failed: {selector}. Trying alternatives...")
                    page_source = self.browser.get_page_source()
                    perception = Perception(page_source)
                    page_summary = perception.get_page_summary()
                    
                    alternative_selectors = self.llm.generate_alternative_selectors(
                        selector, action_name, page_summary
                    )
                    
                    for alt_selector in alternative_selectors:
                        print(f"Trying alternative selector: {alt_selector}")
                        success = self.browser.click_element(alt_selector)
                        if success:
                            print(f"Success with alternative selector: {alt_selector}")
                            break
                
                return success
                
            elif action_name == "enter_text":
                selector = params.get("selector", "")
                text = params.get("text", "")
                success = self.browser.enter_text(selector, text, press_enter=True)
                
                # If main selector fails, try alternative selectors
                if not success and selector:
                    print(f"Main selector failed: {selector}. Trying alternatives...")
                    page_source = self.browser.get_page_source()
                    perception = Perception(page_source)
                    page_summary = perception.get_page_summary()
                    
                    alternative_selectors = self.llm.generate_alternative_selectors(
                        selector, action_name, page_summary
                    )
                    
                    for alt_selector in alternative_selectors:
                        print(f"Trying alternative selector: {alt_selector}")
                        success = self.browser.enter_text(alt_selector, text, press_enter=True)
                        if success:
                            print(f"Success with alternative selector: {alt_selector}")
                            break
                
                return success

            elif action_name == "enter_text_no_enter":
                selector = params.get("selector", "")
                text = params.get("text", "")
                success = self.browser.enter_text_without_enter(selector, text)
                
                # If main selector fails, try alternative selectors
                if not success and selector:
                    print(f"Main selector failed: {selector}. Trying alternatives...")
                    page_source = self.browser.get_page_source()
                    perception = Perception(page_source)
                    page_summary = perception.get_page_summary()
                    
                    alternative_selectors = self.llm.generate_alternative_selectors(
                        selector, action_name, page_summary
                    )
                    
                    for alt_selector in alternative_selectors:
                        print(f"Trying alternative selector: {alt_selector}")
                        success = self.browser.enter_text_without_enter(alt_selector, text)
                        if success:
                            print(f"Success with alternative selector: {alt_selector}")
                            break
                
                return success
                
            elif action_name == "navigate_to":
                url = params.get("url", "")
                self.browser.navigate_to(url)
                return True
                
            elif action_name == "execute_script":
                script = params.get("script", "")
                result = self.browser.execute_script(script)
                return result is not None
                
            elif action_name == "wait":
                seconds = params.get("seconds", 1)
                time.sleep(seconds)
                return True
                
            elif action_name == "scroll":
                direction = params.get("direction", "down")
                pixels = params.get("pixels", 300)
                if direction == "down":
                    script = f"window.scrollBy(0, {pixels});"
                else:
                    script = f"window.scrollBy(0, -{pixels});"
                self.browser.execute_script(script)
                return True
            else:
                print(f"Unknown action: {action_name}")
                return False
        except Exception as e:
            print(f"Error executing action {action_name}: {e}")
            return False