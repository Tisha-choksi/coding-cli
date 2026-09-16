"""Code/file search tools: find files and grep their contents without
having to read every file one by one.
"""

import fnmatch
import os
import re

import config
from tools.files import _resolve

IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".next", ".venv", "venv",
    "env", "dist", "build", ".pytest_cache", ".mypy_cache", "target",
    ".idea", ".vscode",
}

MAX_RESULTS = 200


def _walk(root):
    """os.walk over `root`, pruning ignored directories as it goes."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        yield dirpath, filenames


def search_files(pattern, path="."):
    """Find files under `path` whose name matches a glob pattern (e.g. '*.py')."""
    root = _resolve(path)
    if not os.path.isdir(root):
        return f"Error: '{path}' is not a directory."

    matches = []
    for dirpath, filenames in _walk(root):
        for name in filenames:
            if fnmatch.fnmatch(name, pattern):
                rel = os.path.relpath(os.path.join(dirpath, name), config.PROJECT_ROOT)
                matches.append(rel.replace(os.sep, "/"))
                if len(matches) >= MAX_RESULTS:
                    return sorted(matches) + [f"... [stopped after {MAX_RESULTS} matches]"]

    return sorted(matches) if matches else f"No files matching '{pattern}' found under '{path}'."


def grep(query, path=".", regex=False):
    """Search file contents under `path` for `query`, returning 'file:line: text' entries."""
    root = _resolve(path)
    if not os.path.exists(root):
        return f"Error: '{path}' does not exist."

    try:
        compiled = re.compile(query) if regex else re.compile(re.escape(query))
    except re.error as exc:
        return f"Error: invalid regex '{query}': {exc}"

    if os.path.isfile(root):
        files = [root]
    else:
        files = [
            os.path.join(dirpath, name)
            for dirpath, filenames in _walk(root)
            for name in filenames
        ]

    results = []
    for full in files:
        rel = os.path.relpath(full, config.PROJECT_ROOT).replace(os.sep, "/")
        try:
            with open(full, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, start=1):
                    if compiled.search(line):
                        results.append(f"{rel}:{i}: {line.strip()}")
                        if len(results) >= MAX_RESULTS:
                            results.append(f"... [stopped after {MAX_RESULTS} matches]")
                            return results
        except OSError:
            continue

    return results if results else f"No matches for '{query}' under '{path}'."


SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": (
                "Find files by filename glob pattern (e.g. '*.py', 'test_*.js') "
                "under a path relative to the project root. Skips node_modules, "
                ".git, __pycache__, and similar directories. Use this when you "
                "don't know a file's exact path."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match filenames against, e.g. '*.py'.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search under. Defaults to the project root.",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": (
                "Search file contents for a string (or regex) under a path "
                "relative to the project root, returning matching "
                "'file:line: text' entries. Use this to find where a "
                "function, variable, import, or string is used or defined "
                "across the project."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text or regex to search for."},
                    "path": {
                        "type": "string",
                        "description": "File or directory to search under. Defaults to the project root.",
                    },
                    "regex": {
                        "type": "boolean",
                        "description": "Treat `query` as a regex instead of a literal string. Defaults to false.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]

FUNCTIONS = {"search_files": search_files, "grep": grep}
