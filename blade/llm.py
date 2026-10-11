"""Tiny Ollama client. Talks to a local open-weight model; nothing leaves the machine."""
import base64
import json
import os
import urllib.error
import urllib.request

DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = os.environ.get("BLADE_MODEL", "gemma3:4b")


class LLMUnavailable(Exception):
    pass


def generate(prompt, system, model=DEFAULT_MODEL, url=DEFAULT_URL, as_json=False,
             images=None, timeout=180, keep_alive=None):
    payload = {"model": model, "system": system, "prompt": prompt, "stream": False,
               "options": {"num_predict": 300, "temperature": 0.7}}
    if keep_alive:
        payload["keep_alive"] = keep_alive
    if as_json:
        payload["format"] = "json"
    if images:
        payload["images"] = [base64.b64encode(i).decode() for i in images]
    req = urllib.request.Request(url.rstrip("/") + "/api/generate", json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)["response"].strip()
    except TimeoutError as exc:
        raise LLMUnavailable(f"timed out after {timeout}s") from exc
    except urllib.error.HTTPError as exc:
        raise LLMUnavailable(f"HTTP {exc.code}: {exc.read()[:200].decode(errors='replace')}") from exc
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        raise LLMUnavailable(str(exc)) from exc
