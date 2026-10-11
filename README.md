# Blade

**Step outside. Touch a blade. Notice the world.**

Blade is a daily outdoor ritual. Each day you get one short *Blade*: a movement task (usually a
10-20 minute walk) and one to three light observation tasks (a sunflower opening, three birds,
three tree barks, the colour of the sky). The screen hands you the Blade, then gets out of the way.

A **local open-weight model (Gemma via [Ollama](https://ollama.com))** writes each Blade in Blade's
voice from a curated quest library, grounded in facts computed on your device (season, daylight left).
No cloud, no API key, no account, no analytics. Your location and your log never leave your machine.

## Run it

```
ollama pull gemma3:4b
python -m blade today --lat 40.7 --lon -74 --minutes 20 --interest birds
python -m blade serve            # local web page at http://127.0.0.1:8317
python -m blade done             # log it (local file: ~/.blade/log.jsonl)
python -m blade look leaf.jpg    # ask the local vision model about a photo
```

Optional: hear it instead of reading it. Set `ELEVENLABS_API_KEY` (and optionally `ELEVENLABS_VOICE_ID`) and
run `python -m blade today ... --speak blade.mp3`, or use the **Listen** button on the web page (it only
appears when a key is set). Only the Blade text is sent; location, photos and your log never are.
Without a key nothing changes: Blade stays fully local.

Python 3.10+, standard library only. Tests: `python -m unittest discover -s tests`.

## How it works

- `quests.py` is the library: movement + observation quests, filtered by time, season, interest.
  No equipment and no fishing. Water gets watching tasks, not catch goals.
- `facts.py` / `sun.py` compute season and daylight offline (sunrise equation), so the model cannot invent them.
- `generate.py` sends Gemma the facts, one movement task and a menu of observations; it replies in JSON.
  Output is validated; if the model is missing or misbehaves, a deterministic Blade is served instead,
  so it works on a trail with no signal and no model at all (`--no-llm` forces this).
- `voice.py` is the whole brand voice as one editable prompt. Swap the model with `--model`.
- `log.py` stores completions locally. Missed day copy: "No streak pressure. Just step outside when you can."

## Why open

Offline on the trail; location and photos stay private; free to run; swap or fine-tune the model;
change the voice by editing a text file.
