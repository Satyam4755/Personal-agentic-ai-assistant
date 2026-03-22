import json
import re
from difflib import SequenceMatcher
from pathlib import Path


class MemoryManager:
    def __init__(self, memory_file):
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.memory_file.exists():
            self.save_memory({})

    def load_memory(self):
        try:
            with self.memory_file.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def save_memory(self, memory_data):
        with self.memory_file.open("w", encoding="utf-8") as file:
            json.dump(memory_data, file, indent=4)

    def remember(self, key, value):
        memory_data = self.load_memory()
        memory_data[key] = value
        self.save_memory(memory_data)

    def process_memory_command(self, command):
        patterns = [
            (r"my name is (.+)", "name", "Nice to meet you, {value}. I will remember your name."),
            (r"my city is (.+)", "city", "I will remember that your city is {value}."),
            (r"i live in (.+)", "city", "I will remember that you live in {value}."),
        ]

        for pattern, key, response in patterns:
            match = re.search(pattern, command, re.IGNORECASE)

            if match:
                value = match.group(1).strip(" .!?")
                if key == "name":
                    value = self._format_name(value)
                self.remember(key, value)
                return response.format(value=value)

        return None

    def get_stored_name(self):
        memory_data = self.load_memory()
        return memory_data.get("name", "")

    def correct_command_with_stored_name(self, command):
        stored_name = self.get_stored_name()
        if not stored_name:
            return command

        corrected_command = self._correct_name_phrase(command, stored_name)
        corrected_command = self._correct_single_word_name(corrected_command, stored_name)
        return corrected_command

    def answer_memory_question(self, command):
        memory_data = self.load_memory()

        if self._contains_phrase(command, "what is my name"):
            name = memory_data.get("name")
            if name:
                return f"Your name is {name}."
            return "I do not know your name yet. Tell me by saying my name is..."

        if (
            self._contains_phrase(command, "what is my city")
            or self._contains_phrase(command, "where do i live")
        ):
            city = memory_data.get("city")
            if city:
                return f"You live in {city}."
            return "I do not know your city yet. Tell me by saying my city is..."

        return None

    def _contains_phrase(self, command, phrase):
        pattern = rf"\b{re.escape(phrase)}\b"
        return re.search(pattern, command, re.IGNORECASE) is not None

    def _correct_name_phrase(self, command, stored_name):
        pattern = r"\b(my name is|i am|i m|call me)\s+([a-zA-Z][a-zA-Z\s'-]*)"
        match = re.search(pattern, command, re.IGNORECASE)

        if not match:
            return command

        candidate_name = match.group(2).strip(" .!?")
        if not self._is_similar_name(candidate_name, stored_name):
            return command

        corrected_phrase = f"{match.group(1)} {stored_name}"
        return (
            command[: match.start()]
            + corrected_phrase
            + command[match.end():]
        )

    def _correct_single_word_name(self, command, stored_name):
        if " " in stored_name.strip():
            return command

        def replace_token(match):
            token = match.group(0)
            if self._is_similar_name(token, stored_name):
                return stored_name
            return token

        return re.sub(r"\b[a-zA-Z]+\b", replace_token, command)

    def _is_similar_name(self, candidate_name, stored_name):
        normalized_candidate = self._normalize_name(candidate_name)
        normalized_stored = self._normalize_name(stored_name)

        if not normalized_candidate or not normalized_stored:
            return False

        if normalized_candidate == normalized_stored:
            return True

        if normalized_candidate[0] != normalized_stored[0]:
            return False

        if abs(len(normalized_candidate) - len(normalized_stored)) > 3:
            return False

        similarity = SequenceMatcher(None, normalized_candidate, normalized_stored).ratio()
        return similarity >= 0.65

    def _normalize_name(self, value):
        return re.sub(r"[^a-zA-Z]", "", value.lower())

    def _format_name(self, value):
        cleaned_value = re.sub(r"\s+", " ", value.strip())
        return " ".join(part.capitalize() for part in cleaned_value.split())
