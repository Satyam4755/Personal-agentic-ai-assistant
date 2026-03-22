# Personal AI Assistant

This is a modular personal AI assistant built in Python. It listens for voice commands, speaks responses, remembers user information, opens apps and websites, generates code, and can create multi-step MERN projects with Gemini as the main AI brain.

## Features

- Basic response system using `data/basic_responses.json`
- AI responses using Google Gemini
- Local memory storage using `memory/user_memory.json`
- Persistent assistant state using `memory/assistant_state.json`
- Silence-based voice recognition using Faster-Whisper
- Text-to-speech using `pyttsx3`
- System control commands for apps and websites
- Python code generation, saving, and execution
- Multi-step MERN project generation and execution

## Project Structure

```text
personal-ai-assistant/
│
├── main.py
├── assistant/
│   ├── __init__.py
│   ├── agent_manager.py
│   ├── code_executor.py
│   ├── command_handler.py
│   ├── gemini_brain.py
│   ├── memory_manager.py
│   ├── state_manager.py
│   ├── voice_engine.py
│   └── system_control.py
│
├── memory/
│   ├── assistant_state.json
│   └── user_memory.json
│
├── data/
│   └── basic_responses.json
│
├── requirements.txt
└── README.md
```

## Installation

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Install the Gemini SDK:

```bash
pip install google-generativeai
```

Set your Gemini API key in your shell:

```bash
export GEMINI_API_KEY="your-api-key"
```

The API key is loaded from the `GEMINI_API_KEY` environment variable. Do not hardcode it in source files.

Optional fallback microphone path:

```bash
pip install SpeechRecognition PyAudio
```

The assistant uses Faster-Whisper as the primary voice recognizer. `SpeechRecognition` is only an optional fallback if Whisper audio capture is unavailable on your machine.

## Run

```bash
python main.py
```

On startup, the assistant prints a quick readiness check for:

- Gemini SDK installation
- `GEMINI_API_KEY`

If Gemini is not ready, local commands still work, but AI replies will not.

## Example Commands

- `hello`
- `hi`
- `what is artificial intelligence`
- `write a short explanation of Python`
- `write python code for a simple calculator`
- `run it`
- `what is today's date`
- `what time is it`
- `my name is Satyam`
- `my city is Lucknow`
- `what is my name`
- `open calculator`
- `open youtube`
- `open google`
- `open vs code`
- `open chrome`
- `build a food delivery full stack website in mernstack in vs code`
- `login payment admin panel`
- `run project`
- `bye`

## Notes

- Gemini responses require internet access and a valid API key.
- Faster-Whisper runs locally after the model is downloaded the first time.
- All memory and assistant state are stored locally in JSON files.
- If Gemini is unavailable or the API key is missing, the assistant returns a safe fallback reply.
- If the microphone stops responding repeatedly, the assistant rebuilds the microphone fallback objects automatically.
