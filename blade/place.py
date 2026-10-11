"""Offline place sense: climate band and what is typically showing, from latitude + date only.

This is deliberately coarse. Latitude can't tell desert from rainforest, so the notes stay
general and say so for the tropics. Live data (blade/live.py) adds the specifics.
"""

TEMPERATE = {
    "spring": ["buds breaking on trees and shrubs", "early flowers: bulbs, blossom, dandelions",
               "birds singing for territory and building nests", "the first insects on warm days"],
    "summer": ["full canopy and deep shade", "flowers at their peak, with bees and butterflies",
               "noisy young birds that have just left the nest", "long light in the evening"],
    "autumn": ["leaves turning and falling", "seed heads, berries, nuts and acorns",
               "birds gathering in flocks or moving south", "fungi after rain and first frosts at night"],
    "winter": ["bare branches that show nests and shapes", "evergreens standing out, frost on grass",
               "winter birds at hedges and feeders", "low sun and early sunsets"],
}
SUBTROPICAL = {
    "warm": ["flowering shrubs and trees", "heat in the afternoon, so early or late is better",
             "lizards and insects active", "afternoon storms possible"],
    "cool": ["mild days with many plants still green", "migrant birds spending the winter",
             "some trees flowering while others drop leaves", "cool mornings with dew"],
}
TROPICAL = ["plants growing and flowering all year", "birdsong loudest at dawn and dusk",
            "heat and humidity, so shade matters",
            "your local wet or dry season shapes the ground: new green after rain, dust and bare soil when dry"]
BOREAL = {
    "spring": ["snow melting, with mud and meltwater", "migrant birds returning", "buds still late"],
    "summer": ["very long days", "wildflowers brief and bright", "berries ripening late in the season"],
    "autumn": ["birch and aspen turning gold", "early frosts, berries and mushrooms", "geese moving south"],
    "winter": ["snow and ice, with animal tracks", "short days and a low sun", "only hardy resident birds"],
}
POLAR = {
    "warm": ["near-constant light, with low tundra plants flowering", "nesting seabirds and waders",
             "wet ground and insects"],
    "cool": ["snow, ice and long darkness", "aurora on clear nights", "tracks in the snow, few birds"],
}


def climate_band(lat):
    a = abs(lat)
    if a < 23.5:
        return "tropical"
    if a < 35:
        return "subtropical"
    if a < 55:
        return "temperate"
    if a < 66.5:
        return "boreal"
    return "polar"


def place_notes(lat, season):
    """Return (band, [notes]) for a latitude and a season label ('spring'..'winter' or 'tropical')."""
    band = climate_band(lat)
    if band == "tropical":
        return band, TROPICAL
    if band == "temperate":
        return band, TEMPERATE[season]
    if band == "boreal":
        return band, BOREAL[season]
    warm = season in ("spring", "summer")
    if band == "subtropical":
        return band, SUBTROPICAL["warm" if warm else "cool"]
    return band, POLAR["warm" if season == "summer" else "cool"]
