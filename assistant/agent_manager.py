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
        from assistant.memory_engine import get_memory_context
        memory_context = get_memory_context()
        
        return (
            "Previous context:\n"
            f"{memory_context}\n\n"
            "Current request:\n"
            f"{new_command.strip()}\n\n"
            "Respond accordingly and continue the previous task if relevant."
        )
