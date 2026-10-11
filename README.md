# Trailhead

An offline-first "go outside now" planner. Tell it where you are and how long you have; it works out
daylight and frost dates locally, then asks a **local open-weight model** (via [Ollama](https://ollama.com))
to write a short plan that gets you off the screen. No cloud, no API key, no account.

```
ollama pull gemma3:4b            # any small open-weight model works
python -m trailhead --lat 40.7 --lon -74 --minutes 45 \
    --weather "sunny, 14C" --interest bird --interest garden --first-frost 2026-10-25
```

- Daylight/sunset: computed with the sunrise equation (`trailhead/sun.py`), stdlib only.
- The model only sees facts computed locally, so it can't invent sunset times.
- No model running? It falls back to a rule-based plan (`--no-llm` forces this).
- Swap models with `--model`; point at another machine with `--ollama-url`.

Tests: `python -m unittest discover -s tests` (Python 3.10+, no dependencies).
