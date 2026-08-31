"""Client for talking to a local Ollama model."""

import json

import requests

import config


def stream_chat(messages):
    """Send messages to Ollama's chat endpoint and stream the reply.

    Prints each token as it arrives and returns the full reply text,
    or None if the request failed.
    """
    url = f"{config.OLLAMA_HOST}/api/chat"
    payload = {"model": config.MODEL, "messages": messages, "stream": True}

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
    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        if chunk.get("done"):
            break
        piece = chunk.get("message", {}).get("content", "")
        print(piece, end="", flush=True)
        full_reply += piece
    print()
    return full_reply
