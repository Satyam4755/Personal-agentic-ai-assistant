# Personal AI Assistant

This is a simple personal AI assistant built in Python. It listens for voice commands, speaks responses, opens basic websites, uses Gemini for AI replies, and can generate Python code into a file and run it.

## Features

- Voice input using `SpeechRecognition`
- Voice output using `pyttsx3`
- Gemini AI replies using `google-generativeai`
- Basic commands:
  - `open google`
  - `open youtube`
- Local memory using `memory/user_memory.json`
- Python code generation, saving, and execution

## Installation

```bash
pip install -r requirements.txt
```

Set your Gemini API key:

```bash
export GEMINI_API_KEY="your-api-key"
```

## Run

```bash
python main.py
```

## Example Commands

- `hello`
- `open google`
- `open youtube`
- `my name is Satyam`
- `what is my name`
- `write python code for a simple calculator`
- `run code`
- `bye`
