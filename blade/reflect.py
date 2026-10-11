"""After the walk: a short reply to what the person noticed. Local model first, fixed line second.

The model only ever sees the person's own words, and its reply is trimmed to two calm sentences.
"""
import re

from .llm import LLMUnavailable, generate
from .voice import REFLECT_SYSTEM

MAX_NOTE = 300


def clean_note(note):
    return " ".join(str(note).split())[:MAX_NOTE]


def _items(note):
    parts = re.split(r",|;|\n|\band\b|&", note, flags=re.I)
    return [p.strip(" .")[:40] for p in parts if p.strip(" .")][:4]


def fallback_reply(note):
    items = _items(note)
    if not items:
        return "You went outside. That is enough."
    return f"Noticed today: {', '.join(items)}. The day is different now."


def tidy(text):
    """Keep at most two sentences, calm punctuation, no questions."""
    text = text.replace("!", ".").strip().strip('"').strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.])\s+", text) if s.strip()]
    sentences = [s for s in sentences if "?" not in s][:2]
    out = " ".join(sentences)
    return out if 3 <= len(out) <= 280 else ""


def reflect(note, blade=None, model="gemma3:4b", url="http://localhost:11434", use_llm=True,
            on_error=None, timeout=30):
    """Return (reply, source) where source is 'model' or 'fallback'."""
    note = clean_note(note)
    if use_llm and note:
        tasks = ""
        if blade:
            tasks = "TODAY'S BLADE: " + " ".join([str(blade.get("movement", ""))]
                                                 + [str(o) for o in blade.get("observations", [])][:3]) + "\n"
        prompt = f"{tasks}WHAT THEY NOTICED: {note}\n\nReply."
        try:
            reply = tidy(generate(prompt, REFLECT_SYSTEM, model, url, timeout=timeout,
                                  keep_alive="30m", max_tokens=100))
            if reply:
                return reply, "model"
            _report(on_error, "model reply was empty or not usable")
        except LLMUnavailable as exc:
            _report(on_error, f"model unavailable at {url} ({exc})")
    return fallback_reply(note), "fallback"


def _report(on_error, reason):
    if on_error:
        on_error(reason)
