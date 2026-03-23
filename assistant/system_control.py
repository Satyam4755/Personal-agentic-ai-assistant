import platform
import re
import shutil
import subprocess


class SystemControl:
    ACTION_WORDS = (
        "open",
        "launch",
        "start",
        "run",
        "khol",
        "kholo",
        "khol do",
        "open karo",
        "chalu karo",
        "चलाओ",
        "खोल",
        "खोलो",
        "खोल दो",
    )

    TARGET_ALIASES = {
        "youtube": ("youtube", "yt", "यूट्यूब"),
        "google": ("google", "गूगल"),
        "vscode": ("vscode", "vs code", "visual studio code", "code editor"),
        "calculator": ("calculator", "calc", "कैलकुलेटर"),
    }

    def __init__(self):
        self.system_name = platform.system()

    def handle_command(self, command):
        normalized_command = self.normalize(command)
        if not self._has_action(normalized_command):
            return None

        if self._mentions_target(normalized_command, "youtube"):
            self._open_url("https://www.youtube.com")
            return "Opening YouTube."

        if self._mentions_target(normalized_command, "google"):
            self._open_url("https://www.google.com")
            return "Opening Google."

        if self._mentions_target(normalized_command, "vscode"):
            return self.open_vs_code()

        if self._mentions_target(normalized_command, "calculator"):
            return self.open_calculator()

        return None

    def open_calculator(self):
        if self.system_name == "Darwin":
            subprocess.Popen(["open", "-a", "Calculator"])
            return "Opening Calculator."

        if self.system_name == "Windows":
            subprocess.Popen(["calc.exe"])
            return "Opening Calculator."

        for command in (["gnome-calculator"], ["kcalc"], ["xcalc"]):
            if self._command_exists(command[0]):
                subprocess.Popen(command)
                return "Opening Calculator."

        return "Calculator application was not found on this computer."

    def open_vs_code(self):
        if self.system_name == "Darwin":
            if self._command_exists("code"):
                subprocess.Popen(["code"])
                return "Opening Visual Studio Code."

            subprocess.Popen(["open", "-a", "Visual Studio Code"])
            return "Opening Visual Studio Code."

        if self.system_name == "Windows":
            for command in (["code"], ["Code.exe"]):
                if self._command_exists(command[0]):
                    subprocess.Popen(command)
                    return "Opening Visual Studio Code."

            return "Visual Studio Code was not found."

        for command in (["code"], ["codium"]):
            if self._command_exists(command[0]):
                subprocess.Popen(command)
                return "Opening Visual Studio Code."

        return "Visual Studio Code was not found."

    def normalize(self, text):
        lowered_text = text.lower().replace("v s code", "vs code")
        lowered_text = re.sub(r"[^\w\s]", " ", lowered_text, flags=re.UNICODE)
        return " ".join(lowered_text.split())

    def _open_url(self, url):
        if self.system_name == "Darwin":
            subprocess.Popen(["open", url])
            return

        if self.system_name == "Windows":
            subprocess.Popen(["cmd", "/c", "start", "", url])
            return

        subprocess.Popen(["xdg-open", url])

    def _command_exists(self, command_name):
        return shutil.which(command_name) is not None

    def _has_action(self, command):
        return any(self._contains_phrase(command, action) for action in self.ACTION_WORDS)

    def _mentions_target(self, command, target):
        aliases = self.TARGET_ALIASES.get(target, ())
        return any(self._contains_phrase(command, alias) for alias in aliases)

    def _contains_phrase(self, command, phrase):
        return f" {phrase} " in f" {command} "
