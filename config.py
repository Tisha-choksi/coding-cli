"""Configuration for the coding agent CLI."""
import os
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
SYSTEM_PROMPT = (
    "You are a helpful coding assistant running in a terminal. "
    "When asked to write code, respond with clear, correct code "
    "in a fenced code block, plus a brief explanation."
)
