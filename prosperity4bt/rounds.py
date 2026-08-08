"""Per-round product and position-limit registry.

Prosperity replaced the tradable universe as the competition went on, and every change
also changed the position limits. The upstream backtester carried a single hardcoded dict
holding the tutorial products, so anything else silently fell through to a default. This
module makes the per-round configuration explicit and is the one place to edit when a new
round is added.

Sources for the limits are noted per round. Where a limit is taken from a trader rather
than from a wiki page, that is because the wiki text was not archived.
"""

# Tutorial only. These two never appear in the round 1-5 datasets.
TUTORIAL_LIMITS: dict[str, int] = {
    "EMERALDS": 80,
    "TOMATOES": 80,
}

# Rounds 1 and 2 trade the same two products. Limits per traders/round1_final.py.
ROUND_1_2_LIMITS: dict[str, int] = {
    "ASH_COATED_OSMIUM": 80,
    "INTARIAN_PEPPER_ROOT": 80,
}

# Rounds 3 and 4: two underlyings plus the VEV option chain.
# Limits per traders/round3_trader.py and traders/round4_trader.py.
ROUND_3_4_LIMITS: dict[str, int] = {
    "HYDROGEL_PACK": 200,
    "VELVETFRUIT_EXTRACT": 200,
    **{f"VEV_{strike}": 300 for strike in
       [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]},
}

# Round 5 wiki: "All products have a position limit of 10". 10 groups of 5.
ROUND_5_GROUPS: dict[str, list[str]] = {
    "GALAXY_SOUNDS": ["BLACK_HOLES", "DARK_MATTER", "PLANETARY_RINGS", "SOLAR_FLAMES", "SOLAR_WINDS"],
    "SLEEP_POD": ["COTTON", "LAMB_WOOL", "NYLON", "POLYESTER", "SUEDE"],
    "MICROCHIP": ["CIRCLE", "OVAL", "RECTANGLE", "SQUARE", "TRIANGLE"],
    "PEBBLES": ["XS", "S", "M", "L", "XL"],
    "ROBOT": ["DISHES", "IRONING", "LAUNDRY", "MOPPING", "VACUUMING"],
    "UV_VISOR": ["AMBER", "MAGENTA", "ORANGE", "RED", "YELLOW"],
    "TRANSLATOR": ["ASTRO_BLACK", "ECLIPSE_CHARCOAL", "GRAPHITE_MIST", "SPACE_GRAY", "VOID_BLUE"],
    "PANEL": ["1X2", "1X4", "2X2", "2X4", "4X4"],
    "OXYGEN_SHAKE": ["CHOCOLATE", "EVENING_BREATH", "GARLIC", "MINT", "MORNING_BREATH"],
    "SNACKPACK": ["CHOCOLATE", "PISTACHIO", "RASPBERRY", "STRAWBERRY", "VANILLA"],
}

ROUND_5_LIMITS: dict[str, int] = {
    f"{group}_{variant}": 10
    for group, variants in ROUND_5_GROUPS.items()
    for variant in variants
}

LIMITS_BY_ROUND: dict[int, dict[str, int]] = {
    0: TUTORIAL_LIMITS,
    1: ROUND_1_2_LIMITS,
    2: ROUND_1_2_LIMITS,
    3: ROUND_3_4_LIMITS,
    4: ROUND_3_4_LIMITS,
    5: ROUND_5_LIMITS,
}

# Product names are unique across rounds, so a flat lookup is unambiguous and the runner
# does not need to know which round it is in.
ALL_LIMITS: dict[str, int] = {
    product: limit
    for limits in LIMITS_BY_ROUND.values()
    for product, limit in limits.items()
}


def limits_for_round(round_num: int) -> dict[str, int]:
    """Products and position limits for one round."""
    return dict(LIMITS_BY_ROUND.get(round_num, {}))
