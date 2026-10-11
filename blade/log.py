"""Local-only completion log: ~/.blade/log.jsonl (override with BLADE_HOME). Nothing is uploaded."""
import json
import os
from datetime import date, timedelta
from pathlib import Path


def _path():
    home = Path(os.environ.get("BLADE_HOME", Path.home() / ".blade"))
    home.mkdir(parents=True, exist_ok=True)
    return home / "log.jsonl"


def record(blade, day=None):
    entry = {"date": (day or date.today()).isoformat(), "blade": blade}
    with open(_path(), "a") as f:
        f.write(json.dumps(entry) + "\n")


def days_done():
    p = _path()
    if not p.exists():
        return set()
    return {json.loads(l)["date"] for l in p.read_text().splitlines() if l.strip()}


def stats(today=None):
    """Streak counts back from today, or from yesterday if today isn't done yet. No guilt either way."""
    today = today or date.today()
    done = days_done()
    cur = today if today.isoformat() in done else today - timedelta(days=1)
    streak = 0
    while cur.isoformat() in done:
        streak += 1
        cur -= timedelta(days=1)
    week = [(today - timedelta(days=i)).isoformat() in done for i in range(6, -1, -1)]  # oldest first
    return {"total": len(done), "streak": streak, "done_today": today.isoformat() in done, "week": week}


def message(s):
    if s["done_today"]:
        return "Blade complete. The day is different now."
    if s["total"] == 0:
        return "The grass is waiting."
    if s["streak"] == 0:
        return "No streak pressure. Just step outside when you can."
    return f"Blade streak: {s['streak']} days"
