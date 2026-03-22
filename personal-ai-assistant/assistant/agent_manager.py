import os
import platform
import re
import shlex
import shutil
import subprocess
import webbrowser
from pathlib import Path

from assistant.gemini_brain import generate_fullstack_code
from assistant.state_manager import StateManager


class AgentManager:
    def __init__(self):
        self.current_task = None
        self.task_step = 0
        self.context = {}
        self.context_history = []
        self.base_path = Path.home() / "Desktop" / "AI_Projects"
        self.npm_cache_path = self.base_path / ".npm-cache"
        self.system_name = platform.system()
        self.state_manager = StateManager()
        stored_project_path = self.state_manager.get("last_project_path")
        self.last_project_path = Path(stored_project_path) if stored_project_path else None

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

    def detect_task(self, command):
        normalized_command = command.lower().strip()

        if self._is_build_project_request(normalized_command):
            print("Agent manager triggered.")
            self.current_task = "build_project"
            self.task_step = 1
            self.context = {
                "project_request": command.strip(),
                "project_name": self._extract_project_name(command),
            }
            print(f"Agent manager task: {self.current_task}")
            print(f"Agent manager project name: {self.context['project_name']}")
            return True

        return False

    def handle_step(self, command):
        if self.current_task != "build_project":
            return "I am not working on a multi-step task right now."

        if self.task_step == 1:
            print("Agent manager step 1: asking for project features.")
            self.task_step = 2
            project_name = self.context.get("project_name", "your project")
            return f"What features do you want for {project_name}? For example: login, payment, admin panel."

        if self.task_step == 2:
            print(f"Agent manager step 2: received features: {command.strip()}")
            self.context["features"] = command.strip()
            self.task_step = 3
            setup_message = self._create_full_stack_project()
            self._reset_task()
            return setup_message

        setup_message = self._create_full_stack_project()
        self._reset_task()
        return setup_message

    def handle_project_command(self, command):
        normalized_command = command.lower().strip()
        if not self._is_project_run_command(normalized_command):
            return None

        if self.last_project_path is None:
            return None

        return self.run_mern_project(self.last_project_path)

    def _is_build_project_request(self, command):
        if self._looks_like_code_request(command):
            return False

        project_keywords = ("build project", "full stack", "fullstack", "mern", "mernstack")
        if any(keyword in command for keyword in project_keywords):
            return True

        if "build" in command and any(word in command for word in ("app", "project", "website", "dashboard", "store")):
            return True

        return False

    def _is_project_run_command(self, command):
        run_phrases = ("run project", "run it", "run the project")
        return any(self._contains_phrase(command, phrase) for phrase in run_phrases)

    def _create_full_stack_project(self):
        project_name = self.context.get("project_name", "mern project")
        project_folder = self.base_path / self._slugify(project_name)
        backend_path = project_folder / "backend"
        frontend_path = project_folder / "frontend"
        print(f"Agent manager base folder: {self.base_path}")
        print(f"Agent manager project folder: {project_folder}")

        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            self.npm_cache_path.mkdir(parents=True, exist_ok=True)
            project_folder.mkdir(parents=True, exist_ok=True)
            backend_path.mkdir(parents=True, exist_ok=True)
            frontend_path.mkdir(parents=True, exist_ok=True)
            print(f"Agent manager backend folder ready: {backend_path}")
            print(f"Agent manager frontend folder ready: {frontend_path}")
            print(f"Agent manager npm cache: {self.npm_cache_path}")
        except OSError as error:
            print(f"Agent manager error creating folders: {error}")
            return "I could not create the project folders."

        if not shutil.which("npm"):
            print("Agent manager warning: npm was not found.")
            return "I need npm installed to create the backend project."

        if not shutil.which("npx"):
            print("Agent manager warning: npx was not found.")
            return "I need npx installed to create the frontend project."

        node_env = self._build_node_env()

        try:
            if not (backend_path / "package.json").exists():
                print(f"Initializing backend in: {backend_path}")
                subprocess.run(["npm", "init", "-y"], cwd=backend_path, check=True, env=node_env)

            if not (frontend_path / "package.json").exists():
                print(f"Creating frontend in: {frontend_path}")
                subprocess.run(
                    ["npx", "--yes", "create-react-app", "frontend"],
                    cwd=project_folder,
                    check=True,
                    env=node_env,
                )

            if not (backend_path / "node_modules" / "express").exists():
                print(f"Installing express in: {backend_path}")
                subprocess.run(["npm", "install", "express"], cwd=backend_path, check=True, env=node_env)
        except subprocess.CalledProcessError as error:
            print(f"Agent manager project setup error: {error}")
            return "I started the setup but one of the project commands failed."
        except OSError as error:
            print(f"Agent manager process error: {error}")
            return "I could not run the project setup commands."

        customization_message = self._write_project_files(frontend_path, backend_path)
        if customization_message:
            return customization_message

        self.last_project_path = project_folder
        self.state_manager.set("last_project_path", str(project_folder))
        print(f"Agent manager stored last project path: {self.last_project_path}")
        self._open_in_vs_code(project_folder)
        run_message = self.run_mern_project(project_folder)
        features = self.context.get("features", "")

        if features:
            return f"Full stack project created successfully in VS Code. Saved features: {features}. {run_message}"

        return f"Full stack project created successfully in VS Code. {run_message}"

    def _open_in_vs_code(self, project_path):
        project_path_str = str(project_path)

        try:
            if shutil.which("code"):
                print(f"Agent manager launching VS Code with: code {project_path_str}")
                subprocess.Popen(["code", project_path_str])
                return

            if self.system_name == "Darwin":
                print(f"Agent manager launching VS Code with macOS open command for: {project_path_str}")
                subprocess.Popen(["open", "-a", "Visual Studio Code", project_path_str])
                return
        except OSError as error:
            print(f"Agent manager editor launch error: {error}")

    def run_mern_project(self, project_path):
        project_path = Path(project_path)
        frontend_path = project_path / "frontend"
        backend_path = project_path / "backend"

        if not frontend_path.exists() or not backend_path.exists():
            print(f"Agent manager warning: MERN project folders are missing under: {project_path}")
            return "I could not find the frontend and backend folders for that project."

        backend_command = f"cd {shlex.quote(str(backend_path))} && node index.js"
        frontend_command = f"cd {shlex.quote(str(frontend_path))} && npm start"

        print(f"Agent manager backend run command: {backend_command}")
        self._run_command_in_terminal(backend_command)
        print(f"Agent manager frontend run command: {frontend_command}")
        self._run_command_in_terminal(frontend_command)
        self._open_project_browser()

        return "Running full stack project in terminal."

    def _extract_project_name(self, command):
        cleaned_command = re.sub(
            r"\b(build|create|a|an|full stack|fullstack|mern|mernstack|project|in vs code|vs code|website)\b",
            " ",
            command,
            flags=re.IGNORECASE,
        )
        cleaned_command = re.sub(
            r"\s+(?:in|inside|using|with|on)\s+(?:vs\s*code|visual\s+studio\s+code|mernstack|mern)\b.*$",
            "",
            cleaned_command,
            flags=re.IGNORECASE,
        )
        cleaned_command = re.sub(r"\b(in|inside|using|with|on)\b", " ", cleaned_command, flags=re.IGNORECASE)
        cleaned_command = re.sub(r"\s+", " ", cleaned_command).strip(" .")
        return cleaned_command or "mern project"

    def _slugify(self, value):
        cleaned_value = re.sub(r"[^a-zA-Z0-9\s]", "", value.lower())
        words = [word for word in cleaned_value.split() if word]
        return "_".join(words[:5]) or "mern_project"

    def _contains_phrase(self, command, phrase):
        pattern = rf"\b{re.escape(phrase)}\b"
        return re.search(pattern, command) is not None

    def _looks_like_code_request(self, command):
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
        return any(word in command for word in code_words) and any(
            language in command for language in language_words
        )

    def _reset_task(self):
        print("Agent manager reset.")
        self.current_task = None
        self.task_step = 0
        self.context = {}

    def _build_node_env(self):
        node_env = os.environ.copy()
        node_env["NPM_CONFIG_CACHE"] = str(self.npm_cache_path)
        node_env["npm_config_cache"] = str(self.npm_cache_path)
        node_env["npm_config_yes"] = "true"
        return node_env

    def _write_project_files(self, frontend_path, backend_path):
        frontend_src_path = frontend_path / "src"

        if not frontend_src_path.exists():
            print(f"Agent manager warning: frontend src folder is missing: {frontend_src_path}")
            return "I created the project, but the React source folder is missing."

        project_name = self.context.get("project_name", "MERN App")
        features = self.context.get("features", "")
        print("Agent manager generating project files with Gemini.")
        generated_text = generate_fullstack_code(project_name, features)
        if not generated_text:
            print("Agent manager warning: Gemini did not return project files.")
            return "I created the project shell, but Gemini could not generate the app files."

        generated_files = self._parse_generated_project_files(generated_text)
        if not generated_files:
            print("Agent manager warning: No valid project files were parsed from Gemini output.")
            return "I created the project shell, but I could not parse the generated app files."

        required_files = {
            "frontend/src/App.js",
            "frontend/src/App.css",
            "backend/index.js",
        }
        missing_files = sorted(required_files - set(generated_files))
        if missing_files:
            print(f"Agent manager warning: Missing generated files: {missing_files}")
            return "I created the project shell, but Gemini did not return all required app files."

        try:
            for relative_path, file_contents in generated_files.items():
                destination_path = frontend_path.parent / relative_path
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                destination_path.write_text(file_contents, encoding="utf-8")
                print(f"Agent manager wrote generated file: {destination_path}")
        except OSError as error:
            print(f"Agent manager file write error: {error}")
            return "I created the project, but I could not write the generated frontend or backend files."

        return None

    def _run_command_in_terminal(self, command):
        try:
            if self.system_name == "Darwin":
                escaped_command = command.replace("\\", "\\\\").replace('"', '\\"')
                apple_script = f'tell application "Terminal" to do script "{escaped_command}"'
                subprocess.Popen(["osascript", "-e", apple_script])
                return

            subprocess.Popen(command, shell=True)
        except OSError as error:
            print(f"Agent manager terminal launch error: {error}")

    def _open_project_browser(self):
        try:
            if self.system_name == "Darwin":
                print("Agent manager opening browser at: http://localhost:3000")
                subprocess.Popen(["open", "http://localhost:3000"])
                return

            print("Agent manager opening browser at: http://localhost:3000")
            webbrowser.open("http://localhost:3000")
        except OSError as error:
            print(f"Agent manager browser launch error: {error}")

    def _parse_generated_project_files(self, generated_text):
        generated_files = {}
        code_blocks = re.findall(r"```([^\n`]+)\n(.*?)```", generated_text, re.DOTALL)

        for raw_label, raw_code in code_blocks:
            relative_path = raw_label.strip()
            file_contents = raw_code.strip()

            if not relative_path or not file_contents:
                continue

            first_line, _, remaining_code = file_contents.partition("\n")
            path_match = re.match(r"^(?://|#)\s*FILE:\s*(.+)$", first_line.strip(), re.IGNORECASE)
            if path_match:
                relative_path = path_match.group(1).strip()
                file_contents = remaining_code.strip()

            safe_relative_path = self._sanitize_generated_path(relative_path)
            if safe_relative_path is None:
                print(f"Agent manager skipped unsafe generated path: {relative_path}")
                continue

            generated_files[safe_relative_path] = file_contents

        print(f"Agent manager parsed generated files: {sorted(generated_files)}")
        return generated_files

    def _sanitize_generated_path(self, relative_path):
        normalized_path = relative_path.strip().replace("\\", "/")
        normalized_path = normalized_path.lstrip("./")

        if not normalized_path:
            return None

        path_obj = Path(normalized_path)
        if path_obj.is_absolute() or ".." in path_obj.parts:
            return None

        allowed_prefixes = ("frontend/", "backend/")
        if not any(normalized_path.startswith(prefix) for prefix in allowed_prefixes):
            return None

        return normalized_path
