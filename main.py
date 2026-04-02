import os
import sys
import multiprocessing
import signal
import threading
from server import app as flask_app, emit_event
import server

multiprocessing.set_start_method("spawn", force=True)

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
from assistant.runtime_state import is_running, set_running
from assistant.voice_engine import VoiceEngine

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional at runtime
    load_dotenv = None


def _load_environment():
    if load_dotenv is not None:
        load_dotenv()


def request_ctrl_c_shutdown():
    set_running(False)
    os.kill(os.getpid(), signal.SIGINT)


def cleanup(voice_engine=None):
    try:
        from assistant.vision_engine import stop_scan
        stop_scan()
    except Exception:
        pass

    if voice_engine is not None:
        try:
            voice_engine.stop()
        except Exception:
            pass

    try:
        import cv2
        cv2.destroyAllWindows()
    except Exception:
        pass


def main():
    _load_environment()
    voice_engine = None

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
    command_handler = CommandHandler(agent_manager=agent_manager)
    command_handler.voice_engine = voice_engine
    
    def test_elevenlabs():
        voice_engine.smart_speak("Hello sir, kaise hai aap")
    
    test_elevenlabs()

    # Expose them to Flask
    server.command_handler = command_handler

    # Patches for UI integration
    original_speak = voice_engine.speak
    def custom_speak(text):
        if not text: return
        if not getattr(voice_engine, "_suppress_ui_chat", False):
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

    print("Assistant loop started. Press Ctrl+C to stop.")
    if voice_engine.has_voice_input():
        print("- Voice input is ready.")
        print("VOICE SYSTEM READY")
    else:
        print("- Voice input is unavailable. Falling back to typed commands.")

    voice_engine.speak("Assistant is ready. Say a command.")
    is_busy = False

    try:
        while is_running():
            try:
                command = voice_engine.listen()
                if not command:
                    continue

                command_lower = command.lower().strip()

                if "stop scanning" in command_lower:
                    response, should_exit = command_handler.handle_command(command)
                    if response:
                        voice_engine.speak(response)
                    if should_exit:
                        request_ctrl_c_shutdown()
                    continue

                if is_busy:
                    continue

                is_busy = True
                try:
                    agent_manager.remember_context(command)
                    response, should_exit = command_handler.handle_command(command)

                    if response:
                        voice_engine.speak(response)

                    if should_exit:
                        request_ctrl_c_shutdown()
                finally:
                    is_busy = False

            except Exception as e:
                print("Loop exception:", e)

    except KeyboardInterrupt:
        set_running(False)
        print("\nStopping assistant.")
    finally:
        print("Assistant stopped.")
        cleanup(voice_engine)
        sys.exit(0)


if __name__ == "__main__":
    main()
