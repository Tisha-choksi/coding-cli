"""Context management.

The raw conversation the agent needs (system prompt + user request +
project structure + relevant files + tool outputs + previous actions +
errors) grows without bound over a long session. ContextManager keeps
it in structured pieces instead of one flat list, and -- when the
rolling conversation window gets too large -- folds the oldest part of
it into a short summary via the LLM instead of just dropping it:

    old conversation -> summarizer -> task summary -> agent continues
"""

# Rough token proxy (~4 chars/token); this model's real context window
# is much larger (32k tokens for qwen2.5-coder:7b), but compressing well
# before that keeps the raw history small and the model's attention on
# recent, relevant turns instead of a huge transcript.
MAX_HISTORY_CHARS = 40000

# Never compress away the most recent messages -- always keep at least
# this many raw, and always cut on a clean user-turn boundary so we
# never strand a "tool" message without the assistant call that led to it.
KEEP_RECENT_MESSAGES = 10

MAX_TRACKED_ERRORS = 10
MAX_TRACKED_TOOL_RESULTS = 30


class ContextManager:
    def __init__(self, system_prompt):
        self.system_prompt = system_prompt
        self.task = None               # the latest user request
        self.relevant_files = {}       # path -> "read" | "created" | "edited" | "deleted"
        self.tool_results = []         # bounded log of {"tool", "args", "output"}
        self.errors = []               # bounded log of recent error/failure strings
        self.summary = None            # condensed text of everything compressed away
        self.history = []              # rolling window of raw role-tagged messages

    # ---- recording ----

    def set_task(self, user_input):
        self.task = user_input
        self.history.append({"role": "user", "content": user_input})

    def add_assistant(self, content, tool_calls=None):
        msg = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.history.append(msg)

    def add_tool_result(self, name, args, output):
        text = output if isinstance(output, str) else str(output)
        self._track(name, args, text)
        self.history.append({"role": "tool", "content": text})

    def drop_last(self):
        """Undo the most recently recorded message, e.g. after a failed LLM call."""
        if self.history:
            self.history.pop()

    def _track(self, name, args, text):
        path = args.get("path")
        if path:
            if name == "read_file":
                self.relevant_files.setdefault(path, "read")
            elif name == "create_file":
                self.relevant_files[path] = "created"
            elif name == "edit_file":
                self.relevant_files[path] = "edited"
            elif name == "delete_file":
                self.relevant_files[path] = "deleted"

        self.tool_results.append({"tool": name, "args": args, "output": text})
        self.tool_results = self.tool_results[-MAX_TRACKED_TOOL_RESULTS:]

        is_error = text.startswith("Error") or text.startswith("Blocked") or (
            "exit code: " in text and "exit code: 0" not in text
        )
        if is_error:
            self.errors.append(text[:300])
            self.errors = self.errors[-MAX_TRACKED_ERRORS:]

    # ---- assembly ----

    def build_messages(self):
        """Build the actual message list to send to the LLM for this turn."""
        messages = [{"role": "system", "content": self.system_prompt}]

        state_lines = []
        if self.task:
            state_lines.append(f"Current task: {self.task}")
        if self.summary:
            state_lines.append(f"Summary of earlier work in this session:\n{self.summary}")
        if self.relevant_files:
            files = "\n".join(f"- {p} ({a})" for p, a in self.relevant_files.items())
            state_lines.append(f"Files touched so far this session:\n{files}")
        if self.errors:
            errs = "\n".join(f"- {e}" for e in self.errors[-5:])
            state_lines.append(f"Recent errors/failures encountered:\n{errs}")

        if state_lines:
            messages.append({"role": "system", "content": "\n\n".join(state_lines)})

        messages.extend(self.history)
        return messages

    # ---- compression ----

    def size_chars(self):
        return sum(len(m.get("content") or "") for m in self.history)

    def needs_compression(self):
        return self.size_chars() > MAX_HISTORY_CHARS and len(self.history) > KEEP_RECENT_MESSAGES

    def compress(self, summarize_fn):
        """Fold everything before the recent tail into `summary` via `summarize_fn`.

        `summarize_fn(existing_summary, old_conversation_text) -> str | None`.
        Returns True if compression happened (or was attempted), False if
        there was nothing worth compressing yet.
        """
        if not self.needs_compression():
            return False

        # Cut on the first user-turn boundary at or after the "keep recent"
        # mark, so `recent` always starts clean rather than mid tool-call.
        earliest_cut = len(self.history) - KEEP_RECENT_MESSAGES
        split = next(
            (i for i in range(earliest_cut, len(self.history)) if self.history[i]["role"] == "user"),
            None,
        )
        if not split:
            return False  # nothing clean to cut yet -- try again once more accumulates

        old, recent = self.history[:split], self.history[split:]
        old_text = "\n".join(_render(m) for m in old)

        new_summary = summarize_fn(self.summary, old_text)
        self.summary = new_summary if new_summary else self.summary
        self.history = recent
        return True

    # ---- debugging / visibility ----

    def status(self):
        lines = [
            f"Task: {self.task or '(none yet)'}",
            f"History: {len(self.history)} messages, ~{self.size_chars()} chars "
            f"(compresses above {MAX_HISTORY_CHARS})",
            f"Summary: {f'{len(self.summary)} chars' if self.summary else '(none yet)'}",
        ]
        if self.summary:
            lines.append(f"  {self.summary}")
        lines.append(f"Files touched ({len(self.relevant_files)}):")
        for path, action in self.relevant_files.items():
            lines.append(f"  - {path} ({action})")
        if self.errors:
            lines.append(f"Recent errors ({len(self.errors)}):")
            for err in self.errors[-5:]:
                lines.append(f"  - {err}")
        return "\n".join(lines)


def _render(message):
    role = message["role"]
    content = message.get("content") or ""
    if role == "assistant" and message.get("tool_calls"):
        calls = ", ".join(
            f"{tc['function']['name']}({tc['function'].get('arguments')})"
            for tc in message["tool_calls"]
        )
        content = f"{content} [called: {calls}]".strip()
    return f"[{role}] {content}"
