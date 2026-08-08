from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from prosperity4bt.datamodel import Symbol, Trade
from prosperity4bt.file_reader import FileReader

DEFAULT_POSITION_LIMIT = 80

# Round 1 wiki.
ROUND_1_LIMITS: dict[str, int] = {"EMERALDS": 80, "TOMATOES": 80}

# Round 5 wiki: "All products have a position limit of 10".
ROUND_5_PRODUCTS = [
    f"{group}_{variant}"
    for group, variants in {
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
    }.items()
    for variant in variants
]

# Rounds 3-4: the two underlyings plus the VEV option chain.
ROUND_3_4_LIMITS: dict[str, int] = {
    "HYDROGEL_PACK": 200,
    "VELVETFRUIT_EXTRACT": 200,
    **{f"VEV_{strike}": 300 for strike in [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]},
}

LIMITS: dict[str, int] = {
    **ROUND_1_LIMITS,
    **ROUND_3_4_LIMITS,
    **{product: 10 for product in ROUND_5_PRODUCTS},
}


def get_position_limit(symbol: str, overrides: Optional[dict[str, int]] = None) -> int:
    if overrides is not None and symbol in overrides:
        return overrides[symbol]
    return LIMITS.get(symbol, DEFAULT_POSITION_LIMIT)


@dataclass
class PriceRow:
    day: int
    timestamp: int
    product: Symbol
    bid_prices: list[int]
    bid_volumes: list[int]
    ask_prices: list[int]
    ask_volumes: list[int]
    mid_price: float
    profit_loss: float


def get_column_values(columns: list[str], indices: list[int]) -> list[int]:
    values = []

    for index in indices:
        value = columns[index]
        if value == "":
            break

        values.append(int(value))

    return values


@dataclass
class ObservationRow:
    timestamp: int
    bidPrice: float
    askPrice: float
    transportFees: float
    exportTariff: float
    importTariff: float
    sugarPrice: float
    sunlightIndex: float


@dataclass
class BacktestData:
    round_num: int
    day_num: int

    prices: dict[int, dict[Symbol, PriceRow]]
    trades: dict[int, dict[Symbol, list[Trade]]]
    observations: dict[int, ObservationRow]
    products: list[Symbol]
    profit_loss: dict[Symbol, float]


def create_backtest_data(
    round_num: int, day_num: int, prices: list[PriceRow], trades: list[Trade], observations: list[ObservationRow]
) -> BacktestData:
    prices_by_timestamp: dict[int, dict[Symbol, PriceRow]] = defaultdict(dict)
    for row in prices:
        prices_by_timestamp[row.timestamp][row.product] = row

    trades_by_timestamp: dict[int, dict[Symbol, list[Trade]]] = defaultdict(
        lambda: defaultdict(list))
    for trade in trades:
        trades_by_timestamp[trade.timestamp][trade.symbol].append(trade)

    products = sorted(set(row.product for row in prices))
    profit_loss = {product: 0.0 for product in products}

    observations_by_timestamp = {row.timestamp: row for row in observations}

    return BacktestData(
        round_num=round_num,
        day_num=day_num,
        prices=prices_by_timestamp,
        trades=trades_by_timestamp,
        observations=observations_by_timestamp,
        products=products,
        profit_loss=profit_loss,
    )


def has_day_data(file_reader: FileReader, round_num: int, day_num: int) -> bool:
    with file_reader.file([f"round{round_num}", f"prices_round_{round_num}_day_{day_num}.csv"]) as file:
        return file is not None


def read_day_data(file_reader: FileReader, round_num: int, day_num: int, no_names: bool) -> BacktestData:
    prices = []
    with file_reader.file([f"round{round_num}", f"prices_round_{round_num}_day_{day_num}.csv"]) as file:
        if file is None:
            raise ValueError(
                f"Prices data is not available for round {round_num} day {day_num}")

        for line in file.read_text(encoding="utf-8").splitlines()[1:]:
            columns = line.split(";")

            prices.append(
                PriceRow(
                    day=int(columns[0]),
                    timestamp=int(columns[1]),
                    product=columns[2],
                    bid_prices=get_column_values(columns, [3, 5, 7]),
                    bid_volumes=get_column_values(columns, [4, 6, 8]),
                    ask_prices=get_column_values(columns, [9, 11, 13]),
                    ask_volumes=get_column_values(columns, [10, 12, 14]),
                    mid_price=float(columns[15]),
                    profit_loss=float(columns[16]),
                )
            )

    trades = []
    with file_reader.file([f"round{round_num}", f"trades_round_{round_num}_day_{day_num}.csv"]) as file:
        if file is not None:
            for line in file.read_text(encoding="utf-8").splitlines()[1:]:
                columns = line.split(";")

                trades.append(
                    Trade(
                        symbol=columns[3],
                        price=int(float(columns[5])),
                        quantity=int(columns[6]),
                        buyer=columns[1],
                        seller=columns[2],
                        timestamp=int(columns[0]),
                    )
                )

    observations = []
    with file_reader.file([f"round{round_num}", f"observations_round_{round_num}_day_{day_num}.csv"]) as file:
        if file is not None:
            for line in file.read_text(encoding="utf-8").splitlines()[1:]:
                columns = line.split(",")

                observations.append(
                    ObservationRow(
                        timestamp=int(columns[0]),
                        bidPrice=float(columns[1]),
                        askPrice=float(columns[2]),
                        transportFees=float(columns[3]),
                        exportTariff=float(columns[4]),
                        importTariff=float(columns[5]),
                        sugarPrice=float(columns[6]),
                        sunlightIndex=float(columns[7]),
                    )
                )

    return create_backtest_data(round_num, day_num, prices, trades, observations)
