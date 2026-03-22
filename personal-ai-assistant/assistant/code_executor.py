import os
import re
import shlex
import time
from pathlib import Path

from assistant.gemini_brain import generate_code
from assistant.state_manager import StateManager


class CodeExecutor:
    def __init__(self):
        self.base_path = Path.home() / "Desktop" / "AI_Projects"
        self.state_manager = StateManager()
        stored_file = self.state_manager.get("last_generated_file")
        self.last_generated_file = Path(stored_file) if stored_file else None

    def handle_code_request(self, command):
        code = generate_code(command)
        if not code:
            return "I could not generate code right now."

        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            project_folder = self.base_path / f"generated_code_{int(time.time())}"
            project_folder.mkdir(parents=True, exist_ok=True)

            file_path = project_folder / "main.py"
            file_path.write_text(code, encoding="utf-8")
            self.last_generated_file = file_path
            self.state_manager.set("last_generated_file", str(file_path))
        except OSError as error:
            print("Code executor error:", error)
            return "I could not save the generated code."

        os.system(f"python3 {shlex.quote(str(file_path))}")
        return f"Code saved to {file_path} and executed."

    def run_last_created_code(self):
        file_path = self.get_last_created_file_path()
        if file_path is None or not file_path.exists():
            return "No generated Python file is available."

        os.system(f"python3 {shlex.quote(str(file_path))}")
        return "Running the saved Python file."

    def get_last_created_file_path(self):
        if self.last_generated_file and self.last_generated_file.exists():
            return self.last_generated_file

        stored_file = self.state_manager.get("last_generated_file")
        if stored_file:
            file_path = Path(stored_file)
            if file_path.exists():
                self.last_generated_file = file_path
                return file_path

        return None
