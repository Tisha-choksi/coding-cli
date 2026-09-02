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


def create_file(path, content=""):
    """Create a new file with `content`. Fails if the file already exists."""
    target = _resolve(path)
    if os.path.exists(target):
        return f"Error: '{path}' already exists. Use edit_file to modify it."
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Created '{path}' ({len(content)} bytes)."


def edit_file(path, content):
    """Overwrite an existing file's full contents with `content`. Fails if it doesn't exist."""
    target = _resolve(path)
    if not os.path.isfile(target):
        return f"Error: '{path}' does not exist. Use create_file to create it."
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Updated '{path}' ({len(content)} bytes)."


def delete_file(path):
    """Delete a file."""
    target = _resolve(path)
    if not os.path.isfile(target):
        return f"Error: '{path}' does not exist or is not a file."
    os.remove(target)
    return f"Deleted '{path}'."


# Tools that touch the filesystem -- these require user confirmation
# before agent.py will actually call them.
MUTATING = {"create_file", "edit_file", "delete_file"}


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
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": (
                "Create a brand new file with the given content, given a path "
                "relative to the project root. Fails if the file already exists "
                "-- use edit_file for existing files. Requires user approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path of the new file."},
                    "content": {"type": "string", "description": "Full contents of the new file."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Overwrite an existing file with new content, given a path "
                "relative to the project root. `content` must be the file's "
                "COMPLETE new contents, not a partial snippet or diff -- read "
                "the file first, then send the whole file back with your "
                "changes applied. Fails if the file doesn't exist. Requires "
                "user approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path of the file to edit."},
                    "content": {
                        "type": "string",
                        "description": "The complete new contents of the file (not a diff).",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": (
                "Permanently delete a file, given a path relative to the "
                "project root. Requires user approval. Only call this when "
                "the user has clearly asked for a file to be removed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path of the file to delete."}
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
    "create_file": create_file,
    "edit_file": edit_file,
    "delete_file": delete_file,
}
