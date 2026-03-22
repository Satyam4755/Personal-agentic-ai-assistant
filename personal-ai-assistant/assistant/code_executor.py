import platform
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path

from assistant.gemini_brain import generate_code
from assistant.state_manager import StateManager


LAST_CREATED_FILE_PATH = None


class CodeExecutor:
    def __init__(self):
        self.base_path = Path.home() / "Desktop" / "AI_Projects"
        self.system_name = platform.system()
        self.state_manager = StateManager()
        stored_file = self.state_manager.get("last_generated_file")
        self.last_generated_file = Path(stored_file) if stored_file else None

    def generate_and_run_code(self, prompt):
        print("Code agent triggered.")
        task = self._extract_task(prompt)
        print(f"Code agent task: {task}")
        code = generate_code(task, language="python")

        if not code:
            print("Code agent error: Gemini did not return Python code.")
            return "I could not generate Python code right now."

        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            print(f"Code agent base folder ready: {self.base_path}")
            folder_path = self._build_project_folder(task)
            folder_path.mkdir(parents=True, exist_ok=False)
            print(f"Project folder created at: {folder_path}")

            file_path = folder_path / "main.py"
            file_path.write_text(code, encoding="utf-8")
            print(f"Python file written to: {file_path}")
            self._set_last_created_file_path(file_path)
        except OSError as error:
            print(f"Code executor error: {error}")
            return "I could not create the project files."

        self._open_in_vs_code(folder_path)
        self._run_python_file(file_path)

        return f"Code created and executed successfully in {folder_path.name}."

    def handle_code_request(self, prompt):
        language = self._detect_language(prompt)
        if language == "python":
            return self.generate_and_run_code(prompt)

        return self.generate_source_file(prompt, language)

    def generate_source_file(self, prompt, language):
        print("Code agent triggered.")
        task = self._extract_task(prompt, language=language)
        print(f"Code agent task: {task}")
        code = generate_code(task, language=language)

        if not code:
            print(f"Code agent error: Gemini did not return {language} code.")
            return f"I could not generate {language.capitalize()} code right now."

        file_name = self._build_file_name(language)

        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            print(f"Code agent base folder ready: {self.base_path}")
            folder_path = self._build_project_folder(task)
            folder_path.mkdir(parents=True, exist_ok=False)
            print(f"Project folder created at: {folder_path}")

            file_path = folder_path / file_name
            file_path.write_text(code, encoding="utf-8")
            print(f"Source file written to: {file_path}")
            self._set_last_created_file_path(file_path)
        except OSError as error:
            print(f"Code executor error: {error}")
            return "I could not create the project files."

        self._open_in_vs_code(folder_path)
        return f"{language.capitalize()} code created successfully in {folder_path.name}."

    def run_last_created_code(self):
        file_path = self.get_last_created_file_path()
        if file_path is None:
            print("Code agent warning: No generated Python file is available to run.")
            return "I do not have a generated Python file to run yet."

        if not file_path.exists():
            print(f"Code agent warning: Last generated file is missing: {file_path}")
            return "I could not find the last generated Python file."

        self.run_in_terminal(file_path)
        return "Running your code in terminal."

    def _extract_task(self, prompt, language="python"):
        normalized_prompt = " ".join(prompt.strip().split())
        language_pattern = re.escape(language)
        match = re.search(
            rf"\b(?:write|create|make|generate)\s+(?:a\s+)?{language_pattern}\s+"
            r"(?:code|program|script|file)\s*(?:for|of|to)?\s*(.+)",
            normalized_prompt,
            re.IGNORECASE,
        )

        if match:
            task = match.group(1).strip()
        else:
            task = normalized_prompt

        task = re.sub(
            r"\s+(?:in|inside|using|on)\s+(?:vs\s*code|visual\s+studio\s+code)\b.*$",
            "",
            task,
            flags=re.IGNORECASE,
        )
        task = re.sub(r"\s+", " ", task).strip(" .")

        return task or f"simple {language} project"

    def _build_project_folder(self, task):
        slug = self._slugify_task(task)
        timestamp = int(time.time())
        return self.base_path / f"{slug}_project_{timestamp}"

    def _slugify_task(self, task):
        cleaned_task = re.sub(r"[^a-zA-Z0-9\s]", "", task.lower())
        words = [word for word in cleaned_task.split() if word]

        if not words:
            return "python"

        return "_".join(words[:4])

    def _detect_language(self, prompt):
        normalized_prompt = prompt.lower()
        language_keywords = (
            "python",
            "java",
            "javascript",
            "typescript",
            "c++",
            "cpp",
            "c",
            "c#",
            "csharp",
            "go",
            "rust",
            "html",
            "css",
        )

        for language in language_keywords:
            if language in normalized_prompt:
                if language == "cpp":
                    return "c++"
                if language == "csharp":
                    return "c#"
                return language

        return "python"

    def _build_file_name(self, language):
        file_names = {
            "python": "main.py",
            "java": "Main.java",
            "javascript": "main.js",
            "typescript": "main.ts",
            "c++": "main.cpp",
            "c": "main.c",
            "c#": "Program.cs",
            "go": "main.go",
            "rust": "main.rs",
            "html": "index.html",
            "css": "styles.css",
        }
        return file_names.get(language, "main.txt")

    def _open_in_vs_code(self, folder_path):
        folder_str = str(folder_path)

        try:
            if shutil.which("code"):
                print(f"Launching VS Code with: code {folder_str}")
                subprocess.Popen(["code", folder_str])
                return

            if self.system_name == "Darwin":
                print(f"Launching VS Code with macOS open command for: {folder_str}")
                subprocess.Popen(["open", "-a", "Visual Studio Code", folder_str])
                return

            if self.system_name == "Windows":
                print(f"Launching folder on Windows for: {folder_str}")
                subprocess.Popen(["cmd", "/c", "start", "", folder_str])
                return

            if shutil.which("xdg-open"):
                print(f"Launching folder with xdg-open: {folder_str}")
                subprocess.Popen(["xdg-open", folder_str])
                return

            print("Code agent warning: VS Code command was not found.")
        except OSError as error:
            print(f"Code executor error opening editor: {error}")

    def _run_python_file(self, file_path):
        self.run_in_terminal(file_path)

    def run_in_terminal(self, file_path):
        try:
            print(f"Running Python file: {file_path}")

            if self.system_name == "Darwin":
                terminal_command = f"python3 {shlex.quote(str(file_path))}"
                escaped_command = terminal_command.replace("\\", "\\\\").replace('"', '\\"')
                apple_script = f'tell application "Terminal" to do script "{escaped_command}"'
                print(f"Launching Terminal with: {terminal_command}")
                subprocess.Popen(["osascript", "-e", apple_script])
                return

            subprocess.Popen(["python3", str(file_path)])
        except OSError as error:
            print(f"Code executor error running file: {error}")

    def _set_last_created_file_path(self, file_path):
        global LAST_CREATED_FILE_PATH
        self.last_generated_file = Path(file_path)
        LAST_CREATED_FILE_PATH = self.last_generated_file
        self.state_manager.set("last_generated_file", str(self.last_generated_file))
        print(f"Last generated file stored as: {LAST_CREATED_FILE_PATH}")

    def get_last_created_file_path(self):
        if self.last_generated_file is not None:
            return Path(self.last_generated_file)

        stored_file = self.state_manager.get("last_generated_file")
        if stored_file:
            self.last_generated_file = Path(stored_file)
            return self.last_generated_file

        if LAST_CREATED_FILE_PATH is None:
            return None

        return Path(LAST_CREATED_FILE_PATH)
