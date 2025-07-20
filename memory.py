
class Memory:
    """
    Stores the history of actions, observations, and other relevant
    information for the agent.
    """
    def __init__(self):
        """Initializes the memory."""
        self.history = []

    def add_entry(self, entry: dict):
        """
        Adds a new entry to the memory.
        An entry can be an action, observation, or error.
        """
        self.history.append(entry)

    def get_full_history(self) -> list[dict]:
        """Returns the full history of the agent."""
        return self.history

    def get_recent_history(self, n: int = 5) -> list[dict]:
        """Returns the last n entries from the history."""
        return self.history[-n:]
