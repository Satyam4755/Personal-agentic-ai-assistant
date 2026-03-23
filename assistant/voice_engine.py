import os
import platform
import re
import shutil
import subprocess

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

from assistant.gemini_brain import refine_spoken_command


class VoiceEngine:
    def __init__(self):
        self.system_name = platform.system()
        self.last_listen_error = False
        self.recognizer = None
        self.microphone = None
        self.engine = None
        self.voice_disabled = False
        self._ambient_noise_calibrated = False
        self.listen_timeout = float(os.getenv("ASSISTANT_LISTEN_TIMEOUT", "5"))
        self.phrase_time_limit = float(os.getenv("ASSISTANT_PHRASE_TIME_LIMIT", "10"))
        self.speech_languages = [
            language.strip()
            for language in os.getenv("ASSISTANT_SPEECH_LANGS", "en-IN,hi-IN,en-US").split(",")
            if language.strip()
        ]
        self.disable_tts = os.getenv("ASSISTANT_DISABLE_TTS", "0") == "1"

        self.reset_microphone()
        self._setup_tts()

    def speak(self, text):
        if not text:
            return

        print(f"Assistant: {text}")
        if self.disable_tts:
            return

        if self.system_name == "Darwin" and shutil.which("say"):
            subprocess.run(["say", text], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return

        if self.engine is not None:
            self.engine.say(text)
            self.engine.runAndWait()

    def stop(self):
        if self.engine is not None:
            try:
                self.engine.stop()
            except Exception:
                pass

    def listen(self):
        self.last_listen_error = False

        if self.has_voice_input():
            command = self._listen_from_microphone()
            if command:
                print(f"You: {command}")
                return command

            if not self.voice_disabled:
                return None

        typed_command = self._listen_from_terminal()
        if typed_command:
            print(f"You: {typed_command}")
        return typed_command

    def reset_microphone(self):
        if sr is None:
            self.voice_disabled = True
            return

        try:
            self.recognizer = sr.Recognizer()
            self.recognizer.pause_threshold = 0.8
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.microphone = sr.Microphone()
            self.voice_disabled = False
        except Exception as error:
            print(f"Microphone unavailable: {error}")
            self.recognizer = None
            self.microphone = None
            self.voice_disabled = True

    def has_voice_input(self):
        return not self.voice_disabled and self.recognizer is not None and self.microphone is not None

    def _setup_tts(self):
        if self.disable_tts or pyttsx3 is None:
            return

        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 170)
        except Exception as error:
            print(f"TTS init error: {error}")
            self.engine = None

    def _listen_from_microphone(self):
        if not self.has_voice_input():
            return None

        try:
            with self.microphone as source:
                print("Listening...")
                if not self._ambient_noise_calibrated:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                    self._ambient_noise_calibrated = True

                audio = self.recognizer.listen(
                    source,
                    timeout=self.listen_timeout,
                    phrase_time_limit=self.phrase_time_limit,
                )
        except sr.WaitTimeoutError:
            return None
        except Exception as error:
            print(f"Microphone error: {error}")
            self.last_listen_error = True
            self.voice_disabled = True
            return None

        transcript = self._recognize_audio(audio)
        if not transcript:
            return None

        cleaned_transcript = self._prepare_spoken_command(transcript)
        return cleaned_transcript or None

    def _recognize_audio(self, audio):
        if self.recognizer is None:
            return None

        last_error = None
        for language in self.speech_languages:
            try:
                transcript = self.recognizer.recognize_google(audio, language=language)
                if transcript and transcript.strip():
                    return transcript.strip()
            except sr.UnknownValueError:
                continue
            except Exception as error:
                last_error = error

        if last_error:
            print(f"Speech recognition error: {last_error}")
            self.last_listen_error = True

        return None

    def _listen_from_terminal(self):
        try:
            typed_command = input("Type command: ").strip()
        except EOFError:
            return None

        return typed_command or None

    def _prepare_spoken_command(self, command):
        if not command:
            return None

        cleaned_command = re.sub(r"\s+", " ", command).strip()
        normalized_command = cleaned_command.lower()
        if len(normalized_command.split()) >= 2:
            refined_command = refine_spoken_command(normalized_command).strip()
            if refined_command:
                return refined_command

        return cleaned_command
