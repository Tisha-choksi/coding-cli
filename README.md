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

## Phase 4 -- Terminal access

The agent can now run shell commands:

- `run_command(command, timeout=60)` -- runs `command` in the project
  root and returns stdout, stderr, and exit code (output over ~4000
  chars is truncated so it doesn't blow out the model's context).

Like the write tools, `run_command` goes through the same permission
check -- you see the exact command before it runs, and nothing
executes without a `y`.

This is what closes the loop and makes it feel like an actual coding
agent: it can run your tests, see a real failure, use `read_file` /
`edit_file` to fix the actual cause, and run the tests again to
confirm -- all in one request, each step still gated by your approval:

```
run_command (pytest) -> failure -> agent reads the error -> edit_file -> run_command again -> pass
```

## Phase 5 -- Search tools, command safety, and memory limits

Three quality-of-life/safety additions:

**Search tools** (`tools/search.py`), so the agent doesn't have to read
every file one by one on a larger project:
- `search_files(pattern, path=".")` -- find files by name glob (e.g. `*.ts`)
- `grep(query, path=".", regex=False)` -- search file contents, returns `file:line: text` matches

Both skip `node_modules`, `.git`, `__pycache__`, `.next`, `venv`, and
similar directories automatically.

**Hardened `run_command`.** Beyond the y/N permission prompt, a fixed
denylist of destructive patterns (`rm -rf /`, force-push, `git reset
--hard`, disk formatting, fork bombs, pipe-to-shell installs, etc.) is
blocked outright -- the agent isn't even asked for approval on these,
they're refused before the prompt appears. This is a floor under human
approval, not a sandbox -- it catches the worst, hardest-to-undo
commands, not everything risky.

**Memory limits**, so a long session doesn't eventually overflow the
model's context window:
- `read_file` truncates any file over ~20,000 characters (use `grep`
  to search inside large files instead of reading them whole).
- Conversation history is capped at `agent.MAX_HISTORY_MESSAGES` (60)
  -- the system prompt is always kept, oldest messages drop first.

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
