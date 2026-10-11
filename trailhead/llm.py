"""Tiny Ollama client. Talks to a local open-weight model; nothing leaves the machine."""
import json
import urllib.error
import urllib.request

DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma3:4b"

SYSTEM = (
    "You are Trailhead, a friendly guide whose only job is to get people off their "
    "screens and outside. Use ONLY the facts provided; never invent weather, times or "
    "places. Reply with a short plan: a one-line headline, then 3 to 5 steps with "
    "approximate minutes, then one line telling them to put the phone away. "
    "Keep it under 120 words."
)


class LLMUnavailable(Exception):
    pass


def generate(prompt, model=DEFAULT_MODEL, url=DEFAULT_URL, timeout=120):
    body = json.dumps(
        {"model": model, "system": SYSTEM, "prompt": prompt, "stream": False}
    ).encode()
    req = urllib.request.Request(
        url.rstrip("/") + "/api/generate", body, {"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)["response"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        raise LLMUnavailable(str(exc)) from exc
