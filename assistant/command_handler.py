import re
from datetime import datetime

from assistant.agent_manager import AgentManager
from assistant.gemini_brain import detect_intent, generate_assistant_response
from assistant.system_control import SystemControl


class CommandHandler:
    def __init__(self, agent_manager=None):
        self.agent_manager = agent_manager or AgentManager()
        self.system_control = SystemControl()

    def handle_command(self, command):
        normalized_command = self.normalize(command)
        if not normalized_command:
            return "I did not catch that. Please try again.", False

        if self._is_direct_exit_command(normalized_command):
            return "Goodbye! Have a nice day.", True

        system_response = self.system_control.handle_command(command)
        if system_response:
            return system_response, False

        if self.agent_manager.is_project_request(command):
            return self.agent_manager.handle_project_request(command), False

        datetime_response = self.handle_datetime_command(normalized_command)
        if datetime_response:
            return datetime_response, False

        gemini_intent = detect_intent(command)
        if gemini_intent["intent"] == "system_command":
            system_response = self.system_control.handle_command(command)
            if system_response:
                return system_response, False

        if gemini_intent["intent"] == "project_generation":
            return self.agent_manager.handle_project_request(command), False

        context_prompt = self.agent_manager.get_context_prompt(command)
        gemini_response = generate_assistant_response(command, context_prompt=context_prompt)
        return gemini_response or "Sorry, I am having trouble connecting right now.", False

    def normalize(self, text):
        normalized_text = text.lower().replace("’", "'")
        normalized_text = normalized_text.replace("'", " ")
        normalized_text = re.sub(r"[^\w\s]", " ", normalized_text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", normalized_text).strip()

    def _is_direct_exit_command(self, command):
        return command in {"exit", "quit", "goodbye", "good bye", "bye", "band karo", "बंद करो"}

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

    def _contains_phrase(self, command, phrase):
        return f" {phrase} " in f" {command} "
