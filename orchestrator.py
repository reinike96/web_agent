import time
import os
import re
from browser_controller import BrowserController
from perception import Perception
from llm_controller import LLMController
from memory import Memory
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

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
            print(f"--- Executing Step {i+1}: {task} ---")
            
            page_source = self.browser.get_page_source()
            perception = Perception(page_source)
            page_summary = perception.get_page_summary()

            # Think and get an action
            action = self.llm.generate_action(
                goal=f"Current Task: {task}",
                plan=self.plan,
                completed_steps=self.completed_steps,
                page_summary=page_summary
            )

            if not action or "action" not in action:
                print("LLM failed to provide a valid action. Skipping step.")
                continue

            action_name = action.get("action")
            if action_name == "skip":
                print("LLM decided to skip this step. Marking as complete.")
                self.completed_steps.add(i)
                continue
            
            # Execute the action
            print(f"Executing: {action}")
            execution_success = self.execute_action(action)
            self.memory.add_entry({"action": action, "step": i+1, "success": execution_success})

            if execution_success:
                print("Action executed successfully. Marking step as complete.")
                self.completed_steps.add(i)
            else:
                print(f"Action failed for step {i+1}. Moving to the next step.")

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
                return self.browser.click_element(**params)
            elif action_name == "enter_text":
                return self.browser.enter_text(**params)
            elif action_name == "navigate_to":
                self.browser.navigate_to(**params)
                return True # Navigation doesn't return a boolean
            elif action_name == "execute_script":
                self.browser.execute_script(**params)
                return True # Script execution doesn't inherently return success
            else:
                print(f"Unknown action: {action_name}")
                return False
        except Exception as e:
            print(f"Error executing action {action_name}: {e}")
            return False