"""Facts -> Blade. Local model first, deterministic fallback second."""
from .llm import LLMUnavailable, generate
from .quests import candidates, fallback_blade
from .voice import SYSTEM


def _prompt(facts, movement, obs):
    menu = "\n".join(f"- {o['text']}" for o in obs)
    return ("FACTS:\n" + "\n".join(f"- {l}" for l in facts.lines())
            + f"\n\nMOVEMENT: {movement['text']}\n\nOBSERVATIONS MENU:\n{menu}\n\nWrite today's Blade.")


def _valid(d):
    return (isinstance(d, dict) and isinstance(d.get("movement"), str) and d["movement"].strip()
            and isinstance(d.get("observations"), list) and 1 <= len(d["observations"]) <= 3
            and all(isinstance(o, str) and o.strip() for o in d["observations"])
            and isinstance(d.get("closing"), str) and d["closing"].strip())


def make_blade(facts, interests=(), model="gemma3:4b", url="http://localhost:11434",
               use_llm=True, rng=None):
    """Return (blade_dict, source) where source is 'model' or 'fallback'."""
    import json
    movement, obs = candidates(facts, interests, rng=rng)
    if use_llm:
        try:
            raw = generate(_prompt(facts, movement, obs), SYSTEM, model, url, as_json=True)
            data = json.loads(raw)
            if _valid(data):
                data["observations"] = [o.strip() for o in data["observations"]]
                return data, "model"
        except (LLMUnavailable, json.JSONDecodeError):
            pass
    return fallback_blade(movement, obs), "fallback"
