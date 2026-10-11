"""The quest library. Every Blade = one movement task + 1-3 observation tasks.

No equipment, no skill, no fishing. Water gets observation tasks, not catch goals.
"""
import random
from datetime import date

MOVEMENT = [
    {"id": "walk10", "text": "Walk for 10 minutes without stopping.", "min": 10},
    {"id": "walk15", "text": "Walk for 15 minutes without stopping.", "min": 15},
    {"id": "walk20", "text": "Walk for 20 minutes without stopping.", "min": 20},
    {"id": "green", "text": "Walk to the nearest park, tree or patch of green.", "min": 10},
    {"id": "water", "text": "Walk to water: a pond, river, fountain or puddle.", "min": 15},
    {"id": "hill", "text": "Take the route with a hill or uneven ground.", "min": 15},
    {"id": "light", "text": "Walk while the sun is close to the horizon.", "min": 15, "needs": "daylight_edge"},
    {"id": "sit", "text": "Sit outside for 10 minutes. Stillness counts.", "min": 10},
]

# interest tags: light, plants, trees, birds, senses, water, season, creative
OBSERVATION = [
    {"id": "sunset", "tag": "light", "text": "Catch the light: photograph the sunrise or sunset."},
    {"id": "lightshift", "tag": "light", "text": "Watch the light change for 5 minutes."},
    {"id": "moon", "tag": "light", "text": "Find the moon, day or night."},
    {"id": "clouds", "tag": "light", "text": "Watch the clouds for 3 minutes. Name one shape."},
    {"id": "sunflower", "tag": "plants", "text": "Record a sunflower or any flower opening or closing.", "seasons": ["summer", "autumn"]},
    {"id": "flowers3", "tag": "plants", "text": "Find three different flowers in bloom.", "seasons": ["spring", "summer", "autumn"]},
    {"id": "tall", "tag": "plants", "text": "Find a plant taller than you, and one shorter than your hand."},
    {"id": "newgrowth", "tag": "plants", "text": "Find new growth: a bud, a shoot, a fresh leaf.", "seasons": ["spring", "summer"]},
    {"id": "seedhead", "tag": "plants", "text": "Find a seed head or a piece of fruit.", "seasons": ["summer", "autumn"]},
    {"id": "leafcolor", "tag": "season", "text": "Find a leaf that is changing colour.", "seasons": ["autumn"]},
    {"id": "frost", "tag": "season", "text": "Look for frost patterns on grass or glass.", "seasons": ["autumn", "winter"]},
    {"id": "rainleaf", "tag": "season", "text": "Watch rain on leaves. Listen to it."},
    {"id": "different", "tag": "season", "text": "Find something that wasn't there last week."},
    {"id": "trees3", "tag": "trees", "text": "Find three trees taller than you."},
    {"id": "bark", "tag": "trees", "text": "Notice three different bark textures."},
    {"id": "treelife", "tag": "trees", "text": "Find a tree with something living on it: moss, lichen, a bird, an insect."},
    {"id": "under", "tag": "trees", "text": "Stand under a tree for two minutes and listen."},
    {"id": "birds3", "tag": "birds", "text": "See or hear three different birds."},
    {"id": "bird60", "tag": "birds", "text": "Watch one bird for 60 seconds without looking away."},
    {"id": "evidence", "tag": "birds", "text": "Find evidence of an animal: a feather, a nest, tracks, chewed leaves."},
    {"id": "insect", "tag": "birds", "text": "Notice an insect doing something."},
    {"id": "sounds5", "tag": "senses", "text": "Close your eyes and name five sounds."},
    {"id": "smell", "tag": "senses", "text": "Find something that smells good, or interesting."},
    {"id": "textures", "tag": "senses", "text": "Touch three natural textures: bark, leaf, stone, grass, soil."},
    {"id": "still3", "tag": "senses", "text": "Stand still for three minutes and just watch."},
    {"id": "water5", "tag": "water", "text": "Watch the water for five minutes.", "needs_move": "water"},
    {"id": "waterlife", "tag": "water", "text": "Find three things living in or near the water.", "needs_move": "water"},
    {"id": "reflect", "tag": "water", "text": "Notice how light moves on the water.", "needs_move": "water"},
    {"id": "grasslight", "tag": "creative", "text": "Photograph light hitting grass."},
    {"id": "skyground", "tag": "creative", "text": "Frame one photo with both sky and ground."},
    {"id": "pattern", "tag": "creative", "text": "Find a natural pattern: spirals, symmetry, repetition."},
]


def candidates(facts, interests=(), n=6, rng=None):
    """Pick movement + a shortlist of observations that fit time, season and interests."""
    rng = rng or random.Random(date.today().toordinal())
    fits = [m for m in MOVEMENT if m["min"] <= max(facts.minutes_free, 10)]
    if facts.daylight_min < 30:
        fits = [m for m in fits if m["id"] != "light"] or fits
    edge = 0 < facts.daylight_min < 90
    fits = [m for m in fits if m.get("needs") != "daylight_edge" or edge] or fits
    movement = rng.choice(fits)
    pool = [o for o in OBSERVATION
            if facts.season in o.get("seasons", [facts.season])
            and o.get("needs_move", movement["id"]) == movement["id"]]
    liked = [o for o in pool if o["tag"] in interests]
    rest = [o for o in pool if o not in liked]
    rng.shuffle(liked)
    rng.shuffle(rest)
    return movement, (liked + rest)[:n]


def fallback_blade(movement, obs, count=2):
    return {
        "movement": movement["text"],
        "observations": [o["text"] for o in obs[:count]],
        "closing": "Phone away. The grass is waiting.",
    }
