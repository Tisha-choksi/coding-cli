"""Shell command execution tool.

Highest blast radius of any tool here -- runs arbitrary shell commands.
Always gated behind a permission check in agent.py (see MUTATING below);
this module never runs anything on its own.
"""

import re
import subprocess

import config

MAX_OUTPUT_CHARS = 4000
DEFAULT_TIMEOUT = 60

# Commands matching any of these are refused outright, even if the user
# approves them -- a hard floor under the permission-check UI, in case a
# risky command slips past a fat-fingered "y". Not exhaustive; it's a
# denylist for the worst, hardest-to-undo cases, not a sandbox.
_DANGEROUS_PATTERNS = [
    r"\brm\s+(-\w*r\w*f\w*|-\w*f\w*r\w*)\s+(/|~|\*|\.\.?)(\s|$)",  # rm -rf /, ~, *, .
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",  # classic fork bomb
    r"\bmkfs(\.\w+)?\b",
    r"\bdd\s+.*\bof=/dev/",
    r"\b(shutdown|reboot)\b",
    r">\s*/dev/sd[a-z]\d*\b",
    r"\bformat\s+[a-zA-Z]:",  # Windows: format C:
    r"\b(rd|rmdir)\s+/s\b.*[a-zA-Z]:\\?\s*$",  # rd /s C:\
    r"\bdel\s+/[a-z]*f[a-z]*\s+/[a-z]*s[a-z]*\b",  # del /f /s ...
    r"git\s+push\s+.*--force",
    r"git\s+reset\s+--hard",
    r"\b(curl|wget)\b[^|]*\|\s*(sh|bash|powershell|iex)\b",  # pipe-to-shell
]
_DANGEROUS_RE = [re.compile(p, re.IGNORECASE) for p in _DANGEROUS_PATTERNS]


def is_dangerous(command):
    """True if `command` matches a denylisted destructive pattern."""
    return any(p.search(command) for p in _DANGEROUS_RE)


def run_command(command, timeout=DEFAULT_TIMEOUT):
    """Run `command` in a shell, cwd'd to the project root. Returns captured output."""
    if is_dangerous(command):
        return (
            f"Blocked: '{command}' matches a denylisted destructive pattern "
            "and will not be run. If this was intentional, run it yourself "
            "outside the agent."
        )
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
