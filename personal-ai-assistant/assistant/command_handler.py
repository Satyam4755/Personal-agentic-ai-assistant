import json
import re
from datetime import datetime
from difflib import get_close_matches
from pathlib import Path

from assistant.code_executor import CodeExecutor
from assistant.gemini_brain import generate_response
from assistant.memory_manager import MemoryManager
from assistant.system_control import SystemControl


class CommandHandler:
    def __init__(self):
        project_root = Path(__file__).resolve().parent.parent
        responses_file = project_root / "data" / "basic_responses.json"
        memory_file = project_root / "memory" / "user_memory.json"

        self.responses = self.load_responses(responses_file)
        self.code_executor = CodeExecutor()
        self.memory_manager = MemoryManager(memory_file)
        self.system_control = SystemControl()
        self.fuzzy_commands = self._build_fuzzy_commands()

    def load_responses(self, responses_file):
        with Path(responses_file).open("r", encoding="utf-8") as file:
            return json.load(file)

    def handle_command(self, command, context_prompt=None):
        normalized_command = self.normalize(command)
        normalized_command = self.apply_fuzzy_match(normalized_command)

        if self._is_direct_exit_command(normalized_command):
            return "Goodbye! Have a nice day.", True

        if self.is_code_request(normalized_command):
            return self.code_executor.handle_code_request(command), False

        if self._is_code_execution_command(normalized_command):
            return self.code_executor.run_last_created_code(), False

        system_response = self.system_control.handle_command(normalized_command)
        if system_response:
            return system_response, False

        response, matched_trigger = self.match_basic_response(normalized_command)
        if response:
            return response, self._is_exit_trigger(normalized_command, matched_trigger)

        memory_response = self.memory_manager.process_memory_command(command)
        if memory_response:
            return memory_response, False

        memory_answer = self.memory_manager.answer_memory_question(normalized_command)
        if memory_answer:
            return memory_answer, False

        datetime_response = self.handle_datetime_command(normalized_command)
        if datetime_response:
            return datetime_response, False

        gemini_prompt = context_prompt or command
        gemini_response = generate_response(gemini_prompt)
        return gemini_response or "Sorry, I am having trouble connecting right now.", False

    def normalize(self, text):
        normalized_text = text.lower().replace("’", "'")
        normalized_text = normalized_text.replace("'", " ")
        normalized_text = re.sub(r"[^a-z0-9\s]", " ", normalized_text)

        replacements = {
            "what s": "what is",
            "whats": "what is",
            "who s": "who is",
            "i m": "i am",
        }

        for source_text, target_text in replacements.items():
            pattern = rf"\b{re.escape(source_text)}\b"
            normalized_text = re.sub(pattern, target_text, normalized_text)

        return re.sub(r"\s+", " ", normalized_text).strip()

    def apply_fuzzy_match(self, command):
        if not command or len(command.split()) > 5:
            return command

        candidate_commands = [
            known_command
            for known_command in self.fuzzy_commands
            if abs(len(known_command.split()) - len(command.split())) <= 2
        ]
        matched_commands = get_close_matches(command, candidate_commands, n=1, cutoff=0.75)
        if matched_commands:
            return matched_commands[0]

        return command

    def match_basic_response(self, command):
        for trigger_group, response in self.responses.items():
            for trigger in self._split_triggers(trigger_group):
                if self._contains_phrase(command, trigger):
                    return response, trigger

        return None, None

    def _split_triggers(self, trigger_group):
        return [trigger.strip().lower() for trigger in trigger_group.split("||") if trigger.strip()]

    def _build_fuzzy_commands(self):
        fuzzy_commands = {
            "what is my name",
            "what is my city",
            "where do i live",
            "open google",
            "open youtube",
            "open calculator",
            "open vs code",
            "open chrome",
            "what is the date",
            "what time is it",
            "date and time",
            "exit",
            "quit",
            "goodbye",
            "bye",
            "bye bye",
        }

        for trigger_group in self.responses:
            fuzzy_commands.update(self._split_triggers(trigger_group))

        return sorted(fuzzy_commands)

    def _contains_phrase(self, command, phrase):
        pattern = rf"\b{re.escape(phrase)}\b"
        return re.search(pattern, command) is not None

    def _is_exit_trigger(self, command, matched_trigger):
        exit_phrases = ("bye", "goodbye", "good bye", "bye bye", "exit", "quit")
        return self._contains_phrase(command, matched_trigger) and any(
            self._contains_phrase(command, phrase) for phrase in exit_phrases
        )

    def _is_direct_exit_command(self, command):
        return command in {"exit", "quit", "goodbye", "good bye", "bye"}

    def handle_datetime_command(self, command):
        now = datetime.now()

        if self._contains_any_phrase(command, ("date and time", "time and date")):
            return now.strftime("Right now it is %I:%M %p on %B %d, %Y.")

        if self._contains_any_phrase(
            command,
            ("today s date", "today date", "what is the date", "what is today s date", "date"),
        ):
            return now.strftime("Today's date is %B %d, %Y.")

        if self._contains_any_phrase(command, ("what time is it", "current time", "time")):
            return now.strftime("The current time is %I:%M %p.")

        return None

    def _contains_any_phrase(self, command, phrases):
        return any(self._contains_phrase(command, phrase) for phrase in phrases)

    def is_code_request(self, command):
        normalized_command = self.normalize(command)
        return self._is_code_generation_command(normalized_command)

    def _is_code_generation_command(self, command):
        creation_words = ("write", "create", "make", "generate")
        code_words = ("code", "program", "script", "file")
        language_words = (
            "python",
            "java",
            "javascript",
            "typescript",
            "c++",
            "cpp",
            "c#",
            "csharp",
            "go",
            "rust",
            "html",
            "css",
        )

        mentions_creation = any(self._contains_phrase(command, word) for word in creation_words)
        mentions_code = any(self._contains_phrase(command, word) for word in code_words)
        mentions_language = any(language in command for language in language_words)

        return (mentions_creation and mentions_code) or (mentions_code and mentions_language)

    def _is_code_execution_command(self, command):
        execution_phrases = (
            "run it",
            "run in terminal",
            "execute code",
            "run the code",
            "execute it",
        )
        return any(self._contains_phrase(command, phrase) for phrase in execution_phrases)
