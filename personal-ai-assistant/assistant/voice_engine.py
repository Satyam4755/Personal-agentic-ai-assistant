import platform
import shutil
import subprocess
import time

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None


class VoiceEngine:
    def __init__(self):
        self.engine = None
        self.system_name = platform.system()
        self.system_tts_command = ["say"] if self.system_name == "Darwin" and shutil.which("say") else None
        self.recognizer = sr.Recognizer() if sr else None
        self.mic = None

        if self.recognizer is not None:
            self.recognizer.pause_threshold = 3.0
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.energy_threshold = 300

        if sr is not None:
            try:
                self.mic = sr.Microphone()
            except Exception as error:
                print(f"Microphone setup error: {error}")
                self.mic = None

    def listen(self):
        if self.recognizer is None or self.mic is None:
            return self._listen_from_text("Voice input is unavailable. Type your command.")

        try:
            with self.mic as source:
                print("Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self.recognizer.listen(source)

            command = self.recognizer.recognize_google(audio)
            cleaned_command = command.strip().lower()
            if not cleaned_command:
                return None

            print(f"You: {cleaned_command}")
            return cleaned_command
        except sr.UnknownValueError:
            return None
        except sr.RequestError as error:
            print(f"Voice recognition error: {error}")
            return self._listen_from_text("Voice failed, using text input.")
        except Exception as error:
            print(f"Microphone error: {error}")
            return self._listen_from_text("Voice failed, using text input.")

    def speak(self, text):
        if not text:
            return

        print(f"Assistant: {text}")
        if self.system_tts_command:
            self._speak_with_system_tts(text)
            return

        if self.engine is None:
            self.engine = self._create_engine()
            if self.engine is None:
                return

        try:
            self.engine.stop()
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as error:
            print(f"TTS error: {error}")
            self.engine = self._create_engine()
            if self.engine is None:
                return
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as retry_error:
                print(f"TTS retry error: {retry_error}")

    def _create_engine(self):
        if pyttsx3 is None:
            return None

        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 170)
            return engine
        except Exception as error:
            print(f"TTS setup error: {error}")
            return None

    def _listen_from_text(self, prompt):
        print(prompt)
        try:
            typed_command = input("You: ").strip()
        except EOFError:
            return None

        if not typed_command:
            return None

        return typed_command.lower()

    def _speak_with_system_tts(self, text):
        try:
            subprocess.run(
                self.system_tts_command + [text],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as error:
            print(f"TTS error: {error}")
