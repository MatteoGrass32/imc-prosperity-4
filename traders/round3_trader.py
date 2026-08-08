import json
import math
from typing import Any, Optional

from datamodel import (
    Listing,
    Observation,
    Order,
    OrderDepth,
    ProsperityEncoder,
    Symbol,
    Trade,
    TradingState,
)


# ─────────────────────────────────────────────────────────────
#  LOGGER  (verbatim from sample)
# ─────────────────────────────────────────────────────────────


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(
        self,
        state: TradingState,
        orders: dict[Symbol, list[Order]],
        conversions: int,
        trader_data: str,
    ) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )
        max_item_length = (self.max_log_length - base_length) // 3
        print(
            self.to_json(
                [
                    self.compress_state(
                        state, self.truncate(state.traderData, max_item_length)
                    ),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )
        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        return [[l.symbol, l.product, l.denomination] for l in listings.values()]

    def compress_order_depths(
        self, order_depths: dict[Symbol, OrderDepth]
    ) -> dict[Symbol, list[Any]]:
        return {s: [od.buy_orders, od.sell_orders] for s, od in order_depths.items()}

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        return [
            [t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
            for arr in trades.values()
            for t in arr
        ]

    def compress_observations(self, observations: Observation) -> list[Any]:
        co = {
            p: [
                o.bidPrice,
                o.askPrice,
                o.transportFees,
                o.exportTariff,
                o.importTariff,
                o.sugarPrice,
                o.sunlightIndex,
            ]
            for p, o in observations.conversionObservations.items()
        }
        return [observations.plainValueObservations, co]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        return [[o.symbol, o.price, o.quantity] for arr in orders.values() for o in arr]

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        lo, hi, out = 0, min(len(value), max_length), ""
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = value[:mid]
            if len(candidate) < len(value):
                candidate += "..."
            if len(json.dumps(candidate)) <= max_length:
                out = candidate
                lo = mid + 1
            else:
                hi = mid - 1
        return out


logger = Logger()


# ─────────────────────────────────────────────────────────────
#  CONSTANTS
#
#  THEORY: All 10 vouchers are European calls on VEV, expiring
#  after a fixed number of days.  r = 0, so the fair value is:
#
#      C(S, K, T, σ) = S·N(d₁) − K·N(d₂)
#      d₁ = [ln(S/K) + ½σ²T] / (σ√T)
#      d₂ = d₁ − σ√T
#
#  σ_annual ≈ 0.24 (flat smile, confirmed across all strikes and days)
#
#  T IS NOT HARDCODED.  We invert the BS formula each tick using
#  the VEV_5300 market price to recover the prevailing TTE.
#  This makes the strategy correct for:
#    - Historical backtesting (T₀ = 8, 7, 6 days per day 0/1/2)
#    - Actual Round 3 submission (T₀ = 5 days)
#
#  Three bugs fixed vs previous version:
#  1. Cold-start: T_ema initialised DIRECTLY from calibration on
#     tick 0, not from a 5-day fallback that takes ~100 ticks to
#     converge.  A slow convergence caused spurious sell-takes on
#     every ATM option for the first ~1000 timestamps.
#  2. Double-subtraction: calibrate_tte() already returns the
#     current remaining TTE.  The old code subtracted elapsed
#     time again, underestimating T progressively through the day.
#  3. Market-EMA FV blend: blending BS with the market mid is
#     theoretically imprecise and caused takes when the market
#     EMA lagged S.  With a correctly calibrated T, BS IS the
#     fair value; no blend needed.
# ─────────────────────────────────────────────────────────────

SIGMA = 0.24  # annualised implied vol (flat smile, calibrated empirically)

POSITION_LIMITS: dict[str, int] = {
    "HYDROGEL_PACK": 200,
    "VELVETFRUIT_EXTRACT": 200,
    "VEV_4000": 300,
    "VEV_4500": 300,
    "VEV_5000": 300,
    "VEV_5100": 300,
    "VEV_5200": 300,
    "VEV_5300": 300,
    "VEV_5400": 300,
    "VEV_5500": 300,
}

# Strike → half_spread, take_edge, clip, max_take_lots
# Deep ITM (4000/4500): wide mkt spread → large edge, quote freely
# Near-ATM  (5000-5300): moderate spread, be careful with delta exposure
# OTM       (5400/5500): tight spread (1-2 ticks), active flow
# Far OTM   (6000/6500): price = min-tick (0.5), no edge → skip
OPTION_PARAMS: dict[str, tuple] = {
    "VEV_4000": (3.5, 5.0, 25, 20),
    "VEV_4500": (3.5, 5.0, 25, 20),
    "VEV_5000": (3.0, 4.0, 20, 15),  # wider HS: delta≈0.92, high adv-sel cost
    "VEV_5100": (2.0, 3.0, 20, 15),
    "VEV_5200": (1.5, 2.5, 18, 15),
    "VEV_5300": (1.2, 2.0, 18, 15),
    #"VEV_5400": (0.8, 1.2, 15, 12), SPENTO, come quelli a 6000 e 6500
    "VEV_5500": (0.8, 1.2, 15, 12),
}
OPTION_STRIKES: dict[str, int] = {s: int(s.split("_")[1]) for s in OPTION_PARAMS}


# ─────────────────────────────────────────────────────────────
#  MATH
# ─────────────────────────────────────────────────────────────


def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_call(S: float, K: float, T: float, sigma: float) -> float:
    """European call, r=0, T in years."""
    if T <= 0.0:
        return max(0.0, S - K)
    sigma = max(1e-9, sigma)
    sq = sigma * math.sqrt(T)
    d1 = (math.log(max(S, 1e-9) / K) + 0.5 * sigma * sigma * T) / sq
    return max(0.0, S * _ncdf(d1) - K * _ncdf(d1 - sq))


def bs_delta(S: float, K: float, T: float, sigma: float) -> float:
    if T <= 0.0:
        return 1.0 if S > K else 0.0
    sigma = max(1e-9, sigma)
    d1 = (math.log(max(S, 1e-9) / K) + 0.5 * sigma * sigma * T) / (sigma * math.sqrt(T))
    return _ncdf(d1)


def calibrate_tte(C_mkt: float, S: float, K: float, sigma: float = SIGMA) -> float:
    """
    Invert BS for T (years) given an observed call price.
    Returns current remaining TTE — caller must NOT subtract elapsed time.
    Uses VEV_5300 (K=5300) as anchor: has meaningful time-value across 5-8 day range.
    """
    intrinsic = max(0.0, S - K)
    if C_mkt <= intrinsic + 0.05:
        return 0.3 / 365.0  # option at intrinsic → near-zero T
    lo, hi = 0.1 / 365.0, 30.0 / 365.0
    for _ in range(54):
        m = (lo + hi) * 0.5
        if bs_call(S, K, m, sigma) < C_mkt:
            lo = m
        else:
            hi = m
    return (lo + hi) * 0.5


class Trader:

    # ── micro helpers ─────────────────────────────────────────

    def _best(self, od: OrderDepth) -> tuple[Optional[int], Optional[int]]:
        bid = max(od.buy_orders) if od.buy_orders else None
        ask = min(od.sell_orders) if od.sell_orders else None
        return bid, ask

    def _clean_mid(self, od: OrderDepth, min_vol: int = 2) -> Optional[float]:
        bids = sorted(od.buy_orders.items(), reverse=True)
        asks = sorted(od.sell_orders.items())
        if not bids or not asks:
            b, a = self._best(od)
            return (b + a) / 2.0 if b is not None and a is not None else None
        b = bids[0][0] if abs(bids[0][1]) >= min_vol or len(bids) == 1 else bids[1][0]
        a = asks[0][0] if abs(asks[0][1]) >= min_vol or len(asks) == 1 else asks[1][0]
        return (b + a) / 2.0

    def _cap_buy(self, prod: str, pos: int) -> int:
        return max(0, POSITION_LIMITS[prod] - pos)

    def _cap_sell(self, prod: str, pos: int) -> int:
        return max(0, POSITION_LIMITS[prod] + pos)

    # ── taking ────────────────────────────────────────────────

    def _take(self, prod: str, od: OrderDepth, fv: float, pos: int, edge: float, max_lots: int = 9999) -> tuple[list[Order], int]:
        orders: list[Order] = []
        buy_cap = min(self._cap_buy(prod, pos), max_lots)
        for ask in sorted(od.sell_orders):
            if ask > fv - edge or buy_cap <= 0: break
            qty = min(-od.sell_orders[ask], buy_cap)
            if qty > 0:
                orders.append(Order(prod, ask, qty))
                pos += qty; buy_cap -= qty

        sell_cap = min(self._cap_sell(prod, pos), max_lots)
        for bid in sorted(od.buy_orders, reverse=True):
            if bid < fv + edge or sell_cap <= 0: break
            qty = min(od.buy_orders[bid], sell_cap)
            if qty > 0:
                orders.append(Order(prod, bid, -qty))
                pos -= qty; sell_cap -= qty
        return orders, pos

    # ── passive quoting (LOGICA MODIFICATA) ────────────────────

    def _quote(self, prod: str, od: OrderDepth, fv: float, pos: int, half_spread: float, clip: int, delta_skew: float = 0.0) -> list[Order]:
        bid0, ask0 = self._best(od)
        if bid0 is None or ask0 is None: return []
        limit = POSITION_LIMITS[prod]

        # SKEW RADIALE - Gestione differenziata per ridurre Drawdown sul Gel
        if prod == "HYDROGEL_PACK":
            coef = 0.56  # Alzato per scaricare inventory più velocemente
            inv_skew = coef * math.copysign(math.sqrt(abs(pos)), pos)
        elif prod == "VELVETFRUIT_EXTRACT":
            coef = 0.1 # Più calmo per la frutta
            inv_skew = coef * math.copysign(math.sqrt(abs(pos)), pos)
        else:
            # Per le opzioni usiamo lo skew lineare classico ( anzi non lo usiamo proprio perché siamo pazziiii)
            inv_skew = (pos / max(1, limit)) * half_spread * 0

        adj_fv = fv - inv_skew + delta_skew

        bid_p = min(bid0 + 1, math.floor(adj_fv - half_spread))
        ask_p = max(ask0 - 1, math.ceil(adj_fv + half_spread))

        if bid_p >= ask_p: bid_p, ask_p = bid0, ask0

        bid_p, ask_p = max(bid_p, 1), max(ask_p, 2)
        bq, sq = min(clip, self._cap_buy(prod, pos)), min(clip, self._cap_sell(prod, pos))
        
        orders: list[Order] = []
        if bq > 0: orders.append(Order(prod, int(bid_p), bq))
        if sq > 0: orders.append(Order(prod, int(ask_p), -sq))
        return orders

    # ── delta-1 fair value ────────────────────────────────────

    def _delta1_fv(self, prod: str, od: OrderDepth, mem: dict) -> float:
        c_mid = self._clean_mid(od)
        default = 10_000.0 if prod == "HYDROGEL_PACK" else 5_250.0
        if c_mid is None or c_mid <= 0: return mem.get(f"{prod}_slow", default)

        tv, tpv = 0, 0.0
        for p, v in list(od.buy_orders.items()) + list(od.sell_orders.items()):
            v = abs(v)
            if v >= 2: tpv += p * v; tv += v
        vwap = tpv / tv if tv > 0 else c_mid

        if prod == "HYDROGEL_PACK":
            af, as_ = 0.30, 0.01
            wf, wv, ws, mag = 0.50, 0.30, 0.20, 0.05
        else:
            af, as_ = 0.40, 0.02
            wf, wv, ws, mag = 0.55, 0.30, 0.15, 0.05

        fast = af * c_mid + (1 - af) * mem.get(f"{prod}_fast", c_mid)
        slow = as_ * c_mid + (1 - as_) * mem.get(f"{prod}_slow", c_mid)
        mem[f"{prod}_fast"], mem[f"{prod}_slow"] = fast, slow

        fv = wf * fast + wv * vwap + ws * slow
        fv -= (c_mid - slow) * mag 
        return fv

    # ── main run ──────────────────────────────────────────────

    def run(self, state: TradingState):
        mem: dict = {}
        if state.traderData:
            try:
                loaded = json.loads(state.traderData)
                if isinstance(loaded, dict): mem = loaded
            except Exception: mem = {}

        result: dict[Symbol, list[Order]] = {}
        
        # 1. Spot Frutta
        vev_od = state.order_depths.get("VELVETFRUIT_EXTRACT", OrderDepth())
        S = self._clean_mid(vev_od) or mem.get("S", 5_250.0)
        mem["S"] = S

        # ── 2. TTE CALIBRATION ────────────────────────────────
        #
        # Invert BS price of VEV_5300 (primary) or VEV_5400 (fallback)
        # to recover the market-implied time-to-expiry in years.
        #
        # FIX 1: On first ever tick (T_ema not in mem), initialise
        #        T_ema = T_raw DIRECTLY.  No slow EMA cold-start.
        # FIX 2: calibrate_tte() already returns remaining TTE.
        #        Do NOT subtract elapsed time again.
        # FIX 3: α = 0.20 (faster EMA than 0.05 to track intraday decay).

        T_ema_prev = mem.get("T_ema", None)  # None on very first tick

        for calib_sym, calib_K in [("VEV_5300", 5300), ("VEV_5400", 5400)]:
            calib_od = state.order_depths.get(calib_sym, OrderDepth())
            calib_mid = self._clean_mid(calib_od)
            if calib_mid is not None and calib_mid > max(S - calib_K, 0.0) + 0.1:
                T_raw = calibrate_tte(calib_mid, S, float(calib_K), SIGMA)
                # First tick: jump directly to calibrated T (avoids the cold-start
                # bug where T_ema starts at 5/365 and needs ~100 ticks to converge)
                if T_ema_prev is None:
                    T_ema = T_raw
                else:
                    multi_raw = 0.2
                    T_ema = multi_raw * T_raw + (1 - multi_raw) * T_ema_prev
                break
        else:
            # No calibration anchor available: use previous or safe default
            T_ema = T_ema_prev if T_ema_prev is not None else 5.0 / 365.0

        mem["T_ema"] = T_ema


        # 3. HYDROGEL_PACK
        hgp_od = state.order_depths.get("HYDROGEL_PACK", OrderDepth())
        if hgp_od.buy_orders or hgp_od.sell_orders:
            hgp_pos = state.position.get("HYDROGEL_PACK", 0)
            hgp_fv = self._delta1_fv("HYDROGEL_PACK", hgp_od, mem)
            takes, pos2 = self._take("HYDROGEL_PACK", hgp_od, hgp_fv, hgp_pos, edge=1.8, max_lots=60)
            result["HYDROGEL_PACK"] = takes + self._quote("HYDROGEL_PACK", hgp_od, hgp_fv, pos2, half_spread=1.5, clip=40)

         # ── 4. OPTIONS ────────────────────────────────────────
        # FIX 3: Fair value = pure BS(S, K, T_ema, σ).
        # No market-EMA blend.  With a correctly calibrated T,
        # BS IS the market price — blending adds noise and causes
        # spurious takes when the market EMA lags after a move in S.

        net_delta = 0.0

        for sym, K in OPTION_STRIKES.items():
            od = state.order_depths.get(sym, OrderDepth())
            if not od.buy_orders and not od.sell_orders:
                continue

            pos = state.position.get(sym, 0)
            delta = bs_delta(S, float(K), T_ema, SIGMA)
            net_delta += pos * delta

            fv = bs_call(S, float(K), T_ema, SIGMA)  # ← pure theory

            half_sp, take_edge, clip, lots = OPTION_PARAMS[sym]

            takes, pos2 = self._take(sym, od, fv, pos, edge=take_edge, max_lots=lots)
            result[sym] = takes + self._quote(
                sym, od, fv, pos2, half_spread=half_sp, clip=clip
            )

        # 5. VELVETFRUIT_EXTRACT
        vev_pos = state.position.get("VELVETFRUIT_EXTRACT", 0)
        vev_fv = self._delta1_fv("VELVETFRUIT_EXTRACT", vev_od, mem)
        
        # Logica Hedging Opzioni (Delta) #no hedge per il momento, ma lasciato il calcolo del delta per future implementazioni
        # ... (net_delta calculation) (trascurato per ora)
        delta_skew = 0.0 # Placeholder

        takes, vev_p2 = self._take("VELVETFRUIT_EXTRACT", vev_od, vev_fv, vev_pos, edge=1.2, max_lots=40)
        
        # MODIFICA FRUTTA: Aumentato half_spread per catturare più profitto
        result["VELVETFRUIT_EXTRACT"] = takes + self._quote(
            "VELVETFRUIT_EXTRACT", vev_od, vev_fv, vev_p2, 
            half_spread=1.6, # Aumentato da 1.0
            clip=30, 
            delta_skew=delta_skew
        )

        trader_data = json.dumps(mem, separators=(",", ":"))
        return result, 0, trader_data