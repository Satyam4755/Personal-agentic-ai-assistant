import json
import os
import re
from datetime import datetime

from assistant.gemini_brain import generate_code_files
from assistant.system_control import SystemControl


class CodeExecutor:
    CODE_TRIGGER_PHRASES = (
        "write code",
        "create project",
        "build project",
        "build app",
        "create app",
        "write python",
        "write html",
        "generate code",
        "generate project",
        "full stack",
        "fullstack",
        "backend",
        "frontend",
    )
    ACTION_WORDS = ("write", "create", "build", "generate", "make", "develop")
    DEVELOPMENT_WORDS = (
        "code",
        "project",
        "app",
        "application",
        "website",
        "python",
        "flask",
        "fastapi",
        "frontend",
        "backend",
        "full stack",
        "fullstack",
        "html",
        "css",
        "javascript",
        "js",
        "node",
        "express",
        "api",
        "calculator",
    )

    def __init__(self, projects_root=None, system_control=None):
        base_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.projects_root = projects_root or os.path.join(base_directory, "projects")
        self.system_control = system_control or SystemControl()
        os.makedirs(self.projects_root, exist_ok=True)

    def is_code_request(self, command):
        normalized_command = self._normalize(command)
        if any(phrase in normalized_command for phrase in self.CODE_TRIGGER_PHRASES):
            return True

        return any(word in normalized_command for word in self.ACTION_WORDS) and any(
            word in normalized_command for word in self.DEVELOPMENT_WORDS
        )

    def execute_code_request(self, command, open_editor=True):
        blueprint = self._build_blueprint(command)
        project_directory = self._create_project_directory(blueprint["project_name"])
        generated_text = generate_code_files(
            request_text=command,
            project_name=blueprint["display_name"],
            files=blueprint["files"],
            project_type=blueprint["project_type"],
        )
        files = self._parse_generated_files(generated_text, blueprint["files"])
        if not files:
            files = self._fallback_files(command, blueprint)

        written_files = self._write_files(project_directory, files)
        editor_status = None
        if open_editor:
            editor_status = self.system_control.open_vs_code(project_directory)

        return {
            "project_path": project_directory,
            "written_files": written_files,
            "opened_in_vscode": bool(editor_status and editor_status.startswith("Opening")),
            "message": self._build_response_message(project_directory, editor_status, written_files),
        }

    def _build_blueprint(self, command):
        normalized_command = self._normalize(command)
        project_type = self._detect_project_type(normalized_command)
        project_name = self._extract_project_name(normalized_command, project_type)
        files = self._default_files_for_type(project_type, normalized_command)
        display_name = project_name.replace("_", " ").title()
        return {
            "project_name": project_name,
            "display_name": display_name,
            "project_type": project_type,
            "files": files,
        }

    def _detect_project_type(self, command):
        if "full stack" in command or "fullstack" in command:
            if any(keyword in command for keyword in ("node", "express", "javascript", "js")):
                return "fullstack_node"
            return "fullstack_python"

        if any(keyword in command for keyword in ("node", "express", "server js", "serverjs")):
            return "node_backend"

        if "backend" in command and any(keyword in command for keyword in ("javascript", "js")):
            return "node_backend"

        if any(keyword in command for keyword in ("frontend", "website", "web", "html", "css", "javascript", "js")):
            return "web"

        if any(keyword in command for keyword in ("python", "flask", "fastapi", "django", "calculator", "api")):
            return "python"

        return "python"

    def _default_files_for_type(self, project_type, command):
        if project_type == "fullstack_python":
            return [
                "README.md",
                "backend/app.py",
                "backend/requirements.txt",
                "frontend/index.html",
                "frontend/styles.css",
                "frontend/app.js",
            ]

        if project_type == "fullstack_node":
            return [
                "README.md",
                "backend/server.js",
                "backend/package.json",
                "frontend/index.html",
                "frontend/styles.css",
                "frontend/app.js",
            ]

        if project_type == "web":
            return ["index.html", "styles.css", "app.js"]

        if project_type == "node_backend":
            return ["server.js", "package.json"]

        if "calculator" in command or "app" in command:
            return ["app.py"]

        return ["main.py"]

    def _extract_project_name(self, command, project_type):
        stop_words = {
            "write",
            "code",
            "create",
            "project",
            "build",
            "app",
            "full",
            "stack",
            "fullstack",
            "backend",
            "frontend",
            "python",
            "html",
            "css",
            "javascript",
            "js",
            "node",
            "express",
            "flask",
            "web",
            "website",
            "for",
            "with",
            "using",
            "a",
            "an",
            "the",
        }
        words = [word for word in command.split() if word not in stop_words][:3]
        if not words:
            default_names = {
                "fullstack_python": "fullstack_python_app",
                "fullstack_node": "fullstack_node_app",
                "web": "frontend_app",
                "node_backend": "node_backend_app",
                "python": "python_app",
            }
            return default_names.get(project_type, "developer_project")

        if len(words) == 1:
            return self._slugify(f"{words[0]}_app")

        return self._slugify("_".join(words))

    def _create_project_directory(self, project_name):
        base_directory = os.path.join(self.projects_root, project_name)
        if not os.path.exists(base_directory):
            os.makedirs(base_directory, exist_ok=False)
            return base_directory

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = 1
        while True:
            candidate = f"{base_directory}_{timestamp}_{suffix}"
            if not os.path.exists(candidate):
                os.makedirs(candidate, exist_ok=False)
                return candidate
            suffix += 1

    def _parse_generated_files(self, generated_text, expected_files):
        if not generated_text:
            return {}

        generated_files = {}
        allowed_files = {self._sanitize_relative_path(file_name) for file_name in expected_files}
        code_blocks = re.findall(r"```([^\n`]*)\n(.*?)```", generated_text, re.DOTALL)
        for raw_label, raw_code in code_blocks:
            relative_path = self._sanitize_relative_path(raw_label.strip())
            if relative_path is None or relative_path not in allowed_files:
                continue

            file_contents = raw_code.strip()
            if file_contents:
                generated_files[relative_path] = file_contents

        if generated_files:
            return generated_files

        if len(expected_files) == 1:
            if code_blocks:
                return {expected_files[0]: code_blocks[0][1].strip()}
            
            clean_text = generated_text.strip()
            if clean_text.startswith("```"):
                first_newline = clean_text.find("\n")
                if first_newline != -1:
                    clean_text = clean_text[first_newline + 1:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
            return {expected_files[0]: clean_text.strip()}

        return {}

    def _sanitize_relative_path(self, relative_path):
        normalized_path = relative_path.strip().replace("\\", "/").lstrip("./")
        if not normalized_path:
            return None

        path_parts = [part for part in normalized_path.split("/") if part]
        if not path_parts or any(part == ".." for part in path_parts):
            return None

        return "/".join(path_parts)

    def _write_files(self, project_directory, files):
        written_files = []
        for relative_path, content in files.items():
            destination_path = os.path.join(project_directory, relative_path)
            parent_directory = os.path.dirname(destination_path)
            if parent_directory:
                os.makedirs(parent_directory, exist_ok=True)

            if os.path.exists(destination_path):
                continue

            with open(destination_path, "w", encoding="utf-8") as output_file:
                output_file.write(content.rstrip() + "\n")
            written_files.append(relative_path)

        return written_files

    def _build_response_message(self, project_directory, editor_status, written_files):
        if editor_status and editor_status.startswith("Opening"):
            return (
                f"Project created and opened in VS Code at {project_directory}. "
                f"{len(written_files)} files were written successfully."
            )

        return (
            f"Code written successfully in {project_directory}. "
            f"{len(written_files)} files were created."
            + (f" {editor_status}" if editor_status else "")
        )

    def _fallback_files(self, command, blueprint):
        project_type = blueprint["project_type"]
        project_name = blueprint["display_name"]

        if project_type == "fullstack_python":
            return self._fallback_fullstack_python(project_name)

        if project_type == "fullstack_node":
            return self._fallback_fullstack_node(project_name)

        if project_type == "web":
            return self._fallback_web_files(project_name)

        if project_type == "node_backend":
            return self._fallback_node_backend(project_name)

        entry_file = blueprint["files"][0]
        return {entry_file: self._fallback_python_script(command, project_name)}

    def _fallback_python_script(self, command, project_name):
        if "calculator" in self._normalize(command):
            return '''def add(left, right):
    return left + right


def subtract(left, right):
    return left - right


def multiply(left, right):
    return left * right


def divide(left, right):
    if right == 0:
        raise ValueError("Cannot divide by zero.")
    return left / right


def main():
    print("Python Calculator")
    left = float(input("Enter first number: "))
    operator = input("Choose operation (+, -, *, /): ").strip()
    right = float(input("Enter second number: "))

    operations = {
        "+": add,
        "-": subtract,
        "*": multiply,
        "/": divide,
    }

    if operator not in operations:
        print("Unsupported operator.")
        return

    result = operations[operator](left, right)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
'''

        return f'''def main():
    print("Project: {project_name}")
    print("This starter file was created by the personal AI assistant.")


if __name__ == "__main__":
    main()
'''

    def _fallback_web_files(self, project_name):
        return {
            "index.html": f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{project_name}</title>
    <link rel="stylesheet" href="./styles.css" />
  </head>
  <body>
    <main class="shell">
      <h1>{project_name}</h1>
      <p>Starter frontend created by the assistant.</p>
      <button id="action-button">Click me</button>
      <p id="status">Ready.</p>
    </main>
    <script src="./app.js"></script>
  </body>
</html>
''',
            "styles.css": """:root {
  --bg: #f6f1e8;
  --surface: #fffdf8;
  --line: #d9cbb8;
  --text: #1f1a15;
  --accent: #0f766e;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "Segoe UI", sans-serif;
  background: linear-gradient(180deg, #fbf7f0 0%, var(--bg) 100%);
  color: var(--text);
}

.shell {
  width: min(720px, calc(100% - 32px));
  margin: 64px auto;
  padding: 32px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: var(--surface);
}

button {
  padding: 12px 16px;
  border: 0;
  border-radius: 12px;
  background: var(--accent);
  color: white;
  cursor: pointer;
}
""",
            "app.js": """const button = document.getElementById("action-button");
const status = document.getElementById("status");

button.addEventListener("click", () => {
  status.textContent = "Frontend starter is working.";
});
""",
        }

    def _fallback_node_backend(self, project_name):
        package_json = {
            "name": self._slugify(project_name),
            "version": "1.0.0",
            "main": "server.js",
            "scripts": {
                "start": "node server.js",
                "dev": "node server.js",
            },
            "dependencies": {
                "express": "^4.21.2",
            },
        }
        return {
            "package.json": json.dumps(package_json, indent=2),
            "server.js": f"""const express = require("express");

const app = express();
app.use(express.json());

app.get("/", (_req, res) => {{
  res.json({{ message: "{project_name} backend is running." }});
}});

app.listen(3000, () => {{
  console.log("{project_name} backend running on http://localhost:3000");
}});
""",
        }

    def _fallback_fullstack_python(self, project_name):
        return {
            "README.md": f"# {project_name}\n\nGenerated by the personal AI assistant.\n",
            "backend/requirements.txt": "Flask>=3.0.0\n",
            "backend/app.py": f'''from flask import Flask, jsonify, request

app = Flask(__name__)
users = []
items = []


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response


@app.route("/api/health")
def health():
    return jsonify({{"project": "{project_name}", "status": "ok"}})


@app.route("/api/auth/register", methods=["POST"])
def register():
    payload = request.get_json(silent=True) or {{}}
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", "")).strip()
    if not name or not email or not password:
        return jsonify({{"message": "Name, email, and password are required."}}), 400

    if any(user["email"] == email for user in users):
        return jsonify({{"message": "User already exists."}}), 409

    user = {{"id": len(users) + 1, "name": name, "email": email, "password": password}}
    users.append(user)
    return jsonify({{"message": "User registered.", "user": {{"id": user["id"], "name": name, "email": email}}}}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {{}}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", "")).strip()
    user = next((entry for entry in users if entry["email"] == email and entry["password"] == password), None)
    if user is None:
        return jsonify({{"message": "Invalid credentials."}}), 401
    return jsonify({{"message": "Login successful.", "user": {{"id": user["id"], "name": user["name"], "email": user["email"]}}}})


@app.route("/api/items", methods=["GET"])
def list_items():
    return jsonify(items)


@app.route("/api/items", methods=["POST"])
def create_item():
    payload = request.get_json(silent=True) or {{}}
    title = str(payload.get("title", "")).strip()
    description = str(payload.get("description", "")).strip()
    if not title:
        return jsonify({{"message": "Title is required."}}), 400

    item = {{"id": len(items) + 1, "title": title, "description": description}}
    items.append(item)
    return jsonify(item), 201


@app.route("/api/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    item = next((entry for entry in items if entry["id"] == item_id), None)
    if item is None:
        return jsonify({{"message": "Item not found."}}), 404

    payload = request.get_json(silent=True) or {{}}
    item["title"] = str(payload.get("title", item["title"])).strip()
    item["description"] = str(payload.get("description", item["description"])).strip()
    return jsonify(item)


@app.route("/api/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    global items
    if not any(entry["id"] == item_id for entry in items):
        return jsonify({{"message": "Item not found."}}), 404

    items = [entry for entry in items if entry["id"] != item_id]
    return jsonify({{"message": "Item deleted."}})


if __name__ == "__main__":
    app.run(debug=True, port=3425)
''',
            "frontend/index.html": f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{project_name}</title>
    <link rel="stylesheet" href="./styles.css" />
  </head>
  <body>
    <main class="shell">
      <section class="panel">
        <h1>{project_name}</h1>
        <p>Full stack starter with auth and CRUD.</p>
      </section>

      <section class="panel grid">
        <form id="register-form">
          <h2>Register</h2>
          <input name="name" placeholder="Name" required />
          <input name="email" type="email" placeholder="Email" required />
          <input name="password" type="password" placeholder="Password" required />
          <button type="submit">Register</button>
        </form>

        <form id="login-form">
          <h2>Login</h2>
          <input name="email" type="email" placeholder="Email" required />
          <input name="password" type="password" placeholder="Password" required />
          <button type="submit">Login</button>
        </form>
      </section>

      <section class="panel">
        <form id="item-form">
          <h2>Create Item</h2>
          <input name="title" placeholder="Title" required />
          <textarea name="description" rows="4" placeholder="Description"></textarea>
          <button type="submit">Create Item</button>
        </form>
      </section>

      <section class="panel">
        <div class="row">
          <h2>Items</h2>
          <button id="refresh-button" type="button">Refresh</button>
        </div>
        <div id="items"></div>
      </section>

      <section class="panel">
        <h2>Status</h2>
        <pre id="status">Ready.</pre>
      </section>
    </main>
    <script src="./app.js"></script>
  </body>
</html>
''',
            "frontend/styles.css": """:root {
  --bg: #f5f0e7;
  --panel: #fffdf8;
  --line: #d7c9b8;
  --text: #201b16;
  --accent: #0f766e;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "Segoe UI", sans-serif;
  background: linear-gradient(180deg, #fbf7f1 0%, var(--bg) 100%);
  color: var(--text);
}

.shell {
  width: min(900px, calc(100% - 32px));
  margin: 0 auto;
  padding: 40px 0 56px;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 20px;
  margin-bottom: 16px;
}

.grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

form {
  display: grid;
  gap: 10px;
}

input,
textarea,
button {
  font: inherit;
}

input,
textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
}

button {
  padding: 12px 16px;
  border: 0;
  border-radius: 12px;
  background: var(--accent);
  color: white;
  cursor: pointer;
}

#items {
  display: grid;
  gap: 12px;
}

.item {
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
}
""",
            "frontend/app.js": """const apiBase = "http://127.0.0.1:3425/api";
let currentUser = null;

const statusEl = document.getElementById("status");
const itemsEl = document.getElementById("items");

document.getElementById("register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = Object.fromEntries(formData.entries());
  const response = await fetch(`${apiBase}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  updateStatus(data.message || "Register request finished.");
});

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = Object.fromEntries(formData.entries());
  const response = await fetch(`${apiBase}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  currentUser = data.user || null;
  updateStatus(data.message || "Login request finished.");
});

document.getElementById("item-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = Object.fromEntries(formData.entries());
  const response = await fetch(`${apiBase}/items`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  updateStatus(data.message || "Item created.");
  event.target.reset();
  await loadItems();
});

document.getElementById("refresh-button").addEventListener("click", loadItems);

async function loadItems() {
  const response = await fetch(`${apiBase}/items`);
  const items = await response.json();
  itemsEl.innerHTML = items
    .map((item) => `<article class="item"><strong>${item.title}</strong><p>${item.description || ""}</p></article>`)
    .join("");
}

function updateStatus(message) {
  statusEl.textContent = message;
}

loadItems();
""",
        }

    def _fallback_fullstack_node(self, project_name):
        backend_package_json = {
            "name": f"{self._slugify(project_name)}-backend",
            "version": "1.0.0",
            "main": "server.js",
            "scripts": {
                "start": "node server.js",
                "dev": "node server.js",
            },
            "dependencies": {
                "cors": "^2.8.5",
                "express": "^4.21.2",
            },
        }
        return {
            "README.md": f"# {project_name}\n\nGenerated by the personal AI assistant.\n",
            "backend/package.json": json.dumps(backend_package_json, indent=2),
            "backend/server.js": f"""const express = require("express");
const cors = require("cors");

const app = express();
const items = [];
const users = [];

app.use(cors());
app.use(express.json());

app.get("/api/health", (_req, res) => {{
  res.json({{ project: "{project_name}", status: "ok" }});
}});

app.post("/api/auth/register", (req, res) => {{
  const {{ name, email, password }} = req.body || {{}};
  if (!name || !email || !password) {{
    return res.status(400).json({{ message: "Name, email, and password are required." }});
  }}

  if (users.some((user) => user.email === email)) {{
    return res.status(409).json({{ message: "User already exists." }});
  }}

  const user = {{ id: users.length + 1, name, email, password }};
  users.push(user);
  return res.status(201).json({{ message: "User registered.", user: {{ id: user.id, name, email }} }});
}});

app.post("/api/auth/login", (req, res) => {{
  const {{ email, password }} = req.body || {{}};
  const user = users.find((entry) => entry.email === email && entry.password === password);
  if (!user) {{
    return res.status(401).json({{ message: "Invalid credentials." }});
  }}

  return res.json({{ message: "Login successful.", user: {{ id: user.id, name: user.name, email: user.email }} }});
}});

app.get("/api/items", (_req, res) => {{
  res.json(items);
}});

app.post("/api/items", (req, res) => {{
  const {{ title, description }} = req.body || {{}};
  if (!title) {{
    return res.status(400).json({{ message: "Title is required." }});
  }}

  const item = {{ id: items.length + 1, title, description: description || "" }};
  items.push(item);
  return res.status(201).json(item);
}});

app.put("/api/items/:id", (req, res) => {{
  const item = items.find((entry) => entry.id === Number(req.params.id));
  if (!item) {{
    return res.status(404).json({{ message: "Item not found." }});
  }}

  item.title = req.body.title || item.title;
  item.description = req.body.description || item.description;
  return res.json(item);
}});

app.delete("/api/items/:id", (req, res) => {{
  const index = items.findIndex((entry) => entry.id === Number(req.params.id));
  if (index === -1) {{
    return res.status(404).json({{ message: "Item not found." }});
  }}

  items.splice(index, 1);
  return res.json({{ message: "Item deleted." }});
}});

app.listen(3000, () => {{
  console.log("{project_name} backend running on http://localhost:3000");
}});
""",
            "frontend/index.html": self._fallback_web_files(project_name)["index.html"],
            "frontend/styles.css": self._fallback_web_files(project_name)["styles.css"],
            "frontend/app.js": """const apiBase = "http://127.0.0.1:3000/api";
const button = document.getElementById("action-button");
const status = document.getElementById("status");

button.textContent = "Check Backend";
button.addEventListener("click", async () => {
  const response = await fetch(`${apiBase}/health`);
  const data = await response.json();
  status.textContent = `${data.project} is ${data.status}.`;
});
""",
        }

    def _normalize(self, text):
        lowered_text = text.lower().replace("v s code", "vs code")
        lowered_text = re.sub(r"[^\w\s]", " ", lowered_text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", lowered_text).strip()

    def _slugify(self, value):
        cleaned_value = re.sub(r"[^a-zA-Z0-9\s_-]", "", value.lower())
        words = [word for word in cleaned_value.split() if word]
        return "_".join(words[:5]) or "developer_project"


def run_last_generated_code():
    import os

    project_dir = "projects"
    latest_project = sorted(os.listdir(project_dir))[-1]

    project_path = os.path.join(project_dir, latest_project)

    for file in os.listdir(project_path):
        if file.endswith(".py"):
            file_path = os.path.join(project_path, file)
            os.system(f"python3 {file_path}")
            return f"Running {file}"

    return "No runnable Python file found."
