import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
MEMORY_PATH = os.path.join(MEMORY_DIR, "memory.json")

def load_memory():
    if not os.path.exists(MEMORY_PATH):
        return {}
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_memory(data):
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def set_memory(key, value):
    data = load_memory()
    data[key] = value
    save_memory(data)

def get_memory(key):
    data = load_memory()
    return data.get(key)

def handle_memory(command):
    command_lower = command.lower().strip()

    # STORE NAME
    if "my name is " in command_lower:
        name = command_lower.split("my name is ")[-1].strip().title()
        set_memory("name", name)
        return f"Got it, I will remember that your name is {name}."

    # GET NAME
    if command_lower in ["what is my name", "what's my name", "what is my name?", "mera naam kya hai", "do you know my name"]:
        name = get_memory("name")
        if name:
            return f"Your name is {name}."
        return "I don't know your name yet. Please tell me."

    return None
