"""
Phase 1: Minimal coding agent CLI.
Reads a prompt from the terminal, sends it to a local Ollama model,
and prints the model's response. No tool use, no file edits, no
autonomous behavior yet -- just a chat loop.
"""
import sys
import config
from agent import Agent
def main():
    print(f"Coding agent CLI (Phase 1) -- model: {config.MODEL}")
    print("Type your request, or 'exit' / 'quit' to leave.\n")
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
        agent.send(user_input)
if __name__ == "__main__":
    sys.exit(main())