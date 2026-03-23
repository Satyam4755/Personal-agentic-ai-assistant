import json
import re
from pathlib import Path

from assistant.gemini_brain import generate_fullstack_project


class AgentManager:
    def __init__(self):
        self.context_history = []
        self.project_root = Path(__file__).resolve().parent.parent
        self.generated_projects_root = self.project_root / "generated_projects"
        self.generated_projects_root.mkdir(parents=True, exist_ok=True)

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

    def is_project_request(self, command):
        normalized_command = self._normalize(command)
        build_words = ("build", "create", "generate", "make", "develop", "banao", "बनाओ")
        project_words = (
            "full stack",
            "fullstack",
            "app",
            "project",
            "website",
            "crud",
            "dashboard",
            "frontend",
            "backend",
            "प्रोजेक्ट",
            "वेबसाइट",
            "ऐप",
        )
        return any(word in normalized_command for word in build_words) and any(
            word in normalized_command for word in project_words
        )

    def handle_project_request(self, command):
        project_name = self._extract_project_name(command)
        project_directory = self.generated_projects_root / self._slugify(project_name)
        generated_files = self._request_project_files(command, project_name)
        write_report = self._write_project_files(project_directory, generated_files, project_name, command)

        return (
            f"Project ready in {project_directory}. "
            f"Created {write_report['created']} files, updated {write_report['updated']} files, "
            f"and preserved {write_report['preserved']} existing files."
        )

    def _normalize(self, text):
        normalized_text = text.lower()
        normalized_text = re.sub(r"[^\w\s]", " ", normalized_text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", normalized_text).strip()

    def _extract_project_name(self, command):
        cleaned_command = self._normalize(command)
        stop_words = {
            "build",
            "create",
            "generate",
            "make",
            "develop",
            "full",
            "stack",
            "app",
            "project",
            "website",
            "crud",
            "frontend",
            "backend",
            "with",
            "for",
            "and",
            "the",
            "a",
            "an",
            "banao",
            "बनाओ",
        }
        important_words = [word for word in cleaned_command.split() if word not in stop_words][:3]
        if not important_words:
            return "personal_fullstack_app"

        return "_".join(important_words)

    def _slugify(self, value):
        cleaned_value = re.sub(r"[^a-zA-Z0-9\s_-]", "", value.lower())
        words = [word for word in cleaned_value.split() if word]
        return "_".join(words[:5]) or "personal_fullstack_app"

    def _request_project_files(self, command, project_name):
        generated_text = generate_fullstack_project(command, project_name)
        generated_files = self._parse_generated_project_files(generated_text or "")
        if generated_files:
            return generated_files

        return self._fallback_project_files(project_name)

    def _parse_generated_project_files(self, generated_text):
        generated_files = {}
        code_blocks = re.findall(r"```([^\n`]+)\n(.*?)```", generated_text, re.DOTALL)

        for raw_label, raw_code in code_blocks:
            relative_path = raw_label.strip()
            file_contents = raw_code.strip()
            if not relative_path or not file_contents:
                continue

            safe_relative_path = self._sanitize_generated_path(relative_path)
            if safe_relative_path is None:
                continue

            generated_files[safe_relative_path] = file_contents

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
            if normalized_path != "README.md":
                return None

        return normalized_path

    def _write_project_files(self, project_directory, files, project_name, source_request):
        project_directory.mkdir(parents=True, exist_ok=True)
        manifest_path = project_directory / ".assistant_manifest.json"
        managed_files = set()

        if manifest_path.exists():
            try:
                managed_files = set(json.loads(manifest_path.read_text(encoding="utf-8")).get("managed_files", []))
            except (OSError, json.JSONDecodeError):
                managed_files = set()

        created = 0
        updated = 0
        preserved = 0

        for relative_path, content in files.items():
            destination_path = project_directory / relative_path
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            next_content = content.rstrip() + "\n"

            if not destination_path.exists():
                destination_path.write_text(next_content, encoding="utf-8")
                created += 1
                continue

            existing_content = destination_path.read_text(encoding="utf-8")
            if existing_content == next_content:
                preserved += 1
                continue

            if relative_path in managed_files:
                destination_path.write_text(next_content, encoding="utf-8")
                updated += 1
            else:
                preserved += 1

        manifest_payload = {
            "project_name": project_name,
            "source_request": source_request,
            "managed_files": sorted(files.keys()),
        }
        manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")
        return {
            "created": created,
            "updated": updated,
            "preserved": preserved,
        }

    def _fallback_project_files(self, project_name):
        display_name = project_name.replace("_", " ").title()
        return {
            "README.md": f"# {display_name}\n\nGenerated by the personal AI assistant.\n\n## Run backend\n\n```bash\ncd backend\npip install -r requirements.txt\npython app.py\n```\n\n## Frontend\n\nOpen `frontend/index.html` in a browser after the backend starts.\n",
            "backend/requirements.txt": "Flask>=3.0.0\n",
            "backend/app.py": self._fallback_backend_app(display_name),
            "frontend/index.html": self._fallback_frontend_html(display_name),
            "frontend/styles.css": self._fallback_frontend_css(),
            "frontend/app.js": self._fallback_frontend_js(),
        }

    def _fallback_backend_app(self, project_name):
        return f'''from flask import Flask, jsonify, request
from pathlib import Path
import hashlib
import json
import secrets

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"
ITEMS_FILE = DATA_DIR / "items.json"
TOKENS_FILE = DATA_DIR / "tokens.json"


def ensure_file(path, default):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(default, indent=2) + "\\n", encoding="utf-8")


def load_json(path, default):
    ensure_file(path, default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def save_json(path, value):
    ensure_file(path, value)
    path.write_text(json.dumps(value, indent=2) + "\\n", encoding="utf-8")


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_authenticated_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "", 1).strip()
    tokens = load_json(TOKENS_FILE, [])
    users = load_json(USERS_FILE, [])
    token_entry = next((entry for entry in tokens if entry["token"] == token), None)
    if token_entry is None:
        return None

    return next((user for user in users if user["id"] == token_entry["user_id"]), None)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response


@app.route("/api/health")
def health():
    return jsonify({{"success": True, "project": "{project_name}"}})


@app.route("/api/auth/register", methods=["POST"])
def register():
    payload = request.get_json(silent=True) or {{}}
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", "")).strip()

    if not name or not email or not password:
        return jsonify({{"message": "Name, email, and password are required."}}), 400

    users = load_json(USERS_FILE, [])
    if any(user["email"] == email for user in users):
        return jsonify({{"message": "User already exists."}}), 409

    user = {{
        "id": len(users) + 1,
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
    }}
    users.append(user)
    save_json(USERS_FILE, users)
    return jsonify({{"message": "User registered successfully."}}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {{}}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", "")).strip()

    users = load_json(USERS_FILE, [])
    user = next((entry for entry in users if entry["email"] == email), None)
    if user is None or user["password_hash"] != hash_password(password):
        return jsonify({{"message": "Invalid credentials."}}), 401

    token = secrets.token_hex(24)
    tokens = load_json(TOKENS_FILE, [])
    tokens = [entry for entry in tokens if entry["user_id"] != user["id"]]
    tokens.append({{"user_id": user["id"], "token": token}})
    save_json(TOKENS_FILE, tokens)

    return jsonify({{
        "message": "Login successful.",
        "token": token,
        "user": {{"id": user["id"], "name": user["name"], "email": user["email"]}},
    }})


@app.route("/api/items", methods=["GET"])
def list_items():
    return jsonify(load_json(ITEMS_FILE, []))


@app.route("/api/items", methods=["POST"])
def create_item():
    user = get_authenticated_user()
    if user is None:
        return jsonify({{"message": "Authentication required."}}), 401

    payload = request.get_json(silent=True) or {{}}
    title = str(payload.get("title", "")).strip()
    description = str(payload.get("description", "")).strip()
    if not title:
        return jsonify({{"message": "Title is required."}}), 400

    items = load_json(ITEMS_FILE, [])
    item = {{
        "id": len(items) + 1,
        "title": title,
        "description": description,
        "owner_id": user["id"],
    }}
    items.append(item)
    save_json(ITEMS_FILE, items)
    return jsonify(item), 201


@app.route("/api/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    user = get_authenticated_user()
    if user is None:
        return jsonify({{"message": "Authentication required."}}), 401

    items = load_json(ITEMS_FILE, [])
    item = next((entry for entry in items if entry["id"] == item_id), None)
    if item is None:
        return jsonify({{"message": "Item not found."}}), 404

    if item["owner_id"] != user["id"]:
        return jsonify({{"message": "You can only edit your own items."}}), 403

    payload = request.get_json(silent=True) or {{}}
    item["title"] = str(payload.get("title", item["title"])).strip()
    item["description"] = str(payload.get("description", item["description"])).strip()
    save_json(ITEMS_FILE, items)
    return jsonify(item)


@app.route("/api/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    user = get_authenticated_user()
    if user is None:
        return jsonify({{"message": "Authentication required."}}), 401

    items = load_json(ITEMS_FILE, [])
    item = next((entry for entry in items if entry["id"] == item_id), None)
    if item is None:
        return jsonify({{"message": "Item not found."}}), 404

    if item["owner_id"] != user["id"]:
        return jsonify({{"message": "You can only delete your own items."}}), 403

    items = [entry for entry in items if entry["id"] != item_id]
    save_json(ITEMS_FILE, items)
    return jsonify({{"message": "Item deleted."}})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
'''

    def _fallback_frontend_html(self, project_name):
        return f'''<!DOCTYPE html>
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
        <p>Minimal full stack starter with auth and CRUD.</p>
      </section>

      <section class="panel grid">
        <form id="register-form">
          <h2>Register</h2>
          <input name="name" type="text" placeholder="Name" required />
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
        <h2>Create Item</h2>
        <form id="item-form">
          <input name="title" type="text" placeholder="Title" required />
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
'''

    def _fallback_frontend_css(self):
        return """:root {
  --bg: #f5f0e7;
  --panel: #fffdf8;
  --line: #d7c9b8;
  --text: #201b16;
  --muted: #6d6255;
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
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 14px;
}

button {
  border: 0;
  border-radius: 999px;
  padding: 12px 16px;
  background: var(--accent);
  color: #fff;
  cursor: pointer;
}

.item-card {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  margin-bottom: 12px;
}

pre {
  margin: 0;
  white-space: pre-wrap;
  color: var(--muted);
}
"""

    def _fallback_frontend_js(self):
        return """const API_BASE = "http://127.0.0.1:5000/api";
const TOKEN_KEY = "assistant-generated-app-token";

const registerForm = document.querySelector("#register-form");
const loginForm = document.querySelector("#login-form");
const itemForm = document.querySelector("#item-form");
const itemsContainer = document.querySelector("#items");
const refreshButton = document.querySelector("#refresh-button");
const statusElement = document.querySelector("#status");

function setStatus(message, payload) {
  statusElement.textContent = payload
    ? `${message}\\n\\n${JSON.stringify(payload, null, 2)}`
    : message;
}

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

async function apiRequest(path, options = {}) {
  const token = getToken();
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || "Request failed.");
  }
  return data;
}

async function loadItems() {
  try {
    const items = await apiRequest("/items");
    itemsContainer.innerHTML = "";
    if (!items.length) {
      itemsContainer.textContent = "No items yet.";
      return;
    }

    items.forEach((item) => {
      const card = document.createElement("article");
      card.className = "item-card";
      card.innerHTML = `<h3>${item.title}</h3><p>${item.description || "No description"}</p>`;
      itemsContainer.appendChild(card);
    });
  } catch (error) {
    setStatus(error.message);
  }
}

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(registerForm).entries());
  try {
    const data = await apiRequest("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setStatus("Registered successfully.", data);
    registerForm.reset();
  } catch (error) {
    setStatus(error.message);
  }
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(loginForm).entries());
  try {
    const data = await apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    localStorage.setItem(TOKEN_KEY, data.token);
    setStatus("Logged in successfully.", data.user);
    loginForm.reset();
    loadItems();
  } catch (error) {
    setStatus(error.message);
  }
});

itemForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(itemForm).entries());
  try {
    const data = await apiRequest("/items", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setStatus("Item created.", data);
    itemForm.reset();
    loadItems();
  } catch (error) {
    setStatus(error.message);
  }
});

refreshButton.addEventListener("click", loadItems);
loadItems();
"""
