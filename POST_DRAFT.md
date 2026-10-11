---
title: Blade: a daily walk, written on your own machine
published: false
tags: devchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

> Your phone will still be there when you get back.

## What I Built

Blade is a daily outdoor ritual. You tell it how long you have and where you are. It hands you one short Blade: a walk, and a few small things to notice. Then it tells you to put the phone away.

That last line is the product. The screen's whole job is to hand over the task and get out of the way.

```
Move.
  Walk to the nearest park.

Notice.
  - See or hear different birds.

Phone away. The grass is waiting.
```

When you come back, you can tell Blade what you saw, and it answers in a line or two. A small streak counts your days, and it never scolds: miss one and it says *No streak pressure. Just step outside when you can.*

It is for anyone who wants a reason to go outside for fifteen minutes, in a city park, on a suburban street, or on a real trail. It is not a fitness tracker and not a bird encyclopedia.

There is no leaderboard, on purpose. Ranking people turns a quiet habit into a contest, and it would need a server holding everyone's activity. That is the opposite of why I chose open models.

## Demo

<!-- TODO: screenshot of the card, and one or two photos from the walk. A short screen recording if you can. -->

Blade runs on your own machine, so there is no hosted link. That is the point. To try it: `ollama pull gemma3:1b`, then `python main.py`.

## Code

<!-- TODO: embed the repo: {% embed https://github.com/AliFikan94/touchGrass %} -->

```
touchGrass/
├── main.py            # python main.py opens the local page
├── blade/
│   ├── quests.py      # the quest library: movement + observation tasks
│   ├── facts.py       # season, daylight, climate: plain code, no network
│   ├── sun.py         # sunrise and sunset from the sunrise equation
│   ├── place.py       # what is typically showing at this latitude and date
│   ├── generate.py    # facts -> Gemma -> validated JSON, or a fallback
│   ├── reflect.py     # the short reply after your walk
│   ├── live.py        # optional weather and recent sightings (opt-in)
│   ├── voice.py       # the whole brand voice, as prompts you can edit
│   ├── llm.py         # tiny Ollama client
│   ├── log.py         # local streak and notes
│   └── web.py, page.html
└── tests/             # 41 tests, standard library only
```

## How I Built It

**The open pieces.** [Gemma](https://ai.google.dev/gemma), an open-weight model, runs locally through [Ollama](https://ollama.com). It writes each Blade in a calm, plain voice defined in one prompt file. The app is Python's standard library and one HTML page. There is no framework, no account and no key.

**The model never decides the facts.** Season, daylight left and climate band are worked out in plain code from your latitude and the date. The model gets one movement task and a menu of real observation tasks, and phrases them as JSON. I validate that JSON. If it is malformed, or the model is not running, a Blade is served from the quest library instead, so the app always works.

**Make it local (opt-in).** A checkbox also looks up current weather ([Open-Meteo](https://open-meteo.com)), a place name (OpenStreetMap) and what other people recorded within 5 km in the last two weeks ([iNaturalist](https://www.inaturalist.org)). Then a task can say *"Look for a Northern Cardinal. Someone recorded one near here in the last two weeks."* The species come from those records, never from the model's memory, because a small model will happily invent a bird. It is off by default, your location is rounded to about 1 km before it is sent, and results are cached.

**After the walk.** An optional box asks what you noticed. Gemma replies, but it only ever sees your own words and today's tasks. Its reply is trimmed to two calm sentences and anything that asks a question or comes back empty is dropped for a plain fixed line.

### What broke

- **It said `[fallback]` and I could not tell why.** The model path failed silently. I made it report the reason, and the reason was: `model requires more system memory (4.0 GiB) than is available (2.5 GiB)`. My machine could not load the 4B model.
- **It loaded forever.** A small CPU-only machine can take minutes on the first request. The fix was a warm-up when the server starts, a cap on how much the model may write, a 60-second limit that falls back and shows the reason, and a live timer on screen.
- **The tropics have no autumn.** Latitude alone said "autumn" in October for anywhere north of the equator. Blade now knows better near the equator.
- **It told me to watch rain on a dry day.** I found this one on the walk, below. The rain task was not tied to the weather at all.

## The walk

I went out from 4:01 to 4:28 pm in Lagos, Nigeria: 27 minutes. The card said:

- Walk to the nearest park.
- Watch rain on leaves. Listen to it.
- See or hear different birds.

There was no rain. That was a bug, and the walk is what found it. Rain tasks now appear only when the weather says rain, and frost tasks only in cold climates. The fix has a test for Lagos on a dry day. I would not have caught it at my desk.

What I noticed, on my own and not from the card: a dove, a pelican and a mango tree.

When I got back I told Blade. It said:

> [PASTE GEMMA'S EXACT REPLY HERE]

<!-- TODO: one honest sentence on how it felt to put the phone away. Leave it out if nothing comes. -->

## Why Does Open Innovation Matter?

**1. Swapping the model was one setting.**
The 4B model would not fit in memory. I set `BLADE_MODEL=gemma3:1b` and carried on. With a closed API there is nothing to downgrade to; you pay or you do not.

**2. The core works with no signal.**
Season, daylight and climate are computed on the device, and the model runs locally. A trail with no coverage is exactly where this should work. The optional live layer needs a network, and it fails soft: with none, you get the offline Blade.

**3. Your place stays yours.**
The core app never sends your location anywhere. The live layer is off by default, says plainly what it sends and where, and rounds it first.

**4. It costs nothing to run.**
No key, no meter, no account.

**Where closed would be better.** The 1B model writes plainer than a frontier model does, so I constrained it hard: a menu of real tasks, validated JSON, a fallback. For a card you read in ten seconds before leaving the house, I would make that trade again.

## Prize Categories

- **Best Use of Gemma:** Gemma, run locally through Ollama, writes every Blade and every reply.

Step outside. Touch a blade. Notice the world.
