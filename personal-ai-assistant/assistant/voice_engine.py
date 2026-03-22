from collections import deque
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import textwrap
import threading
import time
from difflib import SequenceMatcher
from pathlib import Path

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

from assistant.memory_manager import MemoryManager


class VoiceEngine:
    def __init__(self):
        project_root = Path(__file__).resolve().parent.parent
        self.memory_manager = MemoryManager(project_root / "memory" / "user_memory.json")
        self.vosk_model_path = project_root / "models" / "vosk-model-small-en-us-0.15"

        self.system_name = platform.system()
        self.system_tts_command = self._detect_system_tts_command()
        self.prefer_system_tts = self.system_tts_command is not None
        self.preferred_voice_id = "com.apple.voice.compact.hi-IN.Lekha"
        self.engine = None
        self.tts_warning_announced = False

        self.is_speaking = False
        self.text_mode_announced = False
        self.pending_command = None
        self.last_listen_error = False

        self.recognizer = None
        self.microphone = None
        self.vosk_model = None
        self.vosk_model_class = None
        self.vosk_recognizer_class = None
        self.vosk_import_attempted = False
        self.enable_whisper = os.getenv("ASSISTANT_DISABLE_WHISPER") != "1"
        self.whisper_model = None
        self.whisper_model_error = None
        self.np = None
        self.sd = None
        self.whisper_model_class = None
        self.whisper_import_attempted = False
        self.whisper_warmup_started = False
        self.whisper_warmup_in_progress = False
        self.whisper_warmup_thread = None
        self.voice_backend = "text"
        self.voice_status_announced = False

        self.last_spoken_text = ""
        self.last_speech_finished_at = 0.0
        self.listen_resume_delay = 0.25
        self.echo_guard_duration = 1.2
        self.echo_similarity_threshold = 0.55
        self.short_echo_similarity_threshold = 0.85

        self.sample_rate = 16000
        self.chunk_duration = 0.25
        self.pause_threshold = 3.0
        self.energy_threshold = 0.015
        self.ambient_noise_duration = 0.5
        self.pre_speech_buffer_duration = 0.5
        self.speech_start_timeout = 8.0
        self.ambient_multiplier = 1.8
        self.max_speech_threshold = 0.04
        self.max_record_seconds = 45

        self.interrupt_poll_seconds = 0.8
        self.interrupt_chunk_duration = 0.1
        self.interrupt_energy_threshold = 0.04
        self.interrupt_activation_chunks = 2
        self.audio_stream_latency = "low"
        self.audio_overflow_warning_interval = 5.0
        self.last_audio_overflow_warning_at = 0.0
        self.vosk_blocksize = 8000
        self.q = queue.Queue(maxsize=64)

        self.reset_microphone()
        self._refresh_voice_backend()

    def speak(self, text):
        if not text:
            return

        normalized_text = self._normalize_text(text)
        self.is_speaking = True
        print("DEBUG: Speaking started")

        if self.prefer_system_tts:
            try:
                self._speak_with_fallback(text)
            finally:
                self.is_speaking = False
                self.last_spoken_text = normalized_text
                self.last_speech_finished_at = time.monotonic()
                time.sleep(0.2)
            return

        try:
            if self.engine is None:
                self.reset_engine()

            if self.engine is None:
                self._speak_with_fallback(text)
                return

            self.engine.stop()
            self._speak_with_interrupt_checks(text)
        except Exception as error:
            print(f"TTS error: {error}")
            self.reset_engine()
            try:
                if self.engine is not None:
                    self.engine.stop()
                    self._speak_with_interrupt_checks(text)
                else:
                    self._speak_with_fallback(text)
            except Exception as retry_error:
                print(f"TTS retry error: {retry_error}")
                self._speak_with_fallback(text)
        finally:
            self.is_speaking = False
            self.last_spoken_text = normalized_text
            self.last_speech_finished_at = time.monotonic()
            time.sleep(0.2)

    def reset_engine(self):
        if pyttsx3 is None:
            self.engine = None
            return

        try:
            if self.engine is not None:
                self.engine.stop()
        except Exception:
            pass

        try:
            self.engine = pyttsx3.init()
            self._configure_engine()
        except Exception as error:
            print(f"TTS init error: {error}")
            self.engine = None

    def _detect_system_tts_command(self):
        if self.system_name == "Darwin" and shutil.which("say"):
            return ["say"]

        if self.system_name == "Linux":
            if shutil.which("espeak"):
                return ["espeak"]
            if shutil.which("spd-say"):
                return ["spd-say"]

        return None

    def _configure_engine(self):
        if self.engine is None:
            return

        voices = self.engine.getProperty("voices") or []
        preferred_voice_available = any(
            getattr(voice, "id", "") == self.preferred_voice_id
            for voice in voices
        )
        if preferred_voice_available:
            self.engine.setProperty("voice", self.preferred_voice_id)

        self.engine.setProperty("rate", 170)

    def _speak_with_interrupt_checks(self, text):
        if self.engine is None:
            return

        parts = self._split_speech_chunks(text)
        if not parts:
            parts = [text]

        for index, chunk in enumerate(parts):
            if not chunk.strip():
                continue

            self.engine.say(chunk)
            self.engine.runAndWait()

            if index == len(parts) - 1:
                continue

            interrupt_command = self._capture_interrupt_command(chunk)
            if interrupt_command:
                self.pending_command = interrupt_command
                self.engine.stop()
                break

    def _speak_with_fallback(self, text):
        if self._speak_with_system_tts(text):
            return

        if not self.tts_warning_announced:
            print("TTS warning: no voice engine is available. Responses will be printed only.")
            self.tts_warning_announced = True

    def _speak_with_system_tts(self, text):
        if not self.system_tts_command:
            return False

        try:
            parts = self._split_speech_chunks(text)
            if not parts:
                parts = [text]

            for index, chunk in enumerate(parts):
                if not chunk.strip():
                    continue

                subprocess.run(
                    self.system_tts_command + [chunk],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                if index == len(parts) - 1:
                    continue

                interrupt_command = self._capture_interrupt_command(chunk)
                if interrupt_command:
                    self.pending_command = interrupt_command
                    break

            return True
        except OSError as error:
            print(f"System TTS error: {error}")
            return False

    def stop(self):
        try:
            self.engine.stop()
        except Exception:
            pass

        self.is_speaking = False
        self.last_speech_finished_at = time.monotonic()

    def listen(self):
        return self.listen_continuous()

    def listen_continuous(self, announce=True, stop_event=None):
        return self.listen_for_input(announce=announce, stop_event=stop_event)

    def listen_for_input(self, announce=True, stop_event=None):
        self.last_listen_error = False

        if self.pending_command:
            command = self.pending_command
            self.pending_command = None
            print(f"You: {command}")
            return command

        if self.is_speaking or self._is_stop_requested(stop_event):
            return None

        self._wait_for_listen_window()
        self._refresh_voice_backend()

        if self.voice_backend == "whisper" and self.whisper_model is not None:
            return self._listen_with_whisper(announce=announce, stop_event=stop_event)

        if self.voice_backend == "vosk":
            return self._listen_with_vosk(announce=announce, stop_event=stop_event)

        if self.voice_backend == "speech_recognition" and stop_event is None:
            return self._listen_with_speech_recognition(announce=announce)

        if announce:
            self._announce_voice_status_once()
        if stop_event is not None:
            time.sleep(0.1)
        return None

    def _listen_with_speech_recognition(self, announce=True):
        try:
            with self.microphone as source:
                if announce:
                    print("Listening...")
                self.recognizer.pause_threshold = self.pause_threshold
                self.recognizer.energy_threshold = 300
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self.recognizer.listen(
                    source,
                    timeout=4,
                    phrase_time_limit=None,
                )

            command = self.recognizer.recognize_google(audio)
            command = self._normalize_text(command)
            command = self.memory_manager.correct_command_with_stored_name(command)
            if not command:
                return None

            print(f"You (voice): {command}")
            self._maybe_start_whisper_warmup()
            return command.lower()
        except Exception as error:
            print(f"Listening error: {error}")
            self.last_listen_error = True
            return None

    def _listen_with_whisper(self, announce=True, stop_event=None):
        if announce:
            print("Listening...")
        listen_started_at = time.monotonic()

        try:
            audio = self._record_until_silence(stop_event=stop_event)
        except Exception as error:
            print(f"Microphone error: {error}")
            self.last_listen_error = True
            return None

        return self._transcribe_audio(audio, listen_started_at=listen_started_at, print_user=True)

    def _listen_with_vosk(self, announce=True, stop_event=None):
        if not self._ensure_vosk_model() or not self._ensure_sounddevice():
            return None

        if announce:
            print("Listening...")

        recognizer = self.vosk_recognizer_class(self.vosk_model, self.sample_rate)
        listen_started_at = time.monotonic()
        silence_started_at = None
        heard_speech = False
        last_partial = ""
        final_text = ""
        self._reset_vosk_queue()

        try:
            with self.sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=self.vosk_blocksize,
                dtype="int16",
                channels=1,
                latency=self.audio_stream_latency,
                callback=self.callback,
            ):
                while True:
                    if self._is_stop_requested(stop_event) or self.is_speaking:
                        return None

                    try:
                        audio_bytes = self.q.get(timeout=0.1)
                    except queue.Empty:
                        time.sleep(0.01)
                        if time.monotonic() - listen_started_at >= self.speech_start_timeout and not heard_speech:
                            return None
                        continue

                    if recognizer.AcceptWaveform(audio_bytes):
                        result = json.loads(recognizer.Result())
                        text = result.get("text", "").strip()
                        if text:
                            final_text = text
                            heard_speech = True
                            silence_started_at = time.monotonic()
                        elif heard_speech:
                            if silence_started_at is None:
                                silence_started_at = time.monotonic()
                            elif time.monotonic() - silence_started_at >= self.pause_threshold:
                                break
                    else:
                        partial = json.loads(recognizer.PartialResult()).get("partial", "").strip()
                        if partial:
                            last_partial = partial
                            heard_speech = True
                            silence_started_at = None
                        elif heard_speech:
                            if silence_started_at is None:
                                silence_started_at = time.monotonic()
                            elif time.monotonic() - silence_started_at >= self.pause_threshold:
                                break
                        elif time.monotonic() - listen_started_at >= self.speech_start_timeout:
                            return None

                    time.sleep(0.01)
        except Exception as error:
            print(f"Microphone error: {error}")
            print("Voice failed, using text input")
            self.last_listen_error = True
            return None

        final_result = json.loads(recognizer.FinalResult()).get("text", "").strip()
        command = final_result or final_text or last_partial
        command = self._normalize_text(command)
        command = self.memory_manager.correct_command_with_stored_name(command)
        if not command:
            return None

        print(f"You: {command}")
        self._maybe_start_whisper_warmup()
        return command.lower()

    def callback(self, indata, frames, time_info, status):
        if status:
            print("Mic status:", status)
            return

        try:
            self.q.put(bytes(indata), block=False)
        except Exception:
            pass

    def _capture_interrupt_command(self, spoken_chunk):
        if not self.enable_whisper:
            return None

        if self.whisper_model is None or self._ensure_whisper_dependencies() is False:
            return None

        chunk_frames = int(self.interrupt_chunk_duration * self.sample_rate)
        max_wait_chunks = max(1, int(self.interrupt_poll_seconds / self.interrupt_chunk_duration))
        pre_speech_chunks = deque(
            maxlen=max(1, int(self.pre_speech_buffer_duration / self.interrupt_chunk_duration))
        )
        activation_count = 0
        detected_seed_chunks = None

        try:
            with self.sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=chunk_frames,
                latency=self.audio_stream_latency,
            ) as stream:
                for _ in range(max_wait_chunks):
                    chunk, overflowed = stream.read(chunk_frames)
                    chunk = self.np.squeeze(chunk)
                    pre_speech_chunks.append(chunk.copy())

                    if overflowed:
                        self._report_audio_overflow()

                    if self._measure_audio_level(chunk) >= self.interrupt_energy_threshold:
                        activation_count += 1
                    else:
                        activation_count = 0

                    if activation_count >= self.interrupt_activation_chunks:
                        detected_seed_chunks = list(pre_speech_chunks)
                        break
        except Exception:
            return None

        if not detected_seed_chunks:
            return None

        audio = self._record_until_silence(
            seed_chunks=detected_seed_chunks,
            skip_ambient=True,
            allow_during_speaking=True,
        )
        command = self._transcribe_audio(audio, print_user=False)
        if not command:
            return None

        if self._looks_like_echo(command, spoken_chunk):
            return None

        return command

    def _transcribe_audio(self, audio, listen_started_at=None, print_user=False):
        audio = self.np.squeeze(audio)
        if audio.size == 0:
            return None

        if self.np.max(self.np.abs(audio)) < 0.01:
            return None

        try:
            segments, _ = self.whisper_model.transcribe(
                audio,
                language="en",
                vad_filter=True,
            )
        except Exception as error:
            print(f"Whisper transcription error: {error}")
            self.last_listen_error = True
            return None

        transcript_parts = [segment.text.strip() for segment in segments if segment.text.strip()]
        command = " ".join(transcript_parts)
        command = self._normalize_text(command)
        command = self.memory_manager.correct_command_with_stored_name(command)

        if not command:
            return None

        if listen_started_at is not None and self._should_ignore_echo(command, listen_started_at):
            return None

        if print_user:
            print(f"You: {command}")

        return command.lower()

    def _record_until_silence(
        self,
        seed_chunks=None,
        skip_ambient=False,
        allow_during_speaking=False,
        stop_event=None,
    ):
        chunk_frames = int(self.chunk_duration * self.sample_rate)
        ambient_chunks = 0 if skip_ambient else max(1, int(self.ambient_noise_duration / self.chunk_duration))
        pre_speech_chunks = deque(
            maxlen=max(1, int(self.pre_speech_buffer_duration / self.chunk_duration))
        )
        recorded_chunks = [chunk.copy() for chunk in (seed_chunks or [])]
        speech_detected = bool(recorded_chunks)
        silence_duration = 0.0
        recorded_duration = len(recorded_chunks) * self.chunk_duration
        ambient_levels = []
        waiting_for_speech = 0.0

        with self.sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=chunk_frames,
            latency=self.audio_stream_latency,
        ) as stream:
            for _ in range(ambient_chunks):
                chunk, overflowed = stream.read(chunk_frames)
                chunk = self.np.squeeze(chunk)
                ambient_levels.append(self._measure_audio_level(chunk))
                pre_speech_chunks.append(chunk.copy())
                if overflowed:
                    self._report_audio_overflow()

            if seed_chunks:
                pre_speech_chunks.clear()
                for chunk in seed_chunks[-pre_speech_chunks.maxlen :]:
                    pre_speech_chunks.append(chunk.copy())

            ambient_level = float(self.np.median(ambient_levels)) if ambient_levels else 0.0
            speech_threshold = max(
                self.energy_threshold,
                ambient_level * self.ambient_multiplier + 0.005,
            )
            speech_threshold = min(speech_threshold, self.max_speech_threshold)

            while True:
                if self._is_stop_requested(stop_event):
                    return self.np.array([])

                if self.is_speaking and not allow_during_speaking:
                    return self.np.array([])

                chunk, overflowed = stream.read(chunk_frames)
                chunk = self.np.squeeze(chunk)
                current_level = self._measure_audio_level(chunk)

                if overflowed:
                    self._report_audio_overflow()

                if not speech_detected:
                    pre_speech_chunks.append(chunk.copy())
                    waiting_for_speech += self.chunk_duration
                    if current_level >= speech_threshold:
                        speech_detected = True
                        recorded_chunks.extend(list(pre_speech_chunks))
                        silence_duration = 0.0
                        waiting_for_speech = 0.0
                    elif waiting_for_speech >= self.speech_start_timeout:
                        return self.np.array([])
                    continue

                recorded_chunks.append(chunk.copy())
                recorded_duration += self.chunk_duration

                if current_level >= speech_threshold:
                    silence_duration = 0.0
                else:
                    silence_duration += self.chunk_duration
                    if silence_duration >= self.pause_threshold:
                        break

                if recorded_duration >= self.max_record_seconds:
                    break

        if not speech_detected or not recorded_chunks:
            return self.np.array([])

        return self.np.concatenate(recorded_chunks)

    def _measure_audio_level(self, chunk):
        if chunk.size == 0:
            return 0.0

        return float(self.np.max(self.np.abs(chunk)))

    def _wait_for_listen_window(self):
        if not self.last_speech_finished_at:
            return

        ready_at = self.last_speech_finished_at + self.listen_resume_delay
        while time.monotonic() < ready_at:
            time.sleep(0.05)

    def _should_ignore_echo(self, text, listen_started_at):
        if not self.last_spoken_text:
            return False

        if time.monotonic() - listen_started_at > self.echo_guard_duration:
            return False

        return self._looks_like_echo(text, self.last_spoken_text)

    def _looks_like_echo(self, text, reference_text):
        normalized_text = self._normalize_text(text)
        normalized_reference = self._normalize_text(reference_text)
        if not normalized_text or not normalized_reference:
            return False

        threshold = self.echo_similarity_threshold
        if len(normalized_reference.split()) <= 3:
            threshold = self.short_echo_similarity_threshold

        similarity = SequenceMatcher(None, normalized_text, normalized_reference).ratio()
        return similarity >= threshold

    def _is_stop_requested(self, stop_event):
        return stop_event is not None and stop_event.is_set()

    def _normalize_text(self, text):
        cleaned_text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        return " ".join(cleaned_text.split())

    def _ensure_whisper_model(self):
        if self.whisper_model is not None:
            return self.whisper_model

        if not self._ensure_whisper_dependencies():
            return None

        self._start_whisper_warmup()
        return self.whisper_model

    def _ensure_whisper_dependencies(self):
        if self.whisper_model_class is not None and self.np is not None and self.sd is not None:
            return True

        if self.whisper_import_attempted:
            return False

        self.whisper_import_attempted = True
        try:
            import numpy as np
            import sounddevice as sd
            from faster_whisper import WhisperModel
        except Exception as error:
            print(f"Whisper dependency error: {error}")
            self.np = None
            self.sd = None
            self.whisper_model_class = None
            return False

        self.np = np
        self.sd = sd
        self.whisper_model_class = WhisperModel
        return True

    def _ensure_vosk_model(self):
        if self.vosk_model is not None:
            return self.vosk_model

        if not self._ensure_vosk_dependencies():
            return None

        if not self.vosk_model_path.exists():
            return None

        try:
            self.vosk_model = self.vosk_model_class(str(self.vosk_model_path))
        except Exception as error:
            print(f"Vosk model error: {error}")
            self.vosk_model = None

        return self.vosk_model

    def _ensure_vosk_dependencies(self):
        if (
            self.vosk_model_class is not None
            and self.vosk_recognizer_class is not None
            and self.sd is not None
        ):
            return True

        if self.vosk_import_attempted:
            return False

        self.vosk_import_attempted = True
        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model, SetLogLevel
        except Exception:
            self.vosk_model_class = None
            self.vosk_recognizer_class = None
            return False

        SetLogLevel(-1)
        self.sd = sd
        self.vosk_model_class = Model
        self.vosk_recognizer_class = KaldiRecognizer
        return True

    def _ensure_sounddevice(self):
        if self.sd is not None:
            return True

        try:
            import sounddevice as sd
        except Exception:
            return False

        self.sd = sd
        return True

    def reset_microphone(self):
        self.recognizer = None
        self.microphone = None
        self.pending_command = None

        if sr is None:
            return

        try:
            self.recognizer = sr.Recognizer()
            self.recognizer.pause_threshold = self.pause_threshold
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.microphone = sr.Microphone()
        except Exception as error:
            print(f"Microphone reset error: {error}")
            self.recognizer = None
            self.microphone = None

        self._refresh_voice_backend()

    def _split_speech_chunks(self, text):
        chunks = []

        for line in text.split("\n"):
            stripped_line = line.strip()
            if not stripped_line:
                continue

            wrapped_parts = textwrap.wrap(
                stripped_line,
                width=300,
                break_long_words=False,
                break_on_hyphens=False,
            )
            if wrapped_parts:
                chunks.extend(wrapped_parts)
            else:
                chunks.append(stripped_line)

        return chunks

    def accept_typed_command(self, typed_command):
        cleaned_command = typed_command.strip()
        if not cleaned_command:
            return None

        print(f"You: {cleaned_command}")
        self._maybe_start_whisper_warmup()
        return cleaned_command

    def get_input_prompt(self):
        self._refresh_voice_backend()
        if self.voice_backend in {"vosk", "whisper", "speech_recognition"}:
            return "Listening... (speak now)"
        if self.voice_backend == "warming_up":
            return "Voice model is loading. You can type your command."
        return "Voice input unavailable right now. You can type your command."

    def has_voice_input(self):
        self._refresh_voice_backend()
        return self.voice_backend in {"vosk", "whisper", "speech_recognition"}

    def _refresh_voice_backend(self):
        if self.recognizer is not None and self.microphone is not None:
            self.voice_backend = "speech_recognition"
            return

        if self.enable_whisper and self.whisper_model is not None:
            self.voice_backend = "whisper"
            return

        if self._can_use_vosk_backend():
            self.voice_backend = "vosk"
            return

        if self.enable_whisper and self.whisper_warmup_in_progress:
            self.voice_backend = "warming_up"
            return

        self.voice_backend = "text"

    def _can_use_vosk_backend(self):
        if not self.vosk_model_path.exists():
            return False

        if not self._ensure_vosk_dependencies():
            return False

        return self._has_input_device()

    def _can_use_whisper_backend(self):
        return self.whisper_model is not None

    def _has_input_device(self):
        if self.sd is None:
            return False

        try:
            default_input, _ = self.sd.default.device
            if isinstance(default_input, int) and default_input >= 0:
                return True

            devices = self.sd.query_devices()
            return any(device.get("max_input_channels", 0) > 0 for device in devices)
        except Exception:
            return False

    def _start_whisper_warmup(self):
        if self.whisper_warmup_started:
            return

        self.whisper_warmup_started = True
        self.whisper_warmup_in_progress = True
        self.whisper_warmup_thread = threading.Thread(
            target=self._warmup_whisper_model,
            daemon=True,
        )
        self.whisper_warmup_thread.start()

    def _maybe_start_whisper_warmup(self):
        if not self.enable_whisper:
            return

        if self.whisper_warmup_started or self.whisper_model is not None:
            return

        self._start_whisper_warmup()

    def _warmup_whisper_model(self):
        try:
            if not self._ensure_whisper_dependencies():
                self.whisper_model_error = "Whisper dependencies are not available."
                self.whisper_model = None
                return

            self.whisper_model = self.whisper_model_class("base", compute_type="int8")
            self.whisper_model_error = None
        except Exception as error:
            print(f"Whisper model error: {error}")
            self.whisper_model = None
            self.whisper_model_error = str(error)
        finally:
            self.whisper_warmup_in_progress = False
            self._refresh_voice_backend()

    def _announce_voice_status_once(self):
        if self.voice_status_announced:
            return

        if self.voice_backend == "warming_up":
            print("Voice input is still loading. You can type your command meanwhile.")
        elif self.voice_backend == "text":
            print("Voice input is unavailable. Falling back to typed input.")

        self.voice_status_announced = True

    def _report_audio_overflow(self):
        now = time.monotonic()
        if now - self.last_audio_overflow_warning_at < self.audio_overflow_warning_interval:
            return

        print("Microphone warning: audio input overflow detected.")
        self.last_audio_overflow_warning_at = now

    def _reset_vosk_queue(self):
        while True:
            try:
                self.q.get_nowait()
            except queue.Empty:
                break
