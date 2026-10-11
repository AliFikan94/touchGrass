"""Local web UI on http.server. Bind to localhost only; no external requests, no analytics."""
import json
from datetime import datetime
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import live as livemod, log, speech
from .facts import build_facts
from .generate import make_blade
from .reflect import clean_note, reflect

PAGE = (Path(__file__).parent / "page.html").read_text(encoding="utf-8")


WEB_TIMEOUT = 60


def context(f):
    bits = [f.season.capitalize() if f.season == f.climate else f"{f.season.capitalize()}, {f.climate}"]
    if f.place_name:
        bits.append(f.place_name)
    if f.weather != "unknown":
        bits.append(f.weather)
    return " \u00b7 ".join(bits)


def live_status(body, data):
    if body.get("live") is not True:
        return "off"
    got = data and (data["weather"] or data["place"] or data["sightings"])
    return "on" if got else "unavailable"


def make_handler(model, url, use_llm):
    class H(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json"):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n) or b"{}")

        def do_GET(self):
            if self.path == "/":
                self._send(200, PAGE, "text/html")
            elif self.path == "/api/stats":
                s = log.stats()
                self._send(200, json.dumps({**s, "message": log.message(s), "speech": speech.enabled()}))
            else:
                self._send(404, "{}")

        def do_POST(self):
            try:
                b = self._body()
                if self.path == "/api/blade":
                    ints = [str(i) for i in b.get("interests", [])][:6]
                    lat, lon = float(b["lat"]), float(b["lon"])
                    data = livemod.gather(lat, lon) if b.get("live") is True else None
                    facts = build_facts(datetime.now().astimezone(), lat, lon,
                                        int(b["minutes"]), "unknown", ints, live=data)
                    notes = []
                    blade, src = make_blade(facts, ints, model, url, use_llm,
                                            on_error=notes.append, timeout=WEB_TIMEOUT)
                    self._send(200, json.dumps({"blade": blade, "source": src, "model": model,
                                                "note": notes[0] if notes else "",
                                                "context": context(facts), "live": live_status(b, data)}))
                elif self.path == "/api/speak":
                    try:
                        self._send(200, speech.synthesize(b), "audio/mpeg")
                    except speech.SpeechUnavailable as e:
                        self._send(503, json.dumps({"error": str(e)}))
                elif self.path == "/api/reflect":
                    note = clean_note(b.get("note", ""))
                    if not note:
                        raise ValueError("empty note")
                    blade = b.get("blade") if isinstance(b.get("blade"), dict) else None
                    notes = []
                    reply, src = reflect(note, blade, model, url, use_llm, on_error=notes.append)
                    log.annotate(note, reply)
                    self._send(200, json.dumps({"reply": reply, "source": src, "model": model,
                                                "note": notes[0] if notes else ""}))
                elif self.path == "/api/complete":
                    log.record(b)
                    self._send(200, "{}")
                else:
                    self._send(404, "{}")
            except (KeyError, ValueError, TypeError):
                self._send(400, json.dumps({"error": "bad request"}))

        def log_message(self, *a):
            pass
    return H


def serve(port, model, url, use_llm):
    if use_llm:
        threading.Thread(target=_warm, args=(model, url), daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(model, url, use_llm))
    print(f"Blade is open at http://127.0.0.1:{port}  (ctrl-c to close)")
    srv.serve_forever()


def _warm(model, url):
    """Load the model into memory in the background so the first Blade isn't slow."""
    from .llm import LLMUnavailable, generate
    try:
        generate("Say ok.", "Reply with one word.", model, url, timeout=300, keep_alive="30m")
    except LLMUnavailable:
        pass
