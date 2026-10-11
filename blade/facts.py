"""Compute the hard facts locally so the model never has to guess them."""
from dataclasses import dataclass, field
from datetime import date, datetime

from .place import place_notes
from .sun import daylight_left, sun_times


@dataclass
class Facts:
    minutes_free: int
    daylight_min: int
    sunset_local: str
    season: str
    weather: str
    interests: list = field(default_factory=list)
    frost_in_days: int | None = None
    climate: str = ""
    place_notes: list = field(default_factory=list)
    place_name: str | None = None
    sightings: list = field(default_factory=list)
    season_key: str = ""  # season used to filter quests; the tropics count as 'summer' (growing all year)

    def lines(self):
        out = [
            f"Time free: {self.minutes_free} minutes",
            f"Daylight left: {self.daylight_min} minutes (sunset {self.sunset_local})",
            f"Season: {self.season}" + (f" ({self.climate} climate)" if self.climate else ""),
            f"Weather: {self.weather}",
        ]
        if self.place_name:
            out.append(f"Place: {self.place_name}")
        if self.place_notes:
            out.append("Typical here at this time of year: " + "; ".join(self.place_notes))
        if self.sightings:
            groups = {}
            for s in self.sightings:
                groups.setdefault(s["group"], []).append(s["common"])
            out.append("Recorded by others within 5 km in the last two weeks: "
                       + ". ".join(f"{g}: {', '.join(v)}" for g, v in groups.items()))
        if self.interests:
            out.append("Interests: " + ", ".join(self.interests))
        if self.frost_in_days is not None:
            out.append(f"First frost in: {self.frost_in_days} days")
        return out


def season_for(day, lat):
    """Meteorological season, flipped for the southern hemisphere. 'tropical' inside the tropics."""
    if abs(lat) < 23.5:
        return "tropical"
    names = {12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 3, 10: 3, 11: 3}
    labels = ["winter", "spring", "summer", "autumn"]
    idx = names[day.month]
    if lat < 0:
        idx = (idx + 2) % 4
    return labels[idx]


def build_facts(now, lat, lon, minutes_free, weather="unknown", interests=None, first_frost=None,
                live=None):
    """`now` must be timezone-aware; `first_frost` is a date or None."""
    sun = sun_times(now.astimezone().date(), lat, lon)
    sunset = sun[1].astimezone(now.tzinfo).strftime("%H:%M") if sun else "n/a"
    frost = None
    if first_frost:
        frost = (first_frost - now.date()).days
    live = live or {}
    season = season_for(now.date(), lat)
    band, notes = place_notes(lat, season)
    return Facts(
        minutes_free=minutes_free,
        daylight_min=daylight_left(now, lat, lon),
        sunset_local=sunset,
        season=season,
        weather=live.get("weather") or weather,
        interests=interests or [],
        frost_in_days=frost,
        climate=band,
        place_notes=list(notes),
        place_name=live.get("place"),
        sightings=live.get("sightings") or [],
        season_key="summer" if season == "tropical" else season,
    )
