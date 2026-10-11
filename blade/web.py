"""Local web UI on http.server. Bind to localhost only; no external requests, no analytics."""
import json
from datetime import datetime
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import log, speech
from .facts import build_facts
from .generate import make_blade

PAGE = (Path(__file__).parent / "page.html").read_text(encoding="utf-8")


WEB_TIMEOUT = 60


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
                    facts = build_facts(datetime.now().astimezone(), float(b["lat"]), float(b["lon"]),
                                        int(b["minutes"]), "unknown", ints)
                    notes = []
                    blade, src = make_blade(facts, ints, model, url, use_llm,
                                            on_error=notes.append, timeout=WEB_TIMEOUT)
                    self._send(200, json.dumps({"blade": blade, "source": src, "model": model,
                                                "note": notes[0] if notes else ""}))
                elif self.path == "/api/speak":
                    try:
                        self._send(200, speech.synthesize(b), "audio/mpeg")
                    except speech.SpeechUnavailable as e:
                        self._send(503, json.dumps({"error": str(e)}))
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
