import time
import os
from typing import Dict, List
from browser_controller import BrowserController
from page_analyzer import PageAnalyzer
from llm_controller import LLMController
from memory import Memory
from manual_intervention import ManualInterventionDialog

class NewOrchestrator:
    """            elif action_name == "click_element":
                selector = params.get("selector", "")
                return self.browser.click_element(selector)
            
            elif action_name == "click_button":
                # General action to click relevant buttons using JSON data
                keywords = params.get("keywords", None)  # Optional: specific keywords to search for
                page_info = self.page_analyzer.get_comprehensive_page_info()
                return self.browser.click_button_from_json(page_info, keywords)  New orchestrator with improved architecture based on JavaScript extraction and robust validation.
    """
    
    def __init__(self, goal: str, message_callback: callable = None):
        self.goal = goal
        self.message_callback = message_callback
        self.browser = BrowserController()
        
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key or groq_api_key == "YOUR_API_KEY_HERE":
            raise ValueError("GROQ_API_KEY not found or not set.")
        
        self.llm = LLMController(api_key=groq_api_key)
        self.page_analyzer = PageAnalyzer(self.browser, self.llm)  # Pass LLM to PageAnalyzer
        self.memory = Memory()
        self.manual_intervention = ManualInterventionDialog()
        
        self.plan = []
        self.completed_steps = []
        self.current_step_index = 0
        
    def run(self):
        """Main execution loop with the new architecture."""
        if not self.browser.driver:
            print("Browser initialization failed. Aborting.")
            return

        print("Generating initial plan...")
        self.plan = self.llm.generate_plan(self.goal)
        if not self.plan:
            print("Failed to generate a plan. Aborting.")
            return

        print("Plan generated:")
        for i, task in enumerate(self.plan):
            print(f"{i+1}. {task}")

        while self.current_step_index < len(self.plan):
            current_task = self.plan[self.current_step_index]
            
            print(f"\n--- Executing Step {self.current_step_index + 1}: {current_task} ---")
            
            success = self.execute_step_with_retries(current_task)
            
            if success:
                print(f"[OK] Step {self.current_step_index + 1} completed successfully!")
                self.completed_steps.append(current_task)
                self.current_step_index += 1
            else:
                print(f"[ERROR] Step {self.current_step_index + 1} failed after all retries.")
                # Try alternative plan
                if self.try_alternative_approach():
                    continue
                else:
                    print("Failed to find alternative approach. Aborting.")
                    break

        completion_message = "--- All Tasks Completed ---"
        print(completion_message)
        if self.message_callback:
            self.message_callback(completion_message)

    def is_verification_step(self, task: str) -> bool:
        """Check if a task is a verification step."""
        # Remove leading numbers and dots, then check for VERIFY
        clean_task = task.strip()
        # Remove pattern like "6. " from the beginning
        import re
        clean_task = re.sub(r'^\d+\.\s*', '', clean_task)
        return clean_task.upper().startswith("VERIFY:")

    def requires_post_action_verification(self, action: dict) -> bool:
        """
        Determine if an action requires post-execution verification.
        Text entry and button clicks are successful if they execute without errors.
        Only verify actions that navigate or significantly change page state.
        """
        action_type = action.get('action', '')
        
        # Actions that DON'T need verification (assume success if executed without error)
        simple_actions = {
            'enter_text_no_enter',  # Text entry is successful if no errors
            'enter_text',           # Text entry + enter is successful if no errors
            'click_element',        # Button clicks are successful if no errors
            'click_button',         # Button clicks are successful if no errors
            'wait',                 # Wait actions always work
            'scroll'                # Scroll actions always work
        }
        
        # Actions that DO need verification (cause significant page changes)
        verification_needed_actions = {
            'navigate_to'           # Navigation should be verified
        }
        
        if action_type in simple_actions:
            return False
        elif action_type in verification_needed_actions:
            return True
        else:
            # Unknown action - err on the side of caution
            return True

    def execute_verification_step(self, task: str) -> bool:
        """Execute a verification step using LLM-generated JavaScript."""
        # Extract the verification requirement
        verification_text = task.replace("VERIFY:", "").strip()
        
        print(f"Executing verification: {verification_text}")
        
        # Use PageAnalyzer to verify the condition
        verification_result = self.page_analyzer.verify_page_condition(
            verification_requirement=verification_text,
            context=f"Current goal: {self.goal}"
        )
        
        print(f"Verification result: {verification_result}")
        
        if verification_result.get("verified", False):
            print(f"[OK] Verification passed: {verification_text}")
            return True
        else:
            print(f"[ERROR] Verification failed: {verification_result.get('reason', 'Unknown reason')}")
            return False

    def execute_step_with_retries(self, task: str) -> bool:
        """Execute a step with 3 progressive retry strategies."""
        
        # Check if this is a verification step
        if self.is_verification_step(task):
            return self.execute_verification_step(task)
        
        max_attempts = 3
        
        for attempt in range(1, max_attempts + 1):
            print(f"Attempt {attempt}/{max_attempts} for current step...")
            
            # Extract current page information
            print("Extracting page information...")
            page_info_before = self.page_analyzer.get_comprehensive_page_info()
            
            # Enhanced intervention check with detailed logging
            intervention_check = self.page_analyzer.detect_login_or_captcha(page_info_before)
            
            print(f"Intervention check result: {intervention_check.get('message', 'No message')}")
            
            if intervention_check.get("requires_intervention", False):
                print(f"Details: {intervention_check.get('details', 'No details')}")
                if not self.handle_manual_intervention(intervention_check):
                    return False
                # Re-extract page info after intervention
                print("Re-extracting page information after manual intervention...")
                page_info_before = self.page_analyzer.get_comprehensive_page_info()
                
                # Double-check intervention after user action
                recheck = self.page_analyzer.detect_login_or_captcha(page_info_before)
                if recheck.get("requires_intervention", False):
                    print("Still requires intervention after user action. User may need more time.")
                    # Give user another chance or abort
                    if not self.handle_manual_intervention(recheck):
                        return False
                    page_info_before = self.page_analyzer.get_comprehensive_page_info()
            
            # Generate action based on attempt strategy
            if attempt == 1:
                # Normal approach
                action = self.generate_normal_action(task, page_info_before)
            elif attempt == 2:
                # Alternative selector approach
                action = self.generate_alternative_action(task, page_info_before)
            else:
                # Creative approach - let LLM decide completely
                action = self.generate_creative_action(task, page_info_before)
            
            if not action:
                print(f"Failed to generate action for attempt {attempt}")
                continue
            
            print(f"Executing action: {action}")
            
            # Execute the action
            execution_success = self.execute_action(action)
            if not execution_success:
                print(f"Action execution failed on attempt {attempt}")
                continue
            
            # Check if this action needs post-execution verification
            if self.requires_post_action_verification(action):
                print("This action requires verification, waiting for page updates...")
                time.sleep(2)
                
                # Extract page info after action
                page_info_after = self.page_analyzer.get_comprehensive_page_info()
                
                # Verify step completion
                is_complete = self.llm.verify_step_completion_with_page_info(
                    task, page_info_before, page_info_after
                )
                
                if is_complete:
                    print(f"Step verification successful on attempt {attempt}!")
                    return True
                else:
                    print(f"Step verification failed on attempt {attempt}")
            else:
                print(f"Action completed successfully on attempt {attempt} (no verification needed)")
                return True
            
            if is_complete:
                print(f"Step verification successful on attempt {attempt}!")
                return True
            else:
                print(f"Step verification failed on attempt {attempt}")
        
        return False

    def generate_normal_action(self, task: str, page_info: Dict) -> Dict:
        """Generate action using normal approach."""
        remaining_steps = self.plan[self.current_step_index:]
        return self.llm.generate_action_from_page_info(
            self.goal, remaining_steps, self.completed_steps, page_info
        )

    def generate_alternative_action(self, task: str, page_info: Dict) -> Dict:
        """Generate action using alternative selectors."""
        # For now, this is the same as normal, but could be enhanced
        # to specifically request alternative approaches
        remaining_steps = self.plan[self.current_step_index:]
        return self.llm.generate_action_from_page_info(
            f"ALTERNATIVE APPROACH: {self.goal}", remaining_steps, self.completed_steps, page_info
        )

    def generate_creative_action(self, task: str, page_info: Dict) -> Dict:
        """Generate action using creative/desperate approach."""
        # Get additional context with page structure
        page_structure = self.page_analyzer.get_page_structure()
        
        # Combine both info types for maximum context
        enhanced_page_info = page_info.copy()
        enhanced_page_info["additional_structure"] = page_structure
        
        remaining_steps = self.plan[self.current_step_index:]
        return self.llm.generate_action_from_page_info(
            f"CREATIVE APPROACH - USE ANY MEANS: {self.goal}", 
            remaining_steps, self.completed_steps, enhanced_page_info
        )

    def try_alternative_approach(self) -> bool:
        """Try to generate an alternative plan when current approach fails."""
        print("Attempting to generate alternative plan...")
        
        current_page_info = self.page_analyzer.get_comprehensive_page_info()
        failed_steps = self.plan[self.current_step_index:]
        
        alternative_plan = self.llm.generate_alternative_plan(
            self.goal, failed_steps, current_page_info
        )
        
        if alternative_plan:
            print("Alternative plan generated:")
            for i, step in enumerate(alternative_plan):
                print(f"{i+1}. {step}")
            
            # Replace remaining steps with alternative plan
            self.plan = self.completed_steps + alternative_plan
            self.current_step_index = len(self.completed_steps)
            return True
        
        return False

    def handle_manual_intervention(self, intervention_info: Dict) -> bool:
        """Handle manual intervention when needed."""
        intervention_type = intervention_info.get("type", "unknown")
        intervention_message = intervention_info.get("message", "Manual intervention required")
        
        print(f"Manual intervention detected: {intervention_message}")
        
        user_wants_to_continue = self.manual_intervention.show_intervention_popup(
            intervention_message, intervention_type
        )
        
        if user_wants_to_continue:
            print("User completed manual intervention. Continuing...")
            return True
        else:
            print("User chose to abort. Stopping automation.")
            return False

    def execute_action(self, action: Dict) -> bool:
        """Execute a given action and return success status."""
        action_name = action.get("action")
        params = action.get("parameters", {})

        if not action_name:
            print("No action specified.")
            return False

        try:
            if action_name == "click_element":
                selector = params.get("selector", "")
                return self.browser.click_element(selector)
                
            elif action_name == "enter_text":
                selector = params.get("selector", "")
                text = params.get("text", "")
                return self.browser.enter_text(selector, text, press_enter=True)

            elif action_name == "enter_text_no_enter":
                selector = params.get("selector", "")
                text = params.get("text", "")
                success = self.browser.enter_text_without_enter(selector, text)
                
                # For contenteditable elements, verify the content was accepted
                if success:
                    print("Verifying that the text input was detected properly...")
                    # Small delay to allow page to process the input
                    time.sleep(1)
                    # Note: Post-action verification will be handled by the verification system if needed
                
                return success
                
            elif action_name == "navigate_to":
                url = params.get("url", "")
                self.browser.navigate_to(url)
                return True
                
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
