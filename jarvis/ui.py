"""
JARVIS Terminal UI — Rich-based HUD display
"""

import datetime
import random

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box

from jarvis.config import (
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_ACCENT,
    COLOR_SUCCESS,
    COLOR_ERROR,
    COLOR_DIM,
    COLOR_USER,
    COLOR_JARVIS,
    ASSISTANT_NAME,
    USER_TITLE,
)

console = Console()

# ─── ASCII Art ───────────────────────────────────────────────────────

JARVIS_LOGO = r"""
       ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
       ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
       ██║███████║██████╔╝██║   ██║██║███████╗
  ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
  ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
   ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
"""

ARC_REACTOR = r"""
          ╭─────────────╮
        ╭─┤  ╭───────╮  ├─╮
       │  │  │ ╭───╮ │  │  │
       │  │  │ │ ◉ │ │  │  │
       │  │  │ ╰───╯ │  │  │
        ╰─┤  ╰───────╯  ├─╯
          ╰─────────────╯
"""

BOOT_MESSAGES = [
    "Initializing neural interface...",
    "Loading personality matrix...",
    "Calibrating speech synthesis...",
    "Connecting to knowledge base...",
    "Running security protocols...",
    "Arc reactor at full capacity...",
    "All systems nominal.",
]

IDLE_QUOTES = [
    "Standing by for your command.",
    "All systems operational.",
    "Monitoring all channels.",
    "Awaiting instructions.",
    "At your service.",
    "Ready when you are.",
    "Systems nominal.",
]


def print_boot_sequence():
    """Display the dramatic Jarvis boot-up sequence."""
    import time

    console.clear()
    console.print()

    # Logo
    for line in JARVIS_LOGO.strip().split("\n"):
        console.print(f"  {line}", style=f"bold {COLOR_PRIMARY}")
        time.sleep(0.08)

    console.print()
    console.print(
        "  Just A Rather Very Intelligent System",
        style=f"italic {COLOR_SECONDARY}",
    )
    console.print(f"  v1.0.0 | Personal AI Assistant", style=f"{COLOR_DIM}")
    console.print()

    # Boot messages
    for msg in BOOT_MESSAGES:
        console.print(f"  [{COLOR_PRIMARY}]>[/{COLOR_PRIMARY}] {msg}", style=f"{COLOR_DIM}")
        time.sleep(0.25)

    console.print()
    console.print(
        f"  [{COLOR_SUCCESS}]✓[/{COLOR_SUCCESS}] All systems online. "
        f"Good day, {USER_TITLE}.",
        style=f"bold {COLOR_SUCCESS}",
    )
    console.print()


def print_separator():
    console.print(
        f"  {'─' * 60}",
        style=f"{COLOR_DIM}",
    )


def print_listening():
    """Show that Jarvis is listening for voice input."""
    console.print(
        f"\n  [{COLOR_ACCENT}]🎙  Listening...[/{COLOR_ACCENT}]",
    )


def print_thinking():
    """Show that Jarvis is processing."""
    console.print(
        f"  [{COLOR_SECONDARY}]⚡ Processing...[/{COLOR_SECONDARY}]",
    )


def print_speaking():
    """Show that Jarvis is speaking."""
    console.print(
        f"  [{COLOR_PRIMARY}]🔊 Speaking...[/{COLOR_PRIMARY}]",
    )


def print_user_input(text: str):
    """Display user's transcribed speech or typed input."""
    console.print(
        f"\n  [{COLOR_USER}]You:[/{COLOR_USER}] {text}",
    )


def print_jarvis_response(text: str):
    """Display Jarvis's response in a styled panel."""
    response_panel = Panel(
        Text(text, style="white"),
        title=f"[bold {COLOR_PRIMARY}]J.A.R.V.I.S.[/bold {COLOR_PRIMARY}]",
        border_style=COLOR_PRIMARY,
        padding=(0, 2),
        box=box.ROUNDED,
    )
    console.print(f"  ", end="")
    console.print(response_panel, width=70)


def print_error(text: str):
    """Display an error message."""
    console.print(f"\n  [{COLOR_ERROR}]⚠  {text}[/{COLOR_ERROR}]")


def print_status(text: str):
    """Display a status message."""
    console.print(f"  [{COLOR_DIM}]{text}[/{COLOR_DIM}]")


def print_help():
    """Display help / available commands."""
    table = Table(
        title="Available Commands",
        box=box.SIMPLE_HEAVY,
        title_style=f"bold {COLOR_PRIMARY}",
        border_style=COLOR_SECONDARY,
        show_header=True,
        header_style=f"bold {COLOR_ACCENT}",
    )
    table.add_column("Command", style=f"{COLOR_PRIMARY}", min_width=20)
    table.add_column("Description", style="white")

    commands = [
        ("help", "Show this help menu"),
        ("status / diagnostics", "System status report"),
        ("time", "Current time"),
        ("date", "Current date"),
        ("clear", "Clear the screen"),
        ("reset", "Reset conversation memory"),
        ("voice on/off", "Toggle voice output"),
        ("mode voice/text", "Switch input mode"),
        ("quit / exit / goodbye", "Shut down Jarvis"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print()
    console.print(table)
    console.print()
    console.print(
        f"  [{COLOR_DIM}]Or just speak naturally — I'll figure out the rest.[/{COLOR_DIM}]"
    )
    console.print()


def print_idle_status():
    """Print a random idle status message."""
    quote = random.choice(IDLE_QUOTES)
    console.print(f"  [{COLOR_DIM}]» {quote}[/{COLOR_DIM}]")


def print_mode_status(input_mode: str, voice_enabled: bool, tts_backend: str, stt_available: bool):
    """Show current mode configuration."""
    voice_status = f"[{COLOR_SUCCESS}]ON[/{COLOR_SUCCESS}]" if voice_enabled else f"[{COLOR_ERROR}]OFF[/{COLOR_ERROR}]"
    input_label = f"[{COLOR_PRIMARY}]{input_mode.upper()}[/{COLOR_PRIMARY}]"
    tts_label = f"[{COLOR_DIM}]{tts_backend}[/{COLOR_DIM}]"
    stt_label = (
        f"[{COLOR_SUCCESS}]Available[/{COLOR_SUCCESS}]" if stt_available
        else f"[{COLOR_ERROR}]Unavailable[/{COLOR_ERROR}]"
    )

    console.print(f"  Input: {input_label}  |  Voice Output: {voice_status}  |  TTS: {tts_label}  |  STT: {stt_label}")


def print_goodbye():
    """Farewell sequence."""
    console.print()
    console.print(
        f"  [{COLOR_PRIMARY}]Shutting down all systems...[/{COLOR_PRIMARY}]"
    )
    console.print(
        f"  [{COLOR_PRIMARY}]It's been a pleasure, {USER_TITLE}. "
        f"Until next time.[/{COLOR_PRIMARY}]"
    )
    console.print()

    # Dim the arc reactor
    for line in ARC_REACTOR.strip().split("\n"):
        console.print(f"  {line}", style=f"{COLOR_DIM}")

    console.print()


def get_prompt() -> str:
    """Get the styled input prompt string."""
    return f"  [{COLOR_ACCENT}]{USER_TITLE} >[/{COLOR_ACCENT}] "


def prompt_input() -> str:
    """Get text input from the user with a styled prompt."""
    try:
        return console.input(get_prompt())
    except (EOFError, KeyboardInterrupt):
        return "exit"
