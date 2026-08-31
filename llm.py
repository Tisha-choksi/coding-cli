"""Client for talking to a local Ollama model."""
import json
import re
import requests
import config


def chat(messages, tools=None):
    """Send messages (and optional tool schemas) to Ollama's chat endpoint.

    Returns {"content": str, "tool_calls": list} on success, or None on failure.
    """
    url = f"{config.OLLAMA_HOST}/api/chat"
    payload = {"model": config.MODEL, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(
            f"\n[error] Could not connect to Ollama at {config.OLLAMA_HOST}. "
            "Is 'ollama serve' running?\n"
        )
        return None
    except requests.exceptions.HTTPError as exc:
        print(f"\n[error] Ollama returned an error: {exc}\n")
        return None

    message = response.json().get("message", {})
    content = message.get("content", "")
    tool_calls = message.get("tool_calls") or []

    if not tool_calls:
        # Some local models emit a tool call as raw JSON text in `content`
        # instead of using Ollama's structured tool_calls field. Catch that.
        fallback = _extract_fallback_tool_calls(content)
        if fallback:
            tool_calls = fallback
            content = ""

    return {"content": content, "tool_calls": tool_calls}


_TAGGED_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


def _find_json_objects(text):
    """Extract top-level balanced {...} substrings from free-form text."""
    objects = []
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    objects.append(text[start : i + 1])
                    start = None
    return objects


def _extract_fallback_tool_calls(content):
    candidates = _TAGGED_RE.findall(content) or _find_json_objects(content)

    calls = []
    for candidate in candidates:
        try:
            obj = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(obj, dict) and "name" in obj:
            calls.append(
                {"function": {"name": obj["name"], "arguments": obj.get("arguments", {})}}
            )
    return calls
