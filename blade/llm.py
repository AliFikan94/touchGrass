"""Tiny Ollama client. Talks to a local open-weight model; nothing leaves the machine."""
import base64
import json
import urllib.error
import urllib.request

DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma3:4b"


class LLMUnavailable(Exception):
    pass


def generate(prompt, system, model=DEFAULT_MODEL, url=DEFAULT_URL, as_json=False,
             images=None, timeout=180):
    payload = {"model": model, "system": system, "prompt": prompt, "stream": False}
    if as_json:
        payload["format"] = "json"
    if images:
        payload["images"] = [base64.b64encode(i).decode() for i in images]
    req = urllib.request.Request(url.rstrip("/") + "/api/generate", json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)["response"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        raise LLMUnavailable(str(exc)) from exc
