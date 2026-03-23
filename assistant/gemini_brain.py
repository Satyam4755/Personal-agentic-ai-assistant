import importlib.util
import json
import os
import re

genai = None
_genai_import_attempted = False

ERROR_MESSAGE = "Sorry, AI is not available right now."
DEFAULT_MODEL_NAME = "gemini-2.5-flash-lite"
_client = None


def get_startup_status():
    try:
        gemini_spec = importlib.util.find_spec("google.genai")
    except ModuleNotFoundError:
        gemini_spec = None

    if gemini_spec is None:
        return {
            "ready": False,
            "messages": [
                "Gemini SDK: missing (`google-genai` is not installed).",
                "Gemini API key: not checked.",
            ],
        }

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {
            "ready": False,
            "messages": [
                "Gemini SDK: ready.",
                "Gemini API key: missing (`GEMINI_API_KEY` is not set).",
            ],
        }

    return {
        "ready": True,
        "messages": [
            "Gemini SDK: ready.",
            "Gemini API key: set.",
            f"Gemini model: {os.getenv('GEMINI_MODEL', DEFAULT_MODEL_NAME)}.",
        ],
    }


def detect_intent(command: str):
    cleaned_command = command.strip()
    if not cleaned_command:
        return {"intent": "chat", "language": "english", "confidence": "low"}

    client, model_name, _ = _get_client()
    if client is None:
        return {
            "intent": "chat",
            "language": _detect_language(cleaned_command),
            "confidence": "low",
        }

    prompt = f"""Classify the user's assistant request.

Return JSON only:
{{
  "intent": "chat" | "system_command" | "project_generation",
  "language": "english" | "hindi" | "hinglish",
  "confidence": "high" | "medium" | "low"
}}

Rules:
- "system_command" means the user wants a local action like opening YouTube, Google, VS Code, or Calculator.
- "project_generation" means the user wants a full stack app or project generated.
- "chat" means everything else.
- Support English, Hindi, and Hinglish.

User request:
{cleaned_command}
"""

    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
    except Exception as error:
        print("Gemini intent error:", error)
        return {
            "intent": "chat",
            "language": _detect_language(cleaned_command),
            "confidence": "low",
        }

    if not response or not hasattr(response, "text") or not response.text:
        return {
            "intent": "chat",
            "language": _detect_language(cleaned_command),
            "confidence": "low",
        }

    try:
        parsed = _extract_json_object(response.text)
    except ValueError:
        parsed = {}

    intent = parsed.get("intent", "chat")
    if intent not in {"chat", "system_command", "project_generation"}:
        intent = "chat"

    language = parsed.get("language", _detect_language(cleaned_command))
    if language not in {"english", "hindi", "hinglish"}:
        language = _detect_language(cleaned_command)

    confidence = parsed.get("confidence", "low")
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"

    return {
        "intent": intent,
        "language": language,
        "confidence": confidence,
    }


def generate_response(prompt: str) -> str:
    return generate_assistant_response(prompt)


def generate_assistant_response(command: str, context_prompt: str = "") -> str:
    cleaned_command = command.strip()
    if not cleaned_command:
        return "Please tell me what you need help with."

    client, model_name, model_error = _get_client()
    if client is None:
        return model_error or ERROR_MESSAGE

    prompt = f"""You are a smart personal assistant running in a terminal on a Mac.

Rules:
- Understand English, Hindi, and Hinglish.
- Reply in the same language style as the user.
- Be concise, natural, and helpful.
- Do not claim to have executed a system command unless the command layer already handled it.
- If the user asks for guidance, answer directly.

Context:
{context_prompt or "No previous context."}

User:
{cleaned_command}

Assistant:"""

    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
    except Exception as error:
        print("Gemini error:", error)
        return ERROR_MESSAGE

    if response and hasattr(response, "text") and response.text:
        return response.text.strip()

    return "I could not generate a proper response."


def refine_spoken_command(transcript: str) -> str:
    cleaned_transcript = transcript.strip()
    if not cleaned_transcript:
        return ""

    client, model_name, model_error = _get_client()
    if client is None:
        if model_error:
            print("Gemini speech cleanup skipped:", model_error)
        return cleaned_transcript

    cleanup_prompt = f"""You clean noisy speech-to-text transcripts for a personal assistant.

Rules:
- Return only the corrected user command on a single line.
- Preserve the user's original meaning.
- Fix likely speech-recognition mistakes.
- Support mixed Hindi and English written in Latin script.
- Do not answer the command.
- If the transcript is already clear, return it with minimal cleanup.

Examples:
- open goo gal -> open google
- open vs cody -> open vscode
- google kholo -> open google

Transcript:
{cleaned_transcript}

Corrected command:"""

    try:
        response = client.models.generate_content(model=model_name, contents=cleanup_prompt)
    except Exception as error:
        print("Gemini speech cleanup error:", error)
        return cleaned_transcript

    if response and hasattr(response, "text") and response.text:
        refined_text = response.text.strip().splitlines()[0].strip().strip('"').strip("'")
        return refined_text or cleaned_transcript

    return cleaned_transcript


def generate_fullstack_project(request_text: str, project_name: str) -> str | None:
    cleaned_request = request_text.strip()
    cleaned_project_name = project_name.strip() or "Personal Full Stack App"

    client, model_name, model_error = _get_client()
    if client is None:
        print("Gemini error:", model_error)
        return None

    prompt = f"""Generate a full stack starter project.

Project name:
{cleaned_project_name}

Original user request:
{cleaned_request}

Requirements:
- Use a Python Flask backend.
- Use a simple HTML, CSS, and vanilla JavaScript frontend.
- Include CRUD operations for a sample items resource.
- Include basic authentication with register and login endpoints.
- Keep the code readable and runnable.
- Avoid unnecessary dependencies.

Return ONLY fenced code blocks.
Each code block must use the relative file path as the fence label.

Required files:
- README.md
- backend/app.py
- backend/requirements.txt
- frontend/index.html
- frontend/styles.css
- frontend/app.js
"""

    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
    except Exception as error:
        print("Gemini project generation error:", error)
        return None

    if response and hasattr(response, "text") and response.text:
        return response.text.strip()

    return None


def _get_client():
    global _client

    if _load_genai() is None:
        print("Gemini error: google-genai is not installed.")
        return None, None, "Gemini library is not installed. Install google-genai and try again."

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Gemini error: GEMINI_API_KEY is not set.")
        return None, None, "Gemini API key is not configured. Set GEMINI_API_KEY and try again."

    model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL_NAME)
    if _client is None:
        print(f"Gemini selected model: {model_name}")
        _client = genai.Client(api_key=api_key)

    return _client, model_name, None


def _load_genai():
    global genai
    global _genai_import_attempted

    if genai is not None:
        return genai

    if _genai_import_attempted:
        return None

    _genai_import_attempted = True
    try:
        from google import genai as imported_genai
    except Exception as error:
        print("Gemini import error:", error)
        genai = None
        return None

    genai = imported_genai
    return genai


def _detect_language(text: str) -> str:
    if re.search(r"[\u0900-\u097F]", text) and re.search(r"[A-Za-z]", text):
        return "hinglish"

    if re.search(r"[\u0900-\u097F]", text):
        return "hindi"

    normalized_text = text.lower()
    hinglish_hints = ("mera", "mujhe", "kya", "kaise", "banao", "kholo", "karo", "hai")
    if any(hint in normalized_text for hint in hinglish_hints):
        return "hinglish"

    return "english"


def _extract_json_object(text: str):
    cleaned_text = text.strip()
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
        if not match:
            raise ValueError("Gemini did not return JSON.")

        return json.loads(match.group(0))
