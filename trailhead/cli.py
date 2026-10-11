import argparse
import sys
from datetime import date, datetime

from .facts import build_facts
from .llm import DEFAULT_MODEL, DEFAULT_URL
from .planner import make_plan


def main(argv=None):
    p = argparse.ArgumentParser(prog="trailhead", description="Get off the screen. Get outside.")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--minutes", type=int, default=45, help="time you have free")
    p.add_argument("--weather", default="unknown", help="e.g. 'sunny, 12C' (offline: you tell it)")
    p.add_argument("--interest", action="append", default=[], help="bird, garden, foliage, run ...")
    p.add_argument("--first-frost", type=date.fromisoformat, help="YYYY-MM-DD")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--ollama-url", default=DEFAULT_URL)
    p.add_argument("--no-llm", action="store_true", help="skip the model, use rules only")
    args = p.parse_args(argv)

    facts = build_facts(datetime.now().astimezone(), args.lat, args.lon, args.minutes,
                        args.weather, [i.lower() for i in args.interest], args.first_frost)
    plan, source = make_plan(facts, args.model, args.ollama_url, not args.no_llm)
    print(plan)
    print(f"\n[{source}]", file=sys.stderr)


if __name__ == "__main__":
    main()
