import unittest
from datetime import date, datetime, timedelta, timezone

from blade.facts import build_facts, season_for
from blade.sun import daylight_left, sun_times


class SunTests(unittest.TestCase):
    def test_london_summer_solstice(self):
        rise, sset = sun_times(date(2026, 6, 21), 51.5, -0.12)
        hours = (sset - rise).total_seconds() / 3600
        self.assertAlmostEqual(hours, 16.6, delta=0.3)
        self.assertEqual(rise.hour, 3)  # ~03:43 UTC

    def test_polar_night(self):
        self.assertIsNone(sun_times(date(2026, 12, 21), 80, 0))

    def test_daylight_left_after_sunset_is_zero(self):
        _, sset = sun_times(date(2026, 10, 11), 40.7, -74.0)
        self.assertEqual(daylight_left(sset + timedelta(minutes=5), 40.7, -74.0), 0)
        self.assertAlmostEqual(daylight_left(sset - timedelta(minutes=30), 40.7, -74.0), 30, delta=1)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 11, 15, 0, tzinfo=timezone.utc)

    def test_season_hemispheres(self):
        self.assertEqual(season_for(date(2026, 10, 11), 40), "autumn")
        self.assertEqual(season_for(date(2026, 10, 11), -33), "spring")

    def test_frost_countdown(self):
        f = build_facts(self.now, 40.7, -74.0, 30, first_frost=date(2026, 10, 20))
        self.assertEqual(f.frost_in_days, 9)


if __name__ == "__main__":
    unittest.main()
