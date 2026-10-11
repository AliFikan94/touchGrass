"""Compute the hard facts locally so the model never has to guess them."""
from dataclasses import dataclass, field
from datetime import date, datetime

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

    def lines(self):
        out = [
            f"Time free: {self.minutes_free} minutes",
            f"Daylight left: {self.daylight_min} minutes (sunset {self.sunset_local})",
            f"Season: {self.season}",
            f"Weather: {self.weather}",
        ]
        if self.interests:
            out.append("Interests: " + ", ".join(self.interests))
        if self.frost_in_days is not None:
            out.append(f"First frost in: {self.frost_in_days} days")
        return out


def season_for(day, lat):
    """Meteorological season, flipped for the southern hemisphere."""
    names = {12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 3, 10: 3, 11: 3}
    labels = ["winter", "spring", "summer", "autumn"]
    idx = names[day.month]
    if lat < 0:
        idx = (idx + 2) % 4
    return labels[idx]


def build_facts(now, lat, lon, minutes_free, weather="unknown", interests=None, first_frost=None):
    """`now` must be timezone-aware; `first_frost` is a date or None."""
    sun = sun_times(now.astimezone().date(), lat, lon)
    sunset = sun[1].astimezone(now.tzinfo).strftime("%H:%M") if sun else "n/a"
    frost = None
    if first_frost:
        frost = (first_frost - now.date()).days
    return Facts(
        minutes_free=minutes_free,
        daylight_min=daylight_left(now, lat, lon),
        sunset_local=sunset,
        season=season_for(now.date(), lat),
        weather=weather,
        interests=interests or [],
        frost_in_days=frost,
    )
