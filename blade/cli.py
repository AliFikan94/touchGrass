import argparse
import sys
from datetime import datetime
from pathlib import Path

from . import log, speech
from .facts import build_facts
from .generate import make_blade
from .llm import DEFAULT_MODEL, DEFAULT_URL, LLMUnavailable, generate
from .voice import LOOK_SYSTEM


def render(blade):
    lines = ["Move.", f"  {blade['movement']}", "", "Notice."]
    lines += [f"  - {o}" for o in blade["observations"]]
    return "\n".join(lines + ["", blade["closing"]])


def main(argv=None):
    p = argparse.ArgumentParser(prog="blade", description="Step outside. Touch a blade. Notice the world.")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--ollama-url", default=DEFAULT_URL)
    p.add_argument("--no-llm", action="store_true", help="skip the model, use the quest library only")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("today", help="get today's Blade")
    t.add_argument("--lat", type=float, required=True)
    t.add_argument("--lon", type=float, required=True)
    t.add_argument("--minutes", type=int, default=20)
    t.add_argument("--weather", default="unknown")
    t.add_argument("--interest", action="append", default=[], help="birds plants trees light senses water")
    t.add_argument("--speak", type=Path, metavar="OUT.mp3",
                   help="also save a spoken version (optional; needs ELEVENLABS_API_KEY)")
    sub.add_parser("done", help="log today's Blade as complete (local file only)")
    sub.add_parser("stats", help="show your Blade count")
    s = sub.add_parser("serve", help="open the local web page")
    s.add_argument("--port", type=int, default=8317)
    lk = sub.add_parser("look", help="ask the local vision model about a photo")
    lk.add_argument("photo", type=Path)
    a = p.parse_args(argv)

    if a.cmd == "today":
        facts = build_facts(datetime.now().astimezone(), a.lat, a.lon, a.minutes, a.weather,
                            [i.lower() for i in a.interest])
        blade, src = make_blade(facts, [i.lower() for i in a.interest], a.model, a.ollama_url, not a.no_llm)
        print(render(blade))
        print(f"\n[{src}]", file=sys.stderr)
        if a.speak:
            try:
                a.speak.write_bytes(speech.synthesize(blade))
                print(f"Spoken Blade saved to {a.speak}", file=sys.stderr)
            except speech.SpeechUnavailable as e:
                sys.exit(str(e))
    elif a.cmd == "done":
        log.record({"manual": True})
        print(log.message(log.stats()))
    elif a.cmd == "stats":
        s = log.stats()
        print(f"{log.message(s)}  ({s['total']} Blades collected)")
    elif a.cmd == "serve":
        from .web import serve
        serve(a.port, a.model, a.ollama_url, not a.no_llm)
    elif a.cmd == "look":
        try:
            print(generate("What is this?", LOOK_SYSTEM, a.model, a.ollama_url,
                           images=[a.photo.read_bytes()]))
        except LLMUnavailable as e:
            sys.exit(f"Vision model not reachable ({e}). Run `ollama serve` and pull a multimodal model.")


if __name__ == "__main__":
    main()
