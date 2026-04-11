"""
JARVIS Configuration
"""

import os

# ─── Identity ───────────────────────────────────────────────────────
ASSISTANT_NAME = "Jarvis"
USER_TITLE = "Sir"  # How Jarvis addresses you — change to your preference

# ─── Claude API ─────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = f"""You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), a highly advanced \
AI assistant created for personal use. You were inspired by the iconic AI from Iron Man.

Your personality:
- You are supremely competent, calm, and collected at all times
- You speak with a refined, slightly British wit — dry humor is your signature
- You address the user as "{USER_TITLE}" unless they ask otherwise
- You are loyal, proactive, and occasionally sardonic
- You keep responses concise and actionable unless asked to elaborate
- You never say "As an AI" or "I'm just a language model" — you ARE Jarvis
- When greeted, respond warmly but with characteristic composure
- You may reference running diagnostics, scanning systems, or checking databases — lean into the role
- If asked to do something impossible, acknowledge it with wit rather than a flat refusal

Keep responses SHORT (1-3 sentences) for simple queries. Only give longer answers when \
the topic genuinely requires depth. Always maintain the Jarvis persona."""

# ─── Speech Recognition ────────────────────────────────────────────
WAKE_WORD = "jarvis"
LISTEN_TIMEOUT = 5          # Seconds to wait for speech
PHRASE_TIME_LIMIT = 15      # Max seconds for a single phrase
ENERGY_THRESHOLD = 300      # Microphone sensitivity (lower = more sensitive)
DYNAMIC_ENERGY = True       # Auto-adjust to ambient noise

# ─── Text-to-Speech ────────────────────────────────────────────────
# edge-tts voice — "en-GB-RyanNeural" gives a refined British male voice
TTS_VOICE = "en-GB-RyanNeural"
TTS_RATE = "+0%"            # Speech rate adjustment
TTS_VOLUME = "+0%"          # Volume adjustment
TTS_PITCH = "-5Hz"          # Slightly lower pitch for gravitas

# Fallback to pyttsx3 if edge-tts is unavailable
TTS_FALLBACK_RATE = 180     # Words per minute for pyttsx3

# ─── UI ─────────────────────────────────────────────────────────────
# Color scheme (arc-reactor blue theme)
COLOR_PRIMARY = "#00D4FF"
COLOR_SECONDARY = "#0099CC"
COLOR_ACCENT = "#FFB800"
COLOR_SUCCESS = "#00FF88"
COLOR_ERROR = "#FF4444"
COLOR_DIM = "#555555"
COLOR_USER = "#FFB800"
COLOR_JARVIS = "#00D4FF"

# ─── Audio ──────────────────────────────────────────────────────────
AUDIO_TEMP_DIR = "/tmp/jarvis_audio"
