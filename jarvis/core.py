"""
JARVIS Core — The main orchestrator that wires everything together.
Listen → Think → Speak loop with text and voice input modes.
"""

import signal
import sys
import time

from jarvis.config import USER_TITLE, ASSISTANT_NAME
from jarvis.brain import Brain
from jarvis.listener import Listener
from jarvis.speaker import Speaker
from jarvis.commands import try_builtin
from jarvis import ui


class Jarvis:
    """Main Jarvis application engine."""

    def __init__(self, voice_output: bool = True, input_mode: str = "auto"):
        """
        Args:
            voice_output: Whether to speak responses aloud.
            input_mode: "voice", "text", or "auto" (voice if mic available, else text).
        """
        self.brain = Brain()
        self.listener = Listener()
        self.speaker = Speaker()

        self.voice_enabled = voice_output
        self.running = False

        # Determine input mode
        if input_mode == "auto":
            self.input_mode = "voice" if self.listener.is_available else "text"
        else:
            self.input_mode = input_mode

    def run(self):
        """Main entry point — boot up and enter the command loop."""
        self._setup_signal_handlers()

        # ── Boot Sequence ──
        ui.print_boot_sequence()
        ui.print_separator()

        # Show system status
        ui.print_mode_status(
            self.input_mode,
            self.voice_enabled,
            self.speaker.backend_name,
            self.listener.is_available,
        )
        ui.print_separator()

        # Greeting
        greeting = self._get_greeting()
        ui.print_jarvis_response(greeting)
        if self.voice_enabled and self.speaker.is_available:
            self.speaker.speak(greeting)

        ui.print_separator()
        ui.print_status('Type "help" for commands. Say or type "goodbye" to exit.')
        ui.print_separator()

        # ── Main Loop ──
        self.running = True
        while self.running:
            try:
                user_input = self._get_input()

                if user_input is None:
                    continue

                user_input = user_input.strip()
                if not user_input:
                    continue

                # Handle meta-commands (these don't go through the brain)
                if self._handle_meta_command(user_input):
                    continue

                # Show user input
                ui.print_user_input(user_input)

                # Check for exit
                if self._is_exit(user_input):
                    self._shutdown()
                    break

                # Process the input
                ui.print_thinking()
                response = self._process(user_input)

                # Display and speak the response
                ui.print_jarvis_response(response)
                if self.voice_enabled and self.speaker.is_available:
                    ui.print_speaking()
                    self.speaker.speak(response)

                ui.print_separator()

            except KeyboardInterrupt:
                self._shutdown()
                break
            except Exception as e:
                ui.print_error(f"System error: {e}")

    def _get_input(self) -> str | None:
        """Get input from voice or text depending on mode."""
        if self.input_mode == "voice":
            ui.print_listening()
            text = self.listener.listen_for_command()
            if text:
                ui.print_user_input(text)
                return text
            return None
        else:
            return ui.prompt_input()

    def _process(self, user_input: str) -> str:
        """Route input to built-in commands or AI brain."""
        # Try built-in commands first (instant, no API call)
        builtin_result = try_builtin(user_input)
        if builtin_result:
            return builtin_result

        # Otherwise, send to the AI brain
        return self.brain.think(user_input)

    def _handle_meta_command(self, text: str) -> bool:
        """Handle system-level commands. Returns True if handled."""
        cmd = text.lower().strip()

        if cmd == "help":
            ui.print_help()
            return True

        if cmd == "clear":
            ui.console.clear()
            return True

        if cmd == "reset":
            self.brain.reset_memory()
            msg = f"Memory banks cleared, {USER_TITLE}. Starting with a fresh slate."
            ui.print_jarvis_response(msg)
            if self.voice_enabled and self.speaker.is_available:
                self.speaker.speak(msg)
            return True

        if cmd == "voice on":
            self.voice_enabled = True
            ui.print_status("Voice output enabled.")
            return True

        if cmd == "voice off":
            self.voice_enabled = False
            ui.print_status("Voice output disabled.")
            return True

        if cmd == "mode voice":
            if self.listener.is_available:
                self.input_mode = "voice"
                ui.print_status("Switched to voice input mode.")
            else:
                ui.print_error("Microphone is not available. Install PyAudio and check your mic.")
            return True

        if cmd == "mode text":
            self.input_mode = "text"
            ui.print_status("Switched to text input mode.")
            return True

        if cmd == "status":
            ui.print_mode_status(
                self.input_mode,
                self.voice_enabled,
                self.speaker.backend_name,
                self.listener.is_available,
            )
            return True

        return False

    def _is_exit(self, text: str) -> bool:
        """Check if the user wants to exit."""
        exit_phrases = (
            "quit", "exit", "goodbye", "good bye", "bye",
            "shut down", "shutdown", "power off", "terminate",
            "go to sleep", "that will be all",
        )
        return text.lower().strip() in exit_phrases

    def _get_greeting(self) -> str:
        """Generate a time-aware greeting."""
        hour = time.localtime().tm_hour
        if hour < 12:
            tod = "Good morning"
        elif hour < 17:
            tod = "Good afternoon"
        elif hour < 21:
            tod = "Good evening"
        else:
            tod = "Good evening"

        return (
            f"{tod}, {USER_TITLE}. I am {ASSISTANT_NAME}, your personal AI assistant. "
            f"All systems are online and at your disposal."
        )

    def _shutdown(self):
        """Graceful shutdown sequence."""
        self.running = False
        farewell = f"Shutting down. It's been a pleasure, {USER_TITLE}. Until next time."
        ui.print_jarvis_response(farewell)
        if self.voice_enabled and self.speaker.is_available:
            self.speaker.speak(farewell)
        ui.print_goodbye()

    def _setup_signal_handlers(self):
        """Handle SIGINT/SIGTERM gracefully."""
        def _handler(sig, frame):
            self._shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)
