# Coding Agent CLI

## Phase 1 -- Basic chat with a local model

A terminal app that forwards your prompts to a local Ollama model and
prints the response.

## Phase 2 -- Read-only project access

The agent can now call tools to explore a project before answering:

- `list_files(path=".")` -- list files/dirs at a path
- `read_file(path)` -- read a file's contents
- `file_exists(path)` -- check if a path exists

All three are scoped to `PROJECT_ROOT` (see Configuration) and reject
any path that escapes it.

## Phase 3 -- File editing (with permission checks)

The agent can now propose changes to the project:

- `create_file(path, content)` -- create a new file
- `edit_file(path, content)` -- overwrite an existing file with new content
- `delete_file(path)` -- delete a file

**The agent never touches disk directly.** Every one of these goes
through a permission check before anything happens:

```
LLM -> tool request -> agent -> permission check (y/N prompt) -> filesystem
```

For `edit_file`, you'll see a unified diff of exactly what would
change; for `create_file`, a preview of the new file's contents; for
`delete_file`, a confirmation of what would be deleted. Nothing is
written, overwritten, or removed unless you type `y`. If you decline,
the agent is told the change was denied and won't retry it.

The agent still can't run commands (no shell/terminal tool yet) --
so it can't run your code, install packages, or run tests on its own.
That's a later phase.

### Setup

1. Install [Ollama](https://ollama.com) and make sure it's running:
   ```
   ollama serve
   ```
2. Pull a coding model (pick one that supports tool calling):
   ```
   ollama pull qwen2.5-coder:7b
   ollama pull llama3.1
   ```
3. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

### Run

Run against your own project by setting `PROJECT_ROOT` to point at it,
then start the agent from anywhere:

```
set PROJECT_ROOT=C:\path\to\your\project
python main.py
```

(PowerShell: `$env:PROJECT_ROOT="C:\path\to\your\project"`)

If you don't set `PROJECT_ROOT`, it defaults to the current working
directory -- so `cd`-ing into your project and running `python
"d:\projects personal\coding cli\main.py"` from there also works.

Then type a request, e.g.:

```
You: Fix the login bug.
```

The agent will call `list_files`, `read_file`, etc. as needed (printed
as `[tool] ...` lines) before giving its answer.

### Configuration

Environment variables:

- `OLLAMA_MODEL` -- model name to use (default: `qwen2.5-coder:7b`)
- `OLLAMA_HOST` -- Ollama API host (default: `http://localhost:11434`)
- `PROJECT_ROOT` -- project directory the agent's tools can access (default: current working directory)
