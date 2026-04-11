"""
JARVIS Listener — Speech Recognition Module
Captures voice input from the microphone and converts it to text.
"""

import speech_recognition as sr
from jarvis.config import (
    WAKE_WORD,
    LISTEN_TIMEOUT,
    PHRASE_TIME_LIMIT,
    ENERGY_THRESHOLD,
    DYNAMIC_ENERGY,
)


class Listener:
    """Microphone-based speech recognition using Google's STT API."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = ENERGY_THRESHOLD
        self.recognizer.dynamic_energy_threshold = DYNAMIC_ENERGY
        self.microphone = None
        self._available = False
        self._init_microphone()

    def _init_microphone(self):
        """Try to initialize the microphone."""
        try:
            self.microphone = sr.Microphone()
            # Quick calibration for ambient noise
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            self._available = True
        except (OSError, AttributeError, ImportError):
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def calibrate(self, duration: float = 2.0):
        """Calibrate microphone for ambient noise levels."""
        if not self._available:
            return
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=duration)

    def listen(self) -> str | None:
        """
        Listen for speech and return transcribed text.
        Returns None if nothing was heard or recognition failed.
        """
        if not self._available:
            return None

        try:
            with self.microphone as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=LISTEN_TIMEOUT,
                    phrase_time_limit=PHRASE_TIME_LIMIT,
                )
            # Use Google's free STT API
            text = self.recognizer.recognize_google(audio)
            return text.strip() if text else None

        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            return None
        except Exception:
            return None

    def listen_for_wake_word(self) -> bool:
        """
        Listen specifically for the wake word.
        Returns True if wake word was detected.
        """
        text = self.listen()
        if text and WAKE_WORD.lower() in text.lower():
            return True
        return False

    def listen_for_command(self) -> str | None:
        """
        Listen for a command after the wake word has been detected.
        Strips the wake word from the beginning if present.
        """
        text = self.listen()
        if not text:
            return None

        # Remove wake word from start if user said "Jarvis, do something"
        lower = text.lower()
        if lower.startswith(WAKE_WORD.lower()):
            text = text[len(WAKE_WORD):].strip().lstrip(",").strip()
            if not text:
                return None

        return text
