"""Shell command execution tool.

Highest blast radius of any tool here -- runs arbitrary shell commands.
Always gated behind a permission check in agent.py (see MUTATING below);
this module never runs anything on its own.
"""

import subprocess

import config

MAX_OUTPUT_CHARS = 4000
DEFAULT_TIMEOUT = 60


def run_command(command, timeout=DEFAULT_TIMEOUT):
    """Run `command` in a shell, cwd'd to the project root. Returns captured output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=config.PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s: {command}"
    except Exception as exc:
        return f"Error running command: {exc}"

    parts = [f"$ {command}", f"exit code: {result.returncode}"]
    if result.stdout:
        parts.append(f"--- stdout ---\n{_truncate(result.stdout)}")
    if result.stderr:
        parts.append(f"--- stderr ---\n{_truncate(result.stderr)}")
    return "\n".join(parts)


def _truncate(text):
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + f"\n... [truncated, {len(text) - MAX_OUTPUT_CHARS} more chars]"


# Requires user approval -- see agent.py's permission-check gate.
MUTATING = {"run_command"}

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Run a shell command in the project root (e.g. run tests, "
                "install a package, run a script) and return its stdout, "
                "stderr, and exit code. Requires user approval before it "
                "runs. Use this to verify a fix actually works, e.g. by "
                "running the test suite after an edit_file change."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run."},
                    "timeout": {
                        "type": "integer",
                        "description": f"Max seconds to wait (default {DEFAULT_TIMEOUT}).",
                    },
                },
                "required": ["command"],
            },
        },
    }
]

FUNCTIONS = {"run_command": run_command}
