---
title: Blade: a daily walk, written by a model that never leaves your laptop
published: false
tags: devchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built

Blade is a daily outdoor ritual. You tell it how long you have and where you are, and it hands you one short Blade: a walk, and one to three small things to notice. Then it tells you to put the phone away.

That last part is the product. The screen's whole job is to hand over the task and get out of the way.

> Move. Walk for 15 minutes without stopping.
> Notice. See or hear three different birds.
> Phone away. The grass is waiting.

It is not a fitness tracker and not a bird encyclopedia. There is a streak, but it never scolds. Miss a day and it says: *No streak pressure. Just step outside when you can.* There is no leaderboard, on purpose. Ranking people turns a quiet habit into a contest, and it would need a server holding everyone's activity, which is the opposite of the point.

## Demo

<!-- TODO: screenshot of the card, plus 1-2 photos from the walk. A short screen recording if you can. -->

## Code

<!-- TODO: embed the repo: {% embed https://github.com/AliFikan94/touchGrass %} -->

Run it: `ollama pull gemma3:1b`, then `python main.py`. Python standard library only.

## How I Built It

**The model.** [Gemma](https://ai.google.dev/gemma), an open-weight model, runs locally through Ollama. It writes each Blade in a calm, plain voice defined in one prompt file (`blade/voice.py`).

**The model never decides the facts.** Blade works out the season, the daylight left and the climate band from your latitude and the date, in plain code, with no network. The model only phrases what it is given, from a menu of real tasks. If it replies with anything malformed, or isn't running, a deterministic Blade is served instead, so the app always works.

**Make it local (opt-in).** A switch on the page also looks up current weather ([Open-Meteo](https://open-meteo.com)), a place name (OpenStreetMap) and what other people recorded within 5 km in the last two weeks ([iNaturalist](https://www.inaturalist.org)). Then a task can say *"Look for a Northern Cardinal. Someone recorded one near here this week."* The species come from those records, never from the model's memory. A small model will happily invent a bird. It is off by default, your location is rounded to about 1 km before it is sent, and results are cached.

**Things that went wrong, honestly:**

- *It said `[fallback]` and I couldn't tell why.* The model path failed silently. I made it report the reason. The reason turned out to be: `model requires more system memory (4.0 GiB) than is available (2.5 GiB)`. My machine could not load the 4B model.
- *It loaded forever.* A small CPU-only machine can take minutes on the first request. The fix was a warm-up when the server starts, a cap on how much the model may write, a 60-second limit that falls back with the reason shown, and a live timer on screen.
- *Even the tropics needed care.* Latitude says "autumn" in October for most of the north, but not near the equator. Blade now knows there is no autumn there.

## Why Does Open Innovation Matter?

Four concrete things, not a slogan:

1. **Swapping the model was one setting.** When the 4B model would not fit in memory, I set `BLADE_MODEL=gemma3:1b` and carried on. With a closed API there is nothing to downgrade to; you either pay or you don't.
2. **It works with no signal.** The offline layer needs no network at all. A trail with no coverage is exactly where this should work.
3. **Your location stays yours.** The core app never sends it anywhere. The optional live layer says plainly what it sends, and rounds it first.
4. **It costs nothing to run.** No key, no meter, no account.

Where closed would have been better: the 1B model's writing is plainer than a frontier model's, and I had to constrain it hard (menu of tasks, validated JSON, fallback). I think that is the honest trade, and for a thing you read in ten seconds before leaving the house, I would make it again.

## How the walk went

<!-- TODO: this is the part only you can write. Facts so far, all real:
     I saw a dove, a pelican and a mango tree.
     Fill in, in your own words:
       - where you were and the time of day: [ ]
       - what the card actually told you to do: [ ]
       - did the model's text sound right? Which line, if any, felt off or good? [ ]
       - what you noticed that wasn't on the card: [ ]
       - how it felt to put the phone away: [ ]
     Keep it short and specific. One true surprise beats five general sentences. -->

## My Agent Session

<!-- Optional. Only if you actually save it with DevRelay or Entire; do not claim it otherwise. -->

## Prize Categories

- **Best Use of Gemma**: Gemma (via Ollama) writes every Blade, locally.
<!-- Add "Best Use of ElevenLabs" ONLY if you actually used the spoken Blade (--speak / Listen button). -->
<!-- Add "Best Use of Entire" ONLY if you embed or link the agent session in the post. -->
