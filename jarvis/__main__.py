"""
JARVIS Entry Point
Run with: python -m jarvis
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="J.A.R.V.I.S. — Just A Rather Very Intelligent System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python -m jarvis                  Auto-detect voice/text mode
  python -m jarvis --text           Text-only mode (no microphone needed)
  python -m jarvis --no-voice       Disable spoken responses
  python -m jarvis --text --no-voice  Silent text mode (chat only)
""",
    )

    parser.add_argument(
        "--text",
        action="store_true",
        help="Force text input mode (ignore microphone)",
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Force voice input mode (requires microphone)",
    )
    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Disable voice output (text responses only)",
    )

    args = parser.parse_args()

    # Determine input mode
    if args.text and args.voice:
        print("Error: Cannot use both --text and --voice")
        sys.exit(1)

    if args.text:
        input_mode = "text"
    elif args.voice:
        input_mode = "voice"
    else:
        input_mode = "auto"

    voice_output = not args.no_voice

    # Launch Jarvis
    from jarvis.core import Jarvis

    jarvis = Jarvis(voice_output=voice_output, input_mode=input_mode)
    jarvis.run()


if __name__ == "__main__":
    main()
