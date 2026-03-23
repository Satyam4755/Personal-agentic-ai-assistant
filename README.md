# Personal Agentic AI Assistant

Pure Python terminal-based personal assistant with microphone input, Gemini integration, Mac command execution, and full-stack project generation.

## Structure

```text
.
├── assistant/
│   ├── __init__.py
│   ├── agent_manager.py
│   ├── command_handler.py
│   ├── gemini_brain.py
│   ├── system_control.py
│   └── voice_engine.py
├── main.py
├── requirements.txt
└── .env
```

## Features

- Continuous terminal loop: listen -> process -> respond -> repeat
- Microphone input with typed fallback if audio input is unavailable
- Gemini responses for English, Hindi, and Hinglish
- Mac commands like `open youtube`, `open google`, `open vscode`, and `open calculator`
- Full-stack app generation for prompts like `build full stack app`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```env
GEMINI_API_KEY=your_key_here
ASSISTANT_SPEECH_LANGS=en-IN,hi-IN,en-US
ASSISTANT_LISTEN_TIMEOUT=5
ASSISTANT_PHRASE_TIME_LIMIT=10
ASSISTANT_DISABLE_TTS=0
```

## Run

```bash
python main.py
```

## Notes

- On macOS, text-to-speech uses `say` when available.
- Speech recognition uses the microphone through `SpeechRecognition`.
- If microphone setup fails, the assistant falls back to typed terminal input.
- Generated projects are written under `generated_projects/`.
