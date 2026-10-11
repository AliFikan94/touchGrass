"""Turn facts into a plan: local model first, deterministic fallback second."""
from .llm import LLMUnavailable, generate


def build_prompt(facts):
    return "Facts:\n" + "\n".join(f"- {l}" for l in facts.lines()) + "\n\nWrite the plan."


def fallback_plan(facts):
    """Rule-based plan used when no local model is running (e.g. first run, low-end device)."""
    usable = min(facts.minutes_free, facts.daylight_min)
    wet = any(w in facts.weather.lower() for w in ("rain", "storm", "snow"))
    if usable < 10:
        head = "Step outside for a few minutes anyway."
        steps = [("3", "Stand on the doorstep or balcony and look at the horizon.")]
    else:
        head = f"{usable} minutes of daylight is plenty. Go."
        walk = max(usable - 10, 5)
        steps = [
            ("5", "Shoes on, phone in a pocket on silent."),
            (str(walk), "Walk a loop you can finish before sunset, " +
             ("with a rain jacket." if wet else "no destination required.")),
            ("5", "Find three things that changed since last week and look closely.")]
    if "bird" in facts.interests:
        steps.append(("5", "Stop and listen. Count how many different calls you hear."))
    if "garden" in facts.interests:
        if facts.frost_in_days is not None and 0 <= facts.frost_in_days <= 14:
            steps.append(("10", f"Frost is {facts.frost_in_days} days away: harvest tender crops or cover them."))
        else:
            steps.append(("10", "Check your beds: water, weed, and note what is ready."))
    if "foliage" in facts.interests and facts.season == "autumn":
        steps.append(("5", "Pick the tree with the best colour and photograph it once, then stop."))
    lines = [head] + [f"{i}. ({m} min) {t}" for i, (m, t) in enumerate(steps, 1)]
    lines.append("Phone away. See you out there.")
    return "\n".join(lines)


def make_plan(facts, model, url, use_llm=True):
    """Return (plan_text, source) where source is 'model' or 'fallback'."""
    if use_llm:
        try:
            return generate(build_prompt(facts), model=model, url=url), "model"
        except LLMUnavailable:
            pass
    return fallback_plan(facts), "fallback"
