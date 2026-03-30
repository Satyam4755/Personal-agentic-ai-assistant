import re
from datetime import datetime

from assistant.agent_manager import AgentManager
from assistant.code_executor import CodeExecutor, run_last_generated_code
from assistant.gemini_brain import detect_intent, generate_assistant_response
from assistant.system_control import SystemControl


class CommandHandler:
    def __init__(self, agent_manager=None):
        self.agent_manager = agent_manager or AgentManager()
        self.system_control = SystemControl()
        self.code_executor = CodeExecutor(system_control=self.system_control)

    def handle_command(self, command):
        command = command.lower().strip()
        if any(word in command for word in ["bye", "exit", "quit", "goodbye"]):
            return "Goodbye Sir!", True

        command_lower = command

        if command_lower in ["voice off", "mute"]:
            from assistant.voice_engine import toggle_voice
            toggle_voice(False)
            return "Voice responses disabled.", False
            
        if command_lower in ["voice on", "unmute"]:
            from assistant.voice_engine import toggle_voice
            toggle_voice(True)
            return "Voice responses enabled.", False

        basic_commands = ["hello", "hi", "hey", "tum kaise ho", "kaise ho"]
        if command_lower in basic_commands:
            return self._handle_basic(command_lower)

        normalized_command = self.normalize(command)
        if not normalized_command:
            return "I did not catch that. Please try again.", False

        from assistant.memory_engine import handle_memory
        memory_response = handle_memory(command)
        if memory_response:
            return memory_response, False

        system_response = self.system_control.handle_command(command)
        if system_response:
            return system_response, False

        if any(word in command for word in [
            "run", "execute", "run it", "run code", "execute code", "terminal"
        ]):
            from assistant.state_manager import get_last_project
            import os
            
            project_path = get_last_project()
            if project_path:
                main_file = os.path.join(project_path, "main.py")
                app_file = os.path.join(project_path, "app.py")
                if os.path.exists(main_file):
                    os.system(f"python3 '{main_file}'")
                    return "Running main.py in latest project", False
                elif os.path.exists(app_file):
                    os.system(f"python3 '{app_file}'")
                    return "Running app.py in latest project", False
                else:
                    for f in os.listdir(project_path):
                        if f.endswith(".py"):
                            os.system(f"python3 '{os.path.join(project_path, f)}'")
                            return f"Running {f} in latest project", False
                    return "No executable python file found in the generated project.", False
            else:
                return run_last_generated_code(), False

        if self.code_executor.is_code_request(command):
            result = self.code_executor.execute_code_request(command)
            return result["message"], False

        datetime_response = self.handle_datetime_command(normalized_command)
        if datetime_response:
            return datetime_response, False

        gemini_intent = detect_intent(command)
        if gemini_intent["intent"] == "system_command":
            system_response = self.system_control.handle_command(command)
            if system_response:
                return system_response, False

        if gemini_intent["intent"] == "project_generation":
            result = self.code_executor.execute_code_request(command)
            return result["message"], False

        context_prompt = self.agent_manager.get_context_prompt(command)
        gemini_response = generate_assistant_response(command, context_prompt=context_prompt)
        return gemini_response or "Sorry, I am having trouble connecting right now.", False

    def _handle_basic(self, command):
        command = command.lower().strip()

        if command in ["hello", "hi", "hey"]:
            return "Hello sir, kaise hai aap", False

        if command in ["tum kaise ho", "kaise ho"]:
            return "Mai bhi badhiya hu sir, bataiye mai kaise apki madad karu", False

        return "Yes sir?", False

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
