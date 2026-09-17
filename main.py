"""
Coding agent CLI.
Reads a prompt from the terminal and lets the agent use its tools
(read/search/edit files, run commands) to carry it out, checking in
with the user before anything mutates the filesystem or shell.
"""
import sys
import config
from agent import Agent
def main():
    print(f"Coding agent CLI -- model: {config.MODEL}")
    print("Type your request, 'context' to inspect agent state, or 'exit' / 'quit' to leave.\n")
    agent = Agent()
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break
        if user_input.lower() in {"context", "/context"}:
            print(agent.ctx.status())
            continue
        agent.send(user_input)
if __name__ == "__main__":
    sys.exit(main())