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

from assistant.gemini_brain import detect_intent, convert_to_hindi

def normalize_command(text):
    text = text.lower().strip()
    replacements = {
        "bye bye": "bye",
        "ok bye": "bye",
        "okay bye": "bye",
        "bye-bye": "bye",
        "拜拜": "bye"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

def normalize_for_voice(text):
    hinglish_map = {
        "kaise ho": "कैसे हो",
        "kaise hai aap": "कैसे हैं आप",
        "main thik hun": "मैं ठीक हूँ",
    }
    for k, v in hinglish_map.items():
        text = text.replace(k, v)
    return text

whisper_model = None

def load_whisper():
    global whisper_model
    if whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            print("Loading faster-whisper model (base)...")
            whisper_model = WhisperModel("base", compute_type="int8")
        except Exception as e:
            print("Failed to load whisper:", e)
            whisper_model = False

class VoiceEngine:
    def __init__(self):
        self.system_name = platform.system()
        self.last_listen_error = False
        self.recognizer = None
        self.microphone = None
        self.engine = None
        self.voice_disabled = False
        self._ambient_noise_calibrated = False
        self.ELEVEN_ENABLED = True
        self.AUDIO_DISABLED = False
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

        if self.disable_tts or getattr(self, "AUDIO_DISABLED", False):
            return

        skip_words = ["error", "traceback", "code generated", "```", "def ", "function "]
        for word in skip_words:
            if word in text.lower():
                return

        self.smart_speak(text)

    def smart_speak(self, text):
        import os
        MAX_ELEVEN_CHARS = 150
        text = normalize_for_voice(text)

        try:
            intent_data = detect_intent(text)
            language = intent_data.get("language", "english")
            if language == "hinglish":
                text = convert_to_hindi(text)
        except Exception as e:
            pass

        api_key = os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVEN_API_KEY")
        eleven_enabled = getattr(self, "ELEVEN_ENABLED", True)

        if api_key and eleven_enabled and len(text) <= MAX_ELEVEN_CHARS:
            try:
                import requests
                import subprocess

                print("Using ElevenLabs REST API...")
                url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL"
                headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
                data = {"text": text, "model_id": "eleven_multilingual_v2"}
                response = requests.post(url, json=data, headers=headers)
                
                if response.status_code == 200:
                    output_file = "temp_tts.mp3"
                    with open(output_file, "wb") as f:
                        f.write(response.content)
                    
                    if not os.path.exists(output_file):
                        print(f"ERROR: {output_file} not found")
                        return

                    subprocess.run(["afplay", output_file])
                    return
                else:
                    print(f"ElevenLabs API Error [{response.status_code}]: Quota exhausted or Unauthorized.")
                    self.ELEVEN_ENABLED = False
            except Exception as e:
                print("ElevenLabs Exception:", e)
                self.ELEVEN_ENABLED = False

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

        load_whisper()
        
        try:
            with self.microphone as source:
                print("Listening...")
                if not self._ambient_noise_calibrated:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                    self._ambient_noise_calibrated = True

                # Record audio from mic (4-5 sec)
                audio = self.recognizer.listen(
                    source,
                    timeout=self.listen_timeout,
                    phrase_time_limit=5.0,
                )
        except sr.WaitTimeoutError:
            return None
        except Exception as error:
            print(f"Microphone error: {error}")
            self.last_listen_error = True
            self.voice_disabled = True
            return None

        if not whisper_model:
            return self._fallback_listen_microphone_audio(audio)

        import tempfile
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio.get_wav_data())
                temp_filename = f.name
            
            segments, info = whisper_model.transcribe(temp_filename, beam_size=5, language="en", condition_on_previous_text=False)
            transcript = "".join(segment.text for segment in segments).strip()
            os.remove(temp_filename)
            
            print("Recognized Text:", transcript)
        except Exception as e:
            print("Whisper transcription error:", e)
            return self._fallback_listen_microphone_audio(audio)

        if not transcript:
            return None

        cleaned_transcript = self._prepare_spoken_command(transcript)
        return cleaned_transcript or None

    def _fallback_listen_microphone_audio(self, audio):
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
        return normalize_command(command)
