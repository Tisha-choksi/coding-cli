# Coding Agent CLI

## Phase 1 -- Basic chat with a local model

A terminal app that forwards your prompts to a local Ollama model and
prints the response. No autonomous behavior yet (no file edits, no
tool use) -- that comes in later phases.

### Setup

1. Install [Ollama](https://ollama.com) and make sure it's running:
   ```
   ollama serve
   ```
2. Pull a coding model (pick one):
   ```
   ollama pull qwen2.5-coder:7b
   ollama pull deepseek-coder-v2
   ollama pull llama3.1
   ```
3. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

### Run

```
python main.py
```

Then type a request, e.g.:

```
You: Create a Python calculator.
```

### Configuration

Environment variables:

- `OLLAMA_MODEL` -- model name to use (default: `qwen2.5-coder:7b`)
- `OLLAMA_HOST` -- Ollama API host (default: `http://localhost:11434`)
