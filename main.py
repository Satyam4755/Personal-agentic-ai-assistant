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

    startup_status = get_startup_status()
    print("Startup check:")
    for message in startup_status["messages"]:
        print(f"- {message}")
    if not startup_status["ready"]:
        print("- Gemini features may be limited until the issue above is fixed.")

    agent_manager = AgentManager()
    voice_engine = VoiceEngine()
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
