import json
from pathlib import Path

from assistant.code_executor import CodeExecutor
from assistant.gemini_brain import generate_response
from assistant.memory_manager import MemoryManager
from assistant.system_control import SystemControl


class CommandHandler:
    def __init__(self):
        project_root = Path(__file__).resolve().parent.parent
        self.responses = self._load_responses(project_root / "data" / "basic_responses.json")
        self.memory_manager = MemoryManager(project_root / "memory" / "user_memory.json")
        self.system_control = SystemControl()
        self.code_executor = CodeExecutor()

    def handle(self, command):
        cleaned_command = command.strip().lower()
        if not cleaned_command:
            return "Please say that again.", False

        if cleaned_command in {"bye", "goodbye", "exit", "quit"}:
            return "Goodbye!", True

        if self._is_code_command(cleaned_command):
            return self.code_executor.handle_code_request(command), False

        if self._is_run_code_command(cleaned_command):
            return self.code_executor.run_last_created_code(), False

        system_response = self.system_control.handle_command(cleaned_command)
        if system_response:
            return system_response, False

        memory_response = self.memory_manager.process_memory_command(command)
        if memory_response:
            return memory_response, False

        memory_answer = self.memory_manager.answer_memory_question(cleaned_command)
        if memory_answer:
            return memory_answer, False

        basic_response = self._get_basic_response(cleaned_command)
        if basic_response:
            return basic_response, False

        return generate_response(command), False

    def handle_command(self, command, context_prompt=None):
        return self.handle(command)

    def _load_responses(self, path):
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _get_basic_response(self, command):
        for key, value in self.responses.items():
            triggers = [item.strip().lower() for item in key.split("||")]
            for trigger in triggers:
                if trigger and trigger in command:
                    return value
        return None

    def _is_code_command(self, command):
        code_words = ("code", "program", "script")
        action_words = ("write", "create", "generate", "make")
        return any(word in command for word in code_words) and any(
            word in command for word in action_words
        )

    def _is_run_code_command(self, command):
        return "run file" in command or "run code" in command or command == "run it"
