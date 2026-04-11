"""
JARVIS Brain — AI reasoning powered by Claude
"""

import time
from anthropic import Anthropic
from jarvis.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, SYSTEM_PROMPT


class Brain:
    """Handles all AI reasoning and conversation memory."""

    def __init__(self):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
        self.conversation_history: list[dict] = []
        self.max_history = 50  # Keep last N exchanges to manage context

    @property
    def is_available(self) -> bool:
        return self.client is not None

    def think(self, user_input: str) -> str:
        """Process user input and return Jarvis's response."""
        if not self.is_available:
            return self._offline_response(user_input)

        self.conversation_history.append({
            "role": "user",
            "content": user_input,
        })

        # Trim history if it's getting long
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        try:
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=self.conversation_history,
            )
            reply = response.content[0].text

            self.conversation_history.append({
                "role": "assistant",
                "content": reply,
            })
            return reply

        except Exception as e:
            error_type = type(e).__name__
            return (
                f"I'm experiencing a temporary disruption in my neural network, {self._sir()}. "
                f"Error class: {error_type}. Shall I retry?"
            )

    def reset_memory(self):
        """Clear conversation history."""
        self.conversation_history.clear()

    def _sir(self) -> str:
        from jarvis.config import USER_TITLE
        return USER_TITLE

    def _offline_response(self, user_input: str) -> str:
        """Provide basic responses when no API key is configured."""
        text = user_input.lower().strip()

        if any(g in text for g in ("hello", "hi", "hey", "good morning", "good evening")):
            return f"Good day, {self._sir()}. I'm currently running in offline mode — my neural link to Claude is not configured. Set your ANTHROPIC_API_KEY to unlock my full capabilities."

        if "time" in text:
            return f"The current time is {time.strftime('%I:%M %p')}, {self._sir()}."

        if "name" in text:
            return f"I am J.A.R.V.I.S. — Just A Rather Very Intelligent System. At your service, {self._sir()}."

        return (
            f"I'm operating in offline mode, {self._sir()}. My responses are limited without "
            "a connection to Claude. Please set the ANTHROPIC_API_KEY environment variable "
            "to enable my full cognitive abilities."
        )
