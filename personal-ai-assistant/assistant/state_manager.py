import json
from pathlib import Path


class StateManager:
    def __init__(self, state_file=None):
        project_root = Path(__file__).resolve().parent.parent
        self.state_file = Path(state_file or (project_root / "memory" / "assistant_state.json"))
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self):
        try:
            with self.state_file.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def save(self, state):
        with self.state_file.open("w", encoding="utf-8") as file:
            json.dump(state, file, indent=4)

    def get(self, key, default=None):
        state = self.load()
        return state.get(key, default)

    def set(self, key, value):
        state = self.load()
        state[key] = value
        self.save(state)

