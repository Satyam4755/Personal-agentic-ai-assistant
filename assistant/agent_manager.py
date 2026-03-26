class AgentManager:
    def __init__(self):
        self.context_history = []

    def remember_context(self, command):
        cleaned_command = command.strip()
        if not cleaned_command:
            return

        self.context_history.append(cleaned_command)
        if len(self.context_history) > 50:
            self.context_history = self.context_history[-50:]

    def get_context_prompt(self, new_command):
        history_items = self.context_history[-5:]
        if history_items and history_items[-1] == new_command.strip():
            history_items = history_items[:-1]

        history = "\n".join(f"- {item}" for item in history_items) or "- No previous context"
        return (
            "Previous context:\n"
            f"{history}\n\n"
            "Current request:\n"
            f"{new_command.strip()}\n\n"
            "Respond accordingly and continue the previous task if relevant."
        )
