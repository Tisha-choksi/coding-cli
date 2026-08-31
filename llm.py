"""Client for talking to a local Ollama model."""
import json
import requests
import config
def stream_chat(messages, tools=None):
    """Send messages (and optional tool schemas) to Ollama's chat endpoint.

    Streams assistant text to stdout as it arrives. Returns a dict
    {"content": str, "tool_calls": list} on success, or None on failure.
    Model text and tool calls are mutually typical per turn: a turn either
    answers in text or asks to call tool(s).
    """
    url = f"{config.OLLAMA_HOST}/api/chat"
    payload = {"model": config.MODEL, "messages": messages, "stream": True}
    if tools:
        payload["tools"] = tools
    try:
        response = requests.post(url, json=payload, stream=True, timeout=120)
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
    full_reply = ""
    tool_calls = []
    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        message = chunk.get("message", {})
        piece = message.get("content", "")
        if piece:
            print(piece, end="", flush=True)
            full_reply += piece
        if message.get("tool_calls"):
            tool_calls.extend(message["tool_calls"])
        if chunk.get("done"):
            break
    print()
    return {"content": full_reply, "tool_calls": tool_calls}
