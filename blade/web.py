"""Local web UI on http.server. Bind to localhost only; no external requests, no analytics."""
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import log, speech
from .facts import build_facts
from .generate import make_blade

PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Blade</title><style>
:root{--grass:#2f5d3a;--live:#5fbf4a;--light:#faf6ea;--gold:#f0e3b2;--dusk:#6b7a8a;--bark:#4a3f35}
@media(prefers-color-scheme:dark){:root{--light:#1f2a22;--gold:#2a3a2c;--bark:#e8e2d0;--dusk:#9fb0bd}}
body{margin:0;background:var(--light);color:var(--bark);font:18px/1.55 Georgia,serif}
main{max-width:34rem;margin:0 auto;padding:2rem 1rem}h1{color:var(--grass);font-weight:400;letter-spacing:.04em}
.sub{color:var(--dusk)}label{display:block;margin:.8rem 0 .2rem;color:var(--dusk);font-size:.9rem}
input,select{font:inherit;padding:.4rem;border:1px solid var(--dusk);border-radius:6px;background:transparent;color:inherit;width:100%;box-sizing:border-box}
button{font:inherit;margin-top:1rem;padding:.6rem 1.2rem;border:0;border-radius:6px;background:var(--grass);color:#fff;cursor:pointer}
button.done{background:var(--live);color:#10240f}.card{background:var(--gold);border-radius:10px;padding:1rem 1.2rem;margin-top:1.5rem}
li{margin:.4rem 0}.close{font-style:italic;color:var(--grass)}</style>
<main><h1>Blade</h1><p class=sub>Step outside. Touch a blade. Notice the world.</p><p id=msg class=sub></p>
<label>Minutes free<input id=min type=number value=20 min=5></label>
<label>Latitude<input id=lat type=number step=any value=40.7></label>
<label>Longitude<input id=lon type=number step=any value=-74></label>
<label>Interest<select id=int><option value="">Anything</option><option>birds</option><option>plants</option>
<option>trees</option><option>light</option><option>senses</option><option>water</option></select></label>
<button id=go>Get today's Blade</button><div id=out></div></main><script>
const $=i=>document.getElementById(i);let cur=null,speak=false;
async function stats(){const s=await (await fetch('/api/stats')).json();$('msg').textContent=s.message;speak=s.speech}
$('go').onclick=async()=>{$('out').innerHTML='<p class=sub>Listening to the grass...</p>';
const r=await fetch('/api/blade',{method:'POST',body:JSON.stringify({minutes:+$('min').value,lat:+$('lat').value,lon:+$('lon').value,interest:$('int').value})});
const d=await r.json();cur=d.blade;
$('out').innerHTML='<div class=card><p><b>Move.</b> '+esc(cur.movement)+'</p><b>Notice.</b><ul>'+cur.observations.map(o=>'<li>'+esc(o)+'</li>').join('')+'</ul><p class=close>'+esc(cur.closing)+'</p><p class=sub>('+d.source+')</p></div><button class=done id=ok>Blade complete</button>'+(speak?' <button id=ls>Listen</button><audio id=au></audio>':'');
if(speak)$('ls').onclick=async()=>{const r=await fetch('/api/speak',{method:'POST',body:JSON.stringify(cur)});if(!r.ok){$('ls').textContent='Voice unavailable';return}$('au').src=URL.createObjectURL(await r.blob());$('au').play()};
$('ok').onclick=async()=>{await fetch('/api/complete',{method:'POST',body:JSON.stringify(cur)});$('out').innerHTML='';stats()}};
function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}stats()</script>"""


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
                    facts = build_facts(datetime.now().astimezone(), float(b["lat"]), float(b["lon"]),
                                        int(b["minutes"]), "unknown", [b["interest"]] if b.get("interest") else [])
                    blade, src = make_blade(facts, [b["interest"]] if b.get("interest") else [],
                                            model, url, use_llm)
                    self._send(200, json.dumps({"blade": blade, "source": src}))
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
    srv = HTTPServer(("127.0.0.1", port), make_handler(model, url, use_llm))
    print(f"Blade is open at http://127.0.0.1:{port}  (ctrl-c to close)")
    srv.serve_forever()
