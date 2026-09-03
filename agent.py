"""Agent conversation loop.

Phase 4: the agent can now also run shell commands (run_command), e.g.
to run tests and see if a fix actually worked. Like file writes, it
never runs a command directly -- every mutating tool call goes through
a permission check (a y/N prompt to the user) first:

    LLM -> tool request -> agent -> permission check -> filesystem/shell
"""
import difflib
import json
import re

import config
import llm
from tools.files import (
    SCHEMAS as FILE_SCHEMAS,
    FUNCTIONS as FILE_FUNCTIONS,
    MUTATING as FILE_MUTATING,
    read_file,
)
from tools.terminal import (
    SCHEMAS as TERMINAL_SCHEMAS,
    FUNCTIONS as TERMINAL_FUNCTIONS,
    MUTATING as TERMINAL_MUTATING,
)

SCHEMAS = FILE_SCHEMAS + TERMINAL_SCHEMAS
FUNCTIONS = {**FILE_FUNCTIONS, **TERMINAL_FUNCTIONS}
MUTATING = FILE_MUTATING | TERMINAL_MUTATING

MAX_TOOL_ROUNDS = 20

# This local model occasionally leaks chat-template special tokens (used to
# mark tool calls/results in the prompt) into its own generated `content`
# arguments. Strip them before anything reaches the filesystem.
_TEMPLATE_ARTIFACT_RE = re.compile(r"</?tool_(?:call|response)>\n?")


def _sanitize_content(text):
    if not isinstance(text, str):
        return text
    return _TEMPLATE_ARTIFACT_RE.sub("", text)


class Agent:
    def __init__(self):
        self.messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]

    def send(self, user_input):
        """Send a user message, letting the model call tools as needed.

        Prints and returns the final assistant text reply, or None on error.
        """
        self.messages.append({"role": "user", "content": user_input})

        for _ in range(MAX_TOOL_ROUNDS):
            result = llm.chat(self.messages, tools=SCHEMAS)

            if result is None:
                self.messages.pop()
                return None

            content, tool_calls = result["content"], result["tool_calls"]

            assistant_msg = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            self.messages.append(assistant_msg)

            if not tool_calls:
                print(f"Agent: {content}")
                return content

            for call in tool_calls:
                self._run_tool_call(call)

        print(f"Agent: {content}")
        return content

    def _run_tool_call(self, call):
        name = call["function"]["name"]
        raw_args = call["function"].get("arguments") or {}
        args = raw_args if isinstance(raw_args, dict) else json.loads(raw_args)

        if "content" in args:
            args["content"] = _sanitize_content(args["content"])

        fn = FUNCTIONS.get(name)
        if fn is None:
            output = f"Error: unknown tool '{name}'"
        elif name in MUTATING and not self._confirm(name, args):
            target = args.get("path") or args.get("command", "<unknown>")
            output = (
                f"The user did NOT approve this {name} call ('{target}'). "
                "Do not repeat it; ask the user what they'd like instead if relevant."
            )
        else:
            arg_str = ", ".join(
                f"{k}={v!r}" for k, v in args.items() if k != "content"
            )
            print(f"[tool] {name}({arg_str})")
            try:
                output = fn(**args)
            except Exception as exc:
                output = f"Error running {name}: {exc}"

        content = output if isinstance(output, str) else json.dumps(output)
        self.messages.append({"role": "tool", "content": content})

    def _confirm(self, name, args):
        """Show the user what a mutating tool call would do and ask for approval."""
        path = args.get("path", "<unknown>")

        if name == "create_file":
            print(f"\n[permission] Agent wants to CREATE '{path}':")
            print("-" * 50)
            print(args.get("content", "") or "(empty file)")
            print("-" * 50)

        elif name == "edit_file":
            old = read_file(path)
            if not isinstance(old, str) or old.startswith("Error:"):
                old = ""
            new = args.get("content", "")
            diff = "".join(
                difflib.unified_diff(
                    old.splitlines(keepends=True),
                    new.splitlines(keepends=True),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                )
            )
            print(f"\n[permission] Agent wants to EDIT '{path}':")
            print(diff if diff else "(no changes)")

        elif name == "delete_file":
            print(f"\n[permission] Agent wants to DELETE '{path}'.")

        elif name == "run_command":
            print(f"\n[permission] Agent wants to RUN: {args.get('command', '<unknown>')}")

        prompt = "Run this command?" if name == "run_command" else "Apply this change?"
        answer = input(f"{prompt} [y/N]: ").strip().lower()
        return answer in ("y", "yes")
