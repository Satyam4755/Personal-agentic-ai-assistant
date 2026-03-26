import sys
import threading
import queue
import time
from app import app as flask_app, emit_event, command_queue

class SSEStdoutRedirector:
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout

    def write(self, text):
        self.original_stdout.write(text)
        self.original_stdout.flush()
        
        clean_text = text.strip()
        # Avoid repeating chat history in terminal logs
        if clean_text and not clean_text.startswith("Assistant:") and not clean_text.startswith("You:"):
            emit_event("log", content=clean_text)

    def flush(self):
        self.original_stdout.flush()

from assistant.agent_manager import AgentManager
from assistant.command_handler import CommandHandler
from assistant.gemini_brain import get_startup_status
from assistant.voice_engine import VoiceEngine

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional at runtime
    load_dotenv = None


def _load_environment():
    if load_dotenv is not None:
        load_dotenv()


def main():
    _load_environment()

    # Flask UI integration
    sys.stdout = SSEStdoutRedirector(sys.stdout)
    sys.stderr = SSEStdoutRedirector(sys.stderr)

    def run_flask():
        flask_app.run(host="0.0.0.0", port=3425, debug=False, use_reloader=False)
    
    threading.Thread(target=run_flask, daemon=True).start()

    startup_status = get_startup_status()
    print("Startup check:")
    for message in startup_status["messages"]:
        print(f"- {message}")
    if not startup_status["ready"]:
        print("- Gemini features may be limited until the issue above is fixed.")

    agent_manager = AgentManager()
    voice_engine = VoiceEngine()
    
    # Patches for UI integration
    original_speak = voice_engine.speak
    def custom_speak(text):
        if not text: return
        emit_event('chat', role='assistant', content=text)
        emit_event('state', status='speaking')
        original_speak(text)
        emit_event('state', status='idle')
    voice_engine.speak = custom_speak

    original_microphone = voice_engine._listen_from_microphone
    def custom_microphone():
        cmd = original_microphone()
        if cmd:  # Transcribed from voice
            emit_event('chat', role='user', content=cmd)
        return cmd
    voice_engine._listen_from_microphone = custom_microphone

    def custom_terminal_listen():
        try:
            # Poll UI command queue instead of input() blocking
            return command_queue.get(timeout=0.2)
        except queue.Empty:
            return None
    voice_engine._listen_from_terminal = custom_terminal_listen

    command_handler = CommandHandler(agent_manager=agent_manager)

    print("Assistant loop started. Press Ctrl+C to stop.")
    if voice_engine.has_voice_input():
        print("- Voice input is ready.")
    else:
        print("- Voice input is unavailable. Falling back to typed commands.")

    voice_engine.speak("Assistant is ready. Say a command.")

    try:
        exit_commands = ["bye", "bye bye", "exit", "stop", "quit"]

        while True:
            command = voice_engine.listen()
            if not command:
                continue

            text_lower = command.lower().strip()

            # Custom small talk responses
            if "hello" in text_lower:
                response = "Hello sir, kaise hai aap"
                voice_engine.speak(response)
                continue

            if "tum kaise ho" in text_lower or "kaise ho" in text_lower:
                response = "Mai bhi badhiya hu sir, bataiye mai kaise apki madad karu"
                voice_engine.speak(response)
                continue

            # Handle exit commands directly
            if any(cmd in text_lower for cmd in exit_commands):
                response = "Goodbye Sir! 👋"
                voice_engine.speak(response)
                break

            agent_manager.remember_context(command)
            response, should_exit = command_handler.handle_command(command)
            voice_engine.speak(response)

            if should_exit:
                break
    except KeyboardInterrupt:
        print("\nStopping assistant.")
    finally:
        voice_engine.stop()


if __name__ == "__main__":
    main()
