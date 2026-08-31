"""Agent conversation loop.

Phase 2: the agent can now call read-only file tools (list_files,
read_file, file_exists) to explore the project before answering.
It still can't write/edit files or run commands -- that's a later phase.
"""
import json
import config
import llm
from tools.files import SCHEMAS, FUNCTIONS

MAX_TOOL_ROUNDS = 8


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

        fn = FUNCTIONS.get(name)
        if fn is None:
            output = f"Error: unknown tool '{name}'"
        else:
            arg_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
            print(f"[tool] {name}({arg_str})")
            try:
                output = fn(**args)
            except Exception as exc:
                output = f"Error running {name}: {exc}"

        content = output if isinstance(output, str) else json.dumps(output)
        self.messages.append({"role": "tool", "content": content})
