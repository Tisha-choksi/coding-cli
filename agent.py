"""Agent conversation loop.

Phase 1: the agent just forwards conversation history to the LLM and
returns its reply. No tool use, no autonomous behavior yet.
"""

import config
import llm


class Agent:
    def __init__(self):
        self.messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]

    def send(self, user_input):
        """Send a user message and return the assistant's reply (or None on error)."""
        self.messages.append({"role": "user", "content": user_input})

        reply = llm.stream_chat(self.messages)

        if reply is None:
            self.messages.pop()  # drop the failed turn so it doesn't pollute context
            return None

        self.messages.append({"role": "assistant", "content": reply})
        return reply
