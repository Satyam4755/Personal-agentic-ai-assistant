import importlib.util
import os
import re

genai = None
model = None

MODEL_NAME = "gemini-2.5-flash-lite"
ERROR_MESSAGE = "Sorry, AI is not available right now."


def get_startup_status():
    if importlib.util.find_spec("google.generativeai") is None:
        return {
            "ready": False,
            "messages": [
                "Gemini SDK: missing (`google-generativeai` is not installed).",
                "Gemini API key: not checked.",
            ],
        }

    if not os.getenv("GEMINI_API_KEY"):
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
            f"Gemini model: {MODEL_NAME}.",
        ],
    }


def generate_response(prompt: str) -> str:
    cleaned_prompt = prompt.strip()
    if not cleaned_prompt:
        return "Please tell me what you need help with."

    active_model = _get_model()
    if active_model is None:
        return ERROR_MESSAGE

    try:
        response = active_model.generate_content(cleaned_prompt)
        if response and hasattr(response, "text") and response.text:
            return response.text.strip()
        return "I could not generate a proper response."
    except Exception as error:
        print("Gemini error:", error)
        return ERROR_MESSAGE


def generate_code(prompt: str) -> str | None:
    cleaned_prompt = prompt.strip()
    if not cleaned_prompt:
        return None

    active_model = _get_model()
    if active_model is None:
        return None

    code_prompt = "\n".join(
        [
            "Write only Python code for this request.",
            "Return only executable Python code.",
            "Do not add explanations or markdown unless necessary.",
            "If you use markdown fences, use a single python fence.",
            "Make sure the program can run directly.",
            "",
            f"Task: {cleaned_prompt}",
        ]
    )

    try:
        response = active_model.generate_content(code_prompt)
    except Exception as error:
        print("Gemini error:", error)
        return None

    if not response or not hasattr(response, "text") or not response.text:
        return None

    return _extract_code(response.text)


def generate_fullstack_code(project_name: str, features: str):
    prompt = (
        f"Create a simple full stack project plan for {project_name} "
        f"with these features: {features}."
    )
    return generate_response(prompt)


def _get_model():
    global genai
    global model

    if model is not None:
        return model

    if importlib.util.find_spec("google.generativeai") is None:
        print("Gemini error: google-generativeai is not installed.")
        return None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Gemini error: GEMINI_API_KEY is not set.")
        return None

    try:
        import google.generativeai as imported_genai
    except Exception as error:
        print("Gemini import error:", error)
        return None

    genai = imported_genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)
    return model


def _extract_code(text: str) -> str:
    fence_match = re.search(r"```(?:python)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    return text.strip()
