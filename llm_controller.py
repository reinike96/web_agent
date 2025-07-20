import os
import re
import json
import logging
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

        # Setup logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        log_dir = os.path.dirname(__file__)
        log_file_path = os.path.join(log_dir, 'llm_interaction.log')
        file_handler = logging.FileHandler(log_file_path)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        if not self.logger.handlers: # Avoid adding multiple handlers if already initialized
            self.logger.addHandler(file_handler)
    def generate_action(self, goal: str, plan: list[str], completed_steps: set[int], page_summary: str) -> dict:
        """
        Generates a JSON command based on the user's goal, the plan, completed steps, and a summary of the current page.
        """
        system_prompt = """
        You are a highly intelligent AI agent that specializes in web automation.
        Based on the provided page summary, goal, and plan, generate the next action as a JSON object.
        Your response MUST be a single, valid JSON object and nothing else.

        Available Actions:
        - "click_element": Clicks an element. Requires "selector".
        - "enter_text": Enters text into a field. Requires "selector" and "text".
        - "navigate_to": Navigates to a URL. Requires "url".
        - "execute_script": Executes JavaScript for data extraction. Requires "script".

        Example Response:
        {"action": "click_element", "parameters": {"selector": "#my-button"}}
        """

        user_content = (
            f"Current Goal: '{goal}'\n\n"
            f"Overall Plan:\n{plan}\n\n"
            f"Completed Steps: {completed_steps}\n\n"
            f"Current Page Summary:\n---\n{page_summary}\n---"
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
        Return only the numbered list of steps, and nothing else.
        Keep the plan concise and to the point.
        If the user asks to download information, include a step for that.
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


    def needs_manual_intervention(self, page_context: str) -> str | None:
        """
        Checks if the page requires manual user intervention (e.g., CAPTCHA, cookie banner).
        Returns a message for the user if intervention is needed, otherwise None.
        """
        system_prompt = """
        You are an AI assistant that detects when a webpage requires CRITICAL manual user intervention.
        Your ONLY job is to identify CAPTCHA ("I'm not a robot") challenges and login forms.
        Do NOT flag cookie banners, notification pop-ups, or any other dismissible overlays.

        - If you see a CAPTCHA, respond with: "Please solve the CAPTCHA to continue."
        - If you see a login form that is blocking progress, respond with: "Please log in to continue."
        - Otherwise, and for all other pop-ups (like cookie banners), respond with "None".
        """

        user_prompt = f"""
        Simplified HTML of the current page:
        ---
        {page_context}
        ---

        Does this page require manual intervention? If so, what is the required action?
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
                # Removed max_tokens parameter
            )
            response = chat_completion.choices[0].message.content.strip()
            self.logger.info(f"Received from LLM (needs_manual_intervention):\n{response}")
            if "none" in response.lower():
                return None
            return response
        except Exception as e:
            print(f"Error checking for manual intervention: {e}")
            return None

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


if __name__ == '__main__':
    # This block can be used for testing, but is not part of the main application logic.
    pass
