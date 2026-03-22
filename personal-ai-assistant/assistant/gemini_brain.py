import importlib.util
import os
import re
import warnings

genai = None
_genai_import_attempted = False


ERROR_MESSAGE = "Sorry, AI is not available right now."
DEFAULT_MODEL_NAME = "gemini-2.5-flash-lite"
_model = None
_selected_model_name = None


def get_startup_status():
    if importlib.util.find_spec("google.generativeai") is None:
        return {
            "ready": False,
            "messages": [
                "Gemini SDK: missing (`google-generativeai` is not installed).",
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
            "Gemini model: will be selected on first AI request.",
        ],
    }


def _get_model():
    global _model
    global _selected_model_name

    if _load_genai() is None:
        print("Gemini error: google-generativeai is not installed.")
        return None, "Gemini library is not installed. Install google-generativeai and try again."

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Gemini error: GEMINI_API_KEY is not set.")
        return None, "Gemini API key is not configured. Set GEMINI_API_KEY and try again."

    if _model is None:
        genai.configure(api_key=api_key)
        _selected_model_name = DEFAULT_MODEL_NAME
        print(f"Gemini selected model: {_selected_model_name}")
        _model = genai.GenerativeModel(_selected_model_name)

    return _model, None


def _load_genai():
    global genai
    global _genai_import_attempted

    if genai is not None:
        return genai

    if _genai_import_attempted:
        return None

    _genai_import_attempted = True
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            import google.generativeai as imported_genai
    except Exception as error:
        print("Gemini import error:", error)
        genai = None
        return None

    genai = imported_genai
    return genai


def generate_response(prompt: str) -> str:
    cleaned_prompt = prompt.strip()
    if not cleaned_prompt:
        return "Please tell me what you need help with."

    model, model_error = _get_model()
    if model is None:
        return model_error or ERROR_MESSAGE

    try:
        response = model.generate_content(cleaned_prompt)
    except Exception as error:
        print("Gemini error:", error)
        return ERROR_MESSAGE

    if response and hasattr(response, "text") and response.text:
        return response.text.strip()

    return "I could not generate a proper response."


def generate_code(prompt: str, language: str = "python"):
    cleaned_prompt = prompt.strip()
    if not cleaned_prompt:
        return None

    normalized_language = (language or "python").strip().lower()
    model, model_error = _get_model()
    if model is None:
        print("Gemini error:", model_error)
        return None

    prompts = (
        _build_code_prompt(cleaned_prompt, language=normalized_language),
        _build_code_prompt(
            cleaned_prompt,
            language=normalized_language,
            extra_instruction=(
                "Your previous answer was invalid because it used input() or required user interaction. "
                "Rewrite it so it runs immediately with predefined values and prints a demo result."
            ),
        ),
    )

    for code_prompt in prompts:
        try:
            response = model.generate_content(code_prompt)
        except Exception as error:
            print("Gemini error:", error)
            return None

        if response and hasattr(response, "text") and response.text:
            cleaned_code = _clean_code_response(response.text)
            if cleaned_code and (
                normalized_language != "python" or not _contains_interactive_input(cleaned_code)
            ):
                return cleaned_code

    print("Code agent error: Generated code still requires user input.")
    return None


def generate_fullstack_code(project_name: str, features: str):
    cleaned_project_name = project_name.strip()
    cleaned_features = features.strip()

    if not cleaned_project_name:
        cleaned_project_name = "MERN App"

    if not cleaned_features:
        cleaned_features = "home page, product listing, cart page, login/register page"

    model, model_error = _get_model()
    if model is None:
        print("Gemini error:", model_error)
        return None

    fullstack_prompt = _build_fullstack_prompt(cleaned_project_name, cleaned_features)

    try:
        response = model.generate_content(fullstack_prompt)
    except Exception as error:
        print("Gemini error:", error)
        return None

    if response and hasattr(response, "text") and response.text:
        return response.text.strip()

    return None


def _clean_code_response(response_text: str) -> str:
    cleaned_text = response_text.strip()

    fence_match = re.search(r"```(?:python)?\s*(.*?)```", cleaned_text, re.IGNORECASE | re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    lines = cleaned_text.splitlines()
    code_start = _find_code_start(lines)
    if code_start is not None:
        cleaned_text = "\n".join(lines[code_start:]).strip()

    return cleaned_text


def _build_code_prompt(task: str, language: str = "python", extra_instruction: str = "") -> str:
    normalized_language = (language or "python").strip().lower()
    title_language = normalized_language.capitalize()
    instructions = [
        f"You are a {title_language} coding assistant.",
        f"Write {title_language} code for a single source file.",
        f"Return only executable {title_language} code.",
        "Start with code on the first line.",
        "Do not include markdown fences, comments outside the code, or explanations.",
    ]

    if normalized_language == "python":
        instructions.extend(
            [
                "The program must run automatically without user interaction.",
                "Never use input() or any interactive prompt.",
                "Use predefined values, constants, or sample data instead.",
                'Include an if __name__ == "__main__": block that demonstrates the result directly.',
            ]
        )
    else:
        instructions.extend(
            [
                "Keep the code beginner-friendly and self-contained.",
                "Avoid interactive input unless the user explicitly requests it.",
            ]
        )

    if extra_instruction:
        instructions.append(extra_instruction)

    return "\n".join(instructions) + f"\n\nTask: {task}"


def _build_fullstack_prompt(project_name: str, features: str) -> str:
    return f"""Create a full MERN stack application.

Project name:
{project_name}

Features:
{features}

Requirements:
- React frontend with:
  - Home page
  - Product listing
  - Cart page
  - Login/Register page
- Express backend with:
  - Auth routes
  - Product routes
  - Order routes
- Use only packages already available in this setup:
  - frontend: React / CRA defaults only
  - backend: express only
- Do not require extra npm packages such as axios, mongoose, tailwind, redux, or react-router-dom.
- Keep the code beginner-friendly and runnable.

Output rules:
- Return ONLY fenced code blocks.
- Each code block must use the exact relative file path as the fence label.
- Example:
```frontend/src/App.js
// code here
```
- Include at least these files:
  - frontend/src/App.js
  - frontend/src/App.css
  - frontend/src/components/HomePage.js
  - frontend/src/components/ProductList.js
  - frontend/src/components/CartPage.js
  - frontend/src/components/AuthPage.js
  - backend/index.js
- You may include additional files such as backend/routes/auth.js, backend/routes/products.js, backend/routes/orders.js if useful.
"""


def _contains_interactive_input(code_text: str) -> bool:
    return re.search(r"\binput\s*\(", code_text) is not None


def _find_code_start(lines):
    code_prefixes = (
        "import ",
        "from ",
        "def ",
        "class ",
        "if ",
        "for ",
        "while ",
        "print(",
        "try:",
        "with ",
    )

    for index, line in enumerate(lines):
        stripped_line = line.strip()
        if not stripped_line:
            continue

        if stripped_line.startswith(code_prefixes):
            return index

        if "=" in stripped_line and not stripped_line.endswith("?"):
            return index

        if stripped_line.endswith(":"):
            return index

    return None
