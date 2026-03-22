from assistant.command_handler import CommandHandler
from assistant.gemini_brain import get_startup_status
from assistant.voice_engine import VoiceEngine


def main():
    startup_status = get_startup_status()
    print("Startup check:")
    for message in startup_status["messages"]:
        print(f"- {message}")

    voice_engine = VoiceEngine()
    command_handler = CommandHandler()

    voice_engine.speak("Assistant is ready. Say a command.")

    try:
        while True:
            command = voice_engine.listen()

            if not command:
                continue

            response, should_exit = command_handler.handle(command)
            voice_engine.speak(response)

            if should_exit:
                break
    except KeyboardInterrupt:
        voice_engine.speak("Goodbye!")


if __name__ == "__main__":
    main()
