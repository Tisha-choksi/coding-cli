"""Configuration for the coding agent CLI."""
import os
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")

# The project the agent is allowed to look at. Defaults to wherever
# `python main.py` is run from; override with PROJECT_ROOT to point
# the agent at a different codebase.
PROJECT_ROOT = os.environ.get("PROJECT_ROOT", os.getcwd())

SYSTEM_PROMPT = (
    "You are a helpful coding assistant running in a terminal. You have "
    "read-only tools to explore the user's project: list_files, read_file, "
    "and file_exists. Use them to look at the actual project structure and "
    "file contents before answering questions about the codebase, diagnosing "
    "bugs, or proposing fixes -- don't guess at file contents you haven't "
    "read. When asked to write code, respond with clear, correct code in a "
    "fenced code block, plus a brief explanation."
)
