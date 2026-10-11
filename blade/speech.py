"""Optional spoken Blade via ElevenLabs. Off unless ELEVENLABS_API_KEY is set.

This is the only part of Blade that touches the network, and only the Blade text is sent
(never location, photos or your log). The core experience stays fully local.
"""
import json
import os
import urllib.error
import urllib.request

API = "https://api.elevenlabs.io"
DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"
MODEL = "eleven_multilingual_v2"


class SpeechUnavailable(Exception):
    pass


def enabled():
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


def script(blade):
    """Short sentences with pauses (commas and full stops) so it can be heard while walking."""
    parts = ["Move.", blade["movement"], "Notice."] + list(blade["observations"]) + [blade["closing"]]
    return " ".join(p.strip() for p in parts)


def synthesize(blade, base=None):
    """Return mp3 bytes for the Blade."""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise SpeechUnavailable("Set ELEVENLABS_API_KEY to enable spoken Blades.")
    voice = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE)
    req = urllib.request.Request(
        f"{base or API}/v1/text-to-speech/{voice}",
        json.dumps({"text": script(blade), "model_id": MODEL}).encode(),
        {"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SpeechUnavailable(f"Speech service unreachable: {exc}") from exc
