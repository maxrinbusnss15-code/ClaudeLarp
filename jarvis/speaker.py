"""
JARVIS Speaker — Text-to-Speech Module
Converts text responses into spoken audio with a refined British voice.
"""

import asyncio
import os
import tempfile
import threading

from jarvis.config import (
    AUDIO_TEMP_DIR,
    TTS_VOICE,
    TTS_RATE,
    TTS_VOLUME,
    TTS_PITCH,
    TTS_FALLBACK_RATE,
)


class Speaker:
    """Text-to-speech engine with edge-tts (primary) and pyttsx3 (fallback)."""

    def __init__(self):
        self._edge_tts_available = False
        self._pyttsx3_available = False
        self._pygame_available = False
        self._engine = None

        os.makedirs(AUDIO_TEMP_DIR, exist_ok=True)
        self._detect_backends()

    def _detect_backends(self):
        """Check which TTS backends are available."""
        try:
            import edge_tts  # noqa: F401
            self._edge_tts_available = True
        except ImportError:
            pass

        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", TTS_FALLBACK_RATE)
            # Try to select a male voice
            voices = self._engine.getProperty("voices")
            for voice in voices:
                if "male" in voice.name.lower() or "english" in voice.name.lower():
                    self._engine.setProperty("voice", voice.id)
                    break
            self._pyttsx3_available = True
        except Exception:
            pass

        try:
            import pygame.mixer
            pygame.mixer.init()
            self._pygame_available = True
        except Exception:
            pass

    @property
    def is_available(self) -> bool:
        return self._edge_tts_available or self._pyttsx3_available

    @property
    def backend_name(self) -> str:
        if self._edge_tts_available:
            return f"Edge-TTS ({TTS_VOICE})"
        if self._pyttsx3_available:
            return "pyttsx3 (offline)"
        return "None"

    def speak(self, text: str):
        """Speak the given text aloud. Blocks until speech is complete."""
        if not text:
            return

        if self._edge_tts_available:
            self._speak_edge_tts(text)
        elif self._pyttsx3_available:
            self._speak_pyttsx3(text)

    def speak_async(self, text: str):
        """Speak in a background thread (non-blocking)."""
        thread = threading.Thread(target=self.speak, args=(text,), daemon=True)
        thread.start()
        return thread

    def _speak_edge_tts(self, text: str):
        """Use Microsoft Edge TTS for high-quality voice synthesis."""
        try:
            import edge_tts

            audio_path = os.path.join(
                AUDIO_TEMP_DIR,
                f"jarvis_{hash(text) & 0xFFFFFFFF}.mp3",
            )

            async def _generate():
                communicate = edge_tts.Communicate(
                    text,
                    voice=TTS_VOICE,
                    rate=TTS_RATE,
                    volume=TTS_VOLUME,
                    pitch=TTS_PITCH,
                )
                await communicate.save(audio_path)

            # Run the async edge-tts generation
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # We're inside an existing event loop — run in a new thread
                new_loop = asyncio.new_event_loop()
                thread = threading.Thread(
                    target=lambda: new_loop.run_until_complete(_generate()),
                    daemon=True,
                )
                thread.start()
                thread.join()
                new_loop.close()
            else:
                asyncio.run(_generate())

            # Play the audio
            self._play_audio(audio_path)

            # Clean up
            try:
                os.remove(audio_path)
            except OSError:
                pass

        except Exception:
            # Fall back to pyttsx3
            if self._pyttsx3_available:
                self._speak_pyttsx3(text)

    def _speak_pyttsx3(self, text: str):
        """Use pyttsx3 for offline TTS."""
        if self._engine:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                pass

    def _play_audio(self, file_path: str):
        """Play an audio file."""
        if self._pygame_available:
            self._play_with_pygame(file_path)
        else:
            # Try system command as last resort
            self._play_with_system(file_path)

    def _play_with_pygame(self, file_path: str):
        """Play audio using pygame mixer."""
        try:
            import pygame.mixer
            import time

            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except Exception:
            self._play_with_system(file_path)

    def _play_with_system(self, file_path: str):
        """Play audio using system commands (mpv, ffplay, aplay)."""
        players = [
            f"mpv --no-video --really-quiet '{file_path}'",
            f"ffplay -nodisp -autoexit -loglevel quiet '{file_path}'",
            f"aplay '{file_path}'",
        ]
        for cmd in players:
            if os.system(cmd + " 2>/dev/null") == 0:
                return
