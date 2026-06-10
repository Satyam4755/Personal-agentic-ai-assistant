import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
MEMORY_PATH = os.path.join(MEMORY_DIR, "memory.json")

def load_memory():
    if not os.path.exists(MEMORY_PATH):
        return {"profile": {}, "conversations": []}
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if "profile" not in data or not isinstance(data["profile"], dict):
                data["profile"] = {}
            if "conversations" not in data or not isinstance(data["conversations"], list):
                data["conversations"] = []
            return data
        except json.JSONDecodeError:
            return {"profile": {}, "conversations": []}

def save_memory(data):
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def set_memory(key, value):
    data = load_memory()
    data["profile"][key] = value
    save_memory(data)

def get_memory(key):
    data = load_memory()
    return data["profile"].get(key)

def add_conversation(user_text, assistant_text):
    data = load_memory()
    data["conversations"].append({
        "timestamp": datetime.now().isoformat(),
        "user": user_text,
        "assistant": assistant_text
    })
    if len(data["conversations"]) > 200:
        data["conversations"] = data["conversations"][-200:]
    save_memory(data)

def update_profile(new_facts):
    if not new_facts or not isinstance(new_facts, dict):
        return
    data = load_memory()
    data["profile"].update(new_facts)
    save_memory(data)

def get_memory_context():
    data = load_memory()
    context_lines = []
    
    if data.get("profile"):
        context_lines.append("User Profile / Facts:")
        for k, v in data["profile"].items():
            context_lines.append(f"- {k}: {v}")
        context_lines.append("")
        
    conversations = data.get("conversations", [])
    if conversations:
        context_lines.append("Recent Conversation History:")
        recent = conversations[-5:]
        for conv in recent:
            context_lines.append(f"User: {conv.get('user')}")
            context_lines.append(f"Assistant: {conv.get('assistant')}")
        context_lines.append("")
        
    return "\n".join(context_lines).strip()

def handle_memory(command):
    # Old direct handle_memory logic disabled, we use natural conversational memory now.
    return None
