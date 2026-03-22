import time

from assistant.agent_manager import AgentManager
from assistant.command_handler import CommandHandler
from assistant.gemini_brain import get_startup_status
from assistant.voice_engine import VoiceEngine


def respond(voice_engine, text):
    if not text:
        return

    print(f"Assistant: {text}")
    try:
        voice_engine.speak(text)
    except Exception as error:
        print(f"Speak error: {error}")


def get_input(voice_engine):
    print(voice_engine.get_input_prompt())
    if voice_engine.has_voice_input():
        command = voice_engine.listen_continuous(announce=False)
        if command:
            return command

    print("Type your command:")
    try:
        typed_command = input().strip()
    except EOFError:
        return None

    if not typed_command:
        return None

    return voice_engine.accept_typed_command(typed_command)


def main():
    startup_status = get_startup_status()
    print("Startup check:")
    for message in startup_status["messages"]:
        print(f"- {message}")
    if not startup_status["ready"]:
        print("- Gemini replies may be unavailable until the issue above is fixed.")

    voice_engine = VoiceEngine()
    agent_manager = AgentManager()
    command_handler = CommandHandler()
    fail_count = 0

    respond(voice_engine, "Assistant is ready. Say a command.")

    try:
        while True:
            command = get_input(voice_engine)

            if not command:
                if voice_engine.last_listen_error:
                    fail_count += 1
                    if fail_count >= 3:
                        voice_engine.reset_microphone()
                        fail_count = 0
                else:
                    fail_count = 0
                time.sleep(0.1)
                continue

            fail_count = 0
            agent_manager.remember_context(command)

            if agent_manager.current_task:
                response = agent_manager.handle_step(command)
                should_exit = False
            else:
                context_prompt = agent_manager.get_context_prompt(command)
                if command_handler.is_code_request(command):
                    response, should_exit = command_handler.handle_command(
                        command,
                        context_prompt=context_prompt,
                    )
                else:
                    project_response = agent_manager.handle_project_command(command)
                    if project_response:
                        response = project_response
                        should_exit = False
                    elif agent_manager.detect_task(command):
                        response = agent_manager.handle_step(command)
                        should_exit = False
                    else:
                        response, should_exit = command_handler.handle_command(
                            command,
                            context_prompt=context_prompt,
                        )

            respond(voice_engine, response)
            time.sleep(0.3)

            if should_exit:
                break
    except KeyboardInterrupt:
        voice_engine.stop()
        respond(voice_engine, "Goodbye!")


if __name__ == "__main__":
    main()
