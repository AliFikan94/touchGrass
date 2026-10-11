"""Sunrise/sunset from the NOAA-style sunrise equation. Pure stdlib, no network."""
import math
from datetime import datetime, timedelta, timezone

J2000 = 2451545.0


def _julian(dt):
    return dt.timestamp() / 86400.0 + 2440587.5


def _from_julian(jd):
    return datetime.fromtimestamp((jd - 2440587.5) * 86400.0, tz=timezone.utc)


def sun_times(day, lat, lon):
    """Return (sunrise, sunset) as aware UTC datetimes, or None in polar day/night.

    `day` is a datetime.date; `lon` is east-positive degrees.
    """
    noon = datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc)
    n = math.ceil(_julian(noon) - J2000 + 69.184 / 86400.0)
    j_star = n - lon / 360.0
    m = (357.5291 + 0.98560028 * j_star) % 360
    mr = math.radians(m)
    c = 1.9148 * math.sin(mr) + 0.0200 * math.sin(2 * mr) + 0.0003 * math.sin(3 * mr)
    lam = math.radians((m + c + 180 + 102.9372) % 360)
    transit = J2000 + j_star + 0.0053 * math.sin(mr) - 0.0069 * math.sin(2 * lam)
    sin_dec = math.sin(lam) * math.sin(math.radians(23.4397))
    dec = math.asin(sin_dec)
    phi = math.radians(lat)
    cos_w = (math.sin(math.radians(-0.833)) - math.sin(phi) * sin_dec) / (
        math.cos(phi) * math.cos(dec)
    )
    if cos_w > 1 or cos_w < -1:
        return None
    w = math.degrees(math.acos(cos_w))
    return _from_julian(transit - w / 360.0), _from_julian(transit + w / 360.0)


def daylight_left(now, lat, lon):
    """Minutes of daylight remaining at aware datetime `now` (0 after sunset)."""
    utc = now.astimezone(timezone.utc)
    # the sun event for a given UTC date may fall on the adjacent date; check both
    for offset in (0, -1, 1):
        times = sun_times(utc.date() + timedelta(days=offset), lat, lon)
        if times and times[0] <= utc <= times[1]:
            return int((times[1] - utc).total_seconds() // 60)
    return 0
