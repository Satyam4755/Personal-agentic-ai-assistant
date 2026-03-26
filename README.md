# Personal Agentic AI Assistant

Pure Python terminal-based personal assistant with microphone input, Gemini integration, Mac command execution, and full-stack project generation.

## Structure

```text
.
├── assistant/
│   ├── __init__.py
│   ├── agent_manager.py
│   ├── command_handler.py
│   ├── code_executor.py
│   ├── gemini_brain.py
│   ├── system_control.py
│   └── voice_engine.py
├── main.py
├── projects/
├── requirements.txt
└── .env
```

## Features

- Continuous terminal loop: listen -> process -> respond -> repeat
- Microphone input with typed fallback if audio input is unavailable
- Gemini responses for English, Hindi, and Hinglish
- Mac commands like `open youtube`, `open google`, `open vscode`, and `open calculator`
- Code execution workflow for prompts like `write python calculator` and `build full stack app`
- Automatic folder creation under `projects/` with safe timestamp suffixes for duplicates
- Automatic VS Code opening after files are written

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
- Generated projects are written under `projects/`.
