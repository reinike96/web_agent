import tkinter as tk
from tkinter import messagebox
import threading

class ManualInterventionDialog:
    """
    Creates a popup dialog to request manual user intervention when CAPTCHA or login is detected.
    """
    
    def __init__(self):
        self.user_response = None
        self.dialog_completed = threading.Event()

    def show_intervention_popup(self, message: str, intervention_type: str) -> bool:
        """
        Shows a popup requesting manual intervention.
        
        Args:
            message: The message to display to the user
            intervention_type: Type of intervention ("captcha" or "login")
            
        Returns:
            bool: True if user wants to continue, False if user wants to abort
        """
        self.user_response = None
        self.dialog_completed.clear()
        
        # Create the popup in a separate thread to avoid blocking
        popup_thread = threading.Thread(target=self._create_popup, args=(message, intervention_type))
        popup_thread.daemon = True
        popup_thread.start()
        
        # Wait for user response
        self.dialog_completed.wait()
        
        return self.user_response

    def _create_popup(self, message: str, intervention_type: str):
        """Creates and displays the popup dialog."""
        try:
            # Create the main window
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            
            # Prepare the dialog message
            title = "Manual Intervention Required"
            if intervention_type == "captcha":
                full_message = (
                    f"{message}\n\n"
                    "A CAPTCHA has been detected on the current page. "
                    "Please solve it manually in the browser window and then click 'Continue' to proceed.\n\n"
                    "Click 'Continue' when you have completed the CAPTCHA.\n"
                    "Click 'Abort' to stop the automation process."
                )
            elif intervention_type == "login":
                full_message = (
                    f"{message}\n\n"
                    "A login form has been detected that is blocking automation progress. "
                    "Please log in manually in the browser window and then click 'Continue' to proceed.\n\n"
                    "Click 'Continue' when you have logged in.\n"
                    "Click 'Abort' to stop the automation process."
                )
            else:
                full_message = (
                    f"{message}\n\n"
                    "Manual intervention is required. Please complete the required action "
                    "in the browser window and then click 'Continue' to proceed.\n\n"
                    "Click 'Continue' when you have completed the required action.\n"
                    "Click 'Abort' to stop the automation process."
                )
            
            # Show the message box with Yes/No options
            result = messagebox.askyesno(
                title,
                full_message,
                icon='warning'
            )
            
            self.user_response = result
            self.dialog_completed.set()
            
            root.destroy()
            
        except Exception as e:
            print(f"Error creating intervention popup: {e}")
            self.user_response = False
            self.dialog_completed.set()

    def show_simple_message(self, message: str, title: str = "Web Agent"):
        """Shows a simple informational message."""
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(title, message)
            root.destroy()
        except Exception as e:
            print(f"Error showing message: {e}")


# Test the dialog if run directly
if __name__ == "__main__":
    dialog = ManualInterventionDialog()
    
    # Test CAPTCHA dialog
    result = dialog.show_intervention_popup(
        "CAPTCHA detected - manual intervention required",
        "captcha"
    )
    print(f"User response: {result}")
    
    # Test login dialog
    result = dialog.show_intervention_popup(
        "Login required - manual intervention required", 
        "login"
    )
    print(f"User response: {result}")
