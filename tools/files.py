"""File access tools: give the agent read-only visibility into the project.

Everything is scoped under PROJECT_ROOT (config.PROJECT_ROOT) so the agent
can't read or list anything outside the target project directory.
"""

import os

import config


def _resolve(path):
    """Resolve a path relative to PROJECT_ROOT and reject escapes (e.g. '../../etc')."""
    root = os.path.abspath(config.PROJECT_ROOT)
    target = os.path.abspath(os.path.join(root, path))
    if os.path.commonpath([root, target]) != root:
        raise ValueError(f"'{path}' is outside the project root")
    return target


def list_files(path="."):
    """List files and directories at `path` (relative to the project root)."""
    target = _resolve(path)
    if not os.path.isdir(target):
        return f"Error: '{path}' is not a directory."
    entries = []
    for name in sorted(os.listdir(target)):
        entries.append(name + "/" if os.path.isdir(os.path.join(target, name)) else name)
    return entries


def read_file(path):
    """Read and return the text contents of the file at `path`."""
    target = _resolve(path)
    if not os.path.isfile(target):
        return f"Error: '{path}' does not exist."
    try:
        with open(target, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        return f"Error: '{path}' is not a readable text file."


def file_exists(path):
    """Return True if `path` exists (file or directory) under the project root."""
    return os.path.exists(_resolve(path))


# Ollama/OpenAI-style tool schemas so the model knows these functions exist.
SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List files and subdirectories at a path relative to the project "
                "root. Directories are suffixed with '/'. Use this first to see "
                "the project layout."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to list. Defaults to the project root.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read and return the full text contents of a file, given a path relative to the project root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path of the file to read."}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_exists",
            "description": "Check whether a file or directory exists, given a path relative to the project root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to check."}
                },
                "required": ["path"],
            },
        },
    },
]

FUNCTIONS = {
    "list_files": list_files,
    "read_file": read_file,
    "file_exists": file_exists,
}
