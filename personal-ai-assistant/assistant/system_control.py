import os
import platform
import re
import shutil
import subprocess
import webbrowser


class SystemControl:
    def __init__(self):
        self.system_name = platform.system()

    def handle_command(self, command):
        command = command.lower().strip()

        if self._should_open_target(command, ("youtube",)):
            webbrowser.open("https://www.youtube.com")
            return "Opening YouTube."

        if self._should_open_target(command, ("calculator", "calc")):
            return self.open_calculator()

        if self._should_open_target(command, ("vs code", "visual studio code", "code editor")):
            return self.open_vs_code()

        if self._should_open_target(command, ("chrome", "google chrome")):
            return self.open_chrome()

        if self._should_open_target(command, ("google",)) and not self._contains_phrase(command, "chrome"):
            webbrowser.open("https://www.google.com")
            return "Opening Google."

        return None

    def open_calculator(self):
        if self.system_name == "Windows":
            subprocess.Popen(["calc.exe"])
            return "Opening Calculator."

        if self.system_name == "Darwin":
            subprocess.Popen(["open", "-a", "Calculator"])
            return "Opening Calculator."

        for command in (["gnome-calculator"], ["kcalc"], ["xcalc"]):
            if self._command_exists(command[0]):
                subprocess.Popen(command)
                return "Opening Calculator."

        return "Calculator application was not found on this computer."

    def open_vs_code(self):
        if self.system_name == "Windows":
            if self._command_exists("code"):
                subprocess.Popen(["code"])
                return "Opening Visual Studio Code."

            vscode_path = os.path.expandvars(
                r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe"
            )
            if os.path.exists(vscode_path):
                subprocess.Popen([vscode_path])
                return "Opening Visual Studio Code."

            return "Visual Studio Code was not found."

        if self.system_name == "Darwin":
            subprocess.Popen(["open", "-a", "Visual Studio Code"])
            return "Opening Visual Studio Code."

        for command in (["code"], ["codium"]):
            if self._command_exists(command[0]):
                subprocess.Popen(command)
                return "Opening Visual Studio Code."

        return "Visual Studio Code was not found."

    def open_chrome(self):
        if self.system_name == "Windows":
            chrome_path = os.path.expandvars(
                r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
            )
            chrome_path_x86 = os.path.expandvars(
                r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
            )

            if os.path.exists(chrome_path):
                subprocess.Popen([chrome_path])
                return "Opening Google Chrome."

            if os.path.exists(chrome_path_x86):
                subprocess.Popen([chrome_path_x86])
                return "Opening Google Chrome."

            if self._command_exists("chrome"):
                subprocess.Popen(["chrome"])
                return "Opening Google Chrome."

            return "Google Chrome was not found."

        if self.system_name == "Darwin":
            subprocess.Popen(["open", "-a", "Google Chrome"])
            return "Opening Google Chrome."

        for command in (["google-chrome"], ["chromium-browser"], ["chromium"]):
            if self._command_exists(command[0]):
                subprocess.Popen(command)
                return "Opening Google Chrome."

        return "Google Chrome was not found."

    def _command_exists(self, command_name):
        return shutil.which(command_name) is not None

    def _should_open_target(self, command, targets):
        has_action = any(
            self._contains_phrase(command, action)
            for action in ("open", "launch", "start", "run")
        )
        has_target = any(self._contains_phrase(command, target) for target in targets)
        return has_target and (has_action or command in targets)

    def _contains_phrase(self, command, phrase):
        pattern = rf"\b{re.escape(phrase)}\b"
        return re.search(pattern, command) is not None
