import json, math
from typing import Any, Optional
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep=" ", end="\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict, conversions: int, trader_data: str) -> None:
        base_length = len(self.to_json(self.compress_state(state, ""), self.compress_orders(orders), conversions, "", ""))
        max_item_length = (self.max_log_length - base_length) // 3
        print(self.to_json(
            self.compress_state(state, self.truncate(state.traderData, max_item_length)),
            self.compress_orders(orders), conversions,
            self.truncate(trader_data, max_item_length),
            self.truncate(self.logs, max_item_length),
        ))
        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list:
        return [state.timestamp, trader_data, self.compress_listings(state.listings),
                self.compress_order_depths(state.order_depths), self.compress_trades(state.own_trades),
                self.compress_trades(state.market_trades), state.position, self.compress_observations(state.observations)]

    def compress_listings(self, listings: dict) -> list:
        return [[l.symbol, l.product, l.denomination] for l in listings.values()]

    def compress_order_depths(self, order_depths: dict) -> dict:
        return {s: [od.buy_orders, od.sell_orders] for s, od in order_depths.items()}

    def compress_trades(self, trades: dict) -> list:
        return [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
                for arr in trades.values() for t in arr]

    def compress_observations(self, observations: Observation) -> list:
        conv = {p: [o.bidPrice, o.askPrice, o.transportFees, o.exportTariff,
                    o.importTariff, o.sugarPrice, o.sunlightIndex]
                for p, o in observations.conversionObservations.items()}
        return [observations.plainValueObservations, conv]

    def compress_orders(self, orders: dict) -> list:
        return [[o.symbol, o.price, o.quantity] for arr in orders.values() for o in arr]

    def to_json(self, *args) -> str:
        return json.dumps(list(args), cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        lo, hi, out = 0, min(len(value), max_length), ""
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = value[:mid]
            if len(candidate) < len(value): candidate += "..."
            if len(json.dumps(candidate)) <= max_length:
                out = candidate; lo = mid + 1
            else:
                hi = mid - 1
        return out

logger = Logger()

# ==============================================================================
# PARAMETERS
# ==============================================================================
SIGMA = 0.27

POS_LIMITS = {
    "HYDROGEL_PACK": 200, "VELVETFRUIT_EXTRACT": 200,
    "VEV_4000": 300, "VEV_4500": 300, "VEV_5000": 300, "VEV_5100": 300,
    "VEV_5200": 300, "VEV_5300": 300, "VEV_5400": 300, "VEV_5500": 300,
    "VEV_6000": 300, "VEV_6500": 300,
}

# HYDROGEL: spread reale del LOB e' +-7.9 tick -> quotiamo +-7 per stare a top-of-book
HYDRO_TAKE_EDGE = 5.0
HYDRO_MAX_TAKE  = 200
HYDRO_HALF_SPR  = 7.0
HYDRO_CLIP      = 200
HYDRO_INV_SKEW  = 0.08

HYDRO_MOM_MAX   = 2.0
HYDRO_MOM_HL    = 300.0

# VELVETFRUIT_EXTRACT
VEV_INV_SKEW    = 0.25
VEV_TAKE_EDGE   = 3.0
VEV_TAKE_MAX    = 30
VEV_HALF_SPR    = 1.5
VEV_CLIP        = 30
STOP_LOSS_TICKS = 4.0

# Mark 49 rimosso (solo 3/20 accuracy), Mark 67 e Mark 22 confermati
VEV_SIGNALS  = {"Mark 67": (+1, 0.869), "Mark 22": (-1, 0.718)}
MOM_MAX_SKEW = 5.0
MOM_HALFLIFE = 600.0

VEV_EMA_FAST = 0.08
VEV_EMA_SLOW = 0.02
TREND_THRESH = 1.5

# SIGNAL BURST: 100-lot take immediato su segnale fresco Mark 67 / Mark 22
BURST_SIZE = 100

# OPTIONS
# VEV_4000/4500: pure passive MM (no take -- take causava -1 tick loss per fill)
ITM_PARAMS = {
    "VEV_4000": (9.0, 150),
    "VEV_4500": (7.0, 150),
}

# Tutti i cap a 300 -- Mark 01 e Mark 14 comprano ogni tick a prezzi fissi
SELL_ONLY = {
    "VEV_5000": (300, "intrinsic_minus", 4),
    "VEV_5100": (300, "intrinsic_plus",  1),
    "VEV_5200": (300, "intrinsic_plus",  1),
    "VEV_5300": (300, "fixed", 5),
    "VEV_5400": (300, "fixed", 5),
    "VEV_5500": (300, "fixed", 2),
    "VEV_6000": (100, "fixed", 1),
    "VEV_6500": (100, "fixed", 1),
}

# ==============================================================================
# BLACK-SCHOLES
# ==============================================================================
def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def bs_call(S: float, K: float, T: float, sigma: float = SIGMA) -> float:
    if T <= 0.0: return max(0.0, S - K)
    sigma = max(1e-9, sigma)
    d1 = (math.log(max(S, 1e-9) / K) + 0.5 * sigma**2 * T) / (sigma * math.sqrt(T))
    return max(0.0, S * _ncdf(d1) - K * _ncdf(d1 - sigma * math.sqrt(T)))

def bs_delta(S: float, K: float, T: float, sigma: float = SIGMA) -> float:
    if T <= 0.0: return 1.0 if S > K else 0.0
    sigma = max(1e-9, sigma)
    d1 = (math.log(max(S, 1e-9) / K) + 0.5 * sigma**2 * T) / (sigma * math.sqrt(T))
    return _ncdf(d1)

def calibrate_tte(C_mkt: float, S: float, K: float) -> float:
    if C_mkt <= max(0.0, S - K) + 0.05: return 0.3 / 365.0
    lo, hi = 0.1 / 365.0, 30.0 / 365.0
    for _ in range(54):
        mid = 0.5 * (lo + hi)
        if bs_call(S, K, mid) < C_mkt: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)

# ==============================================================================
# TRADER
# ==============================================================================
class Trader:

    def _cap(self, prod: str, pos: int) -> tuple[int, int]:
        lim = POS_LIMITS[prod]
        return max(0, lim - pos), max(0, lim + pos)

    def _mid(self, od: OrderDepth) -> Optional[float]:
        if not od.buy_orders or not od.sell_orders: return None
        return 0.5 * (max(od.buy_orders) + min(od.sell_orders))

    def _clean_mid(self, od: OrderDepth, min_vol: int = 2) -> Optional[float]:
        bids = sorted(od.buy_orders.items(), reverse=True)
        asks = sorted(od.sell_orders.items())
        if not bids or not asks: return self._mid(od)
        b = bids[0][0] if abs(bids[0][1]) >= min_vol or len(bids) == 1 else bids[1][0]
        a = asks[0][0] if abs(asks[0][1]) >= min_vol or len(asks) == 1 else asks[1][0]
        return 0.5 * (b + a)

    def _hydro_fv(self, od: OrderDepth, mem: dict) -> float:
        cm = self._clean_mid(od) or mem.get("h_slow", 10_000.0)
        items = {**od.buy_orders, **od.sell_orders}
        vols = {p: abs(v) for p, v in items.items() if abs(v) >= 2}
        vwap = (sum(p * v for p, v in vols.items()) / sum(vols.values())) if vols else cm
        f = 0.30 * cm + 0.70 * mem.get("h_fast", cm)
        s = 0.004 * cm + 0.996 * mem.get("h_slow", 10_000.0)
        mem["h_fast"], mem["h_slow"] = f, s
        return 0.50 * f + 0.30 * vwap + 0.20 * s

    def _hydro_mom(self, state: TradingState, mem: dict) -> float:
        for tr in state.market_trades.get("HYDROGEL_PACK", []):
            if tr.buyer == "Mark 38":    mem["hm_dir"], mem["hm_ts"] = +1, state.timestamp
            elif tr.seller == "Mark 38": mem["hm_dir"], mem["hm_ts"] = -1, state.timestamp
        if "hm_ts" not in mem: return 0.0
        decay = math.exp(-(state.timestamp - mem["hm_ts"]) * math.log(2) / HYDRO_MOM_HL)
        skew  = mem["hm_dir"] * HYDRO_MOM_MAX * decay
        if abs(skew) < HYDRO_MOM_MAX * 0.05: mem.pop("hm_ts", None); return 0.0
        return skew

    def _vev_fv(self, od: OrderDepth, mem: dict) -> float:
        mid = self._mid(od) or mem.get("vev_ema", 5_250.0)
        ema = 0.35 * mid + 0.65 * mem.get("vev_ema", mid)
        mem["vev_ema"] = ema
        return 0.6 * mid + 0.4 * ema

    def _vev_trend(self, S: float, mem: dict) -> int:
        f = VEV_EMA_FAST * S + (1 - VEV_EMA_FAST) * mem.get("vev_f", S)
        s = VEV_EMA_SLOW * S + (1 - VEV_EMA_SLOW) * mem.get("vev_s", S)
        mem["vev_f"], mem["vev_s"] = f, s
        if f - s > +TREND_THRESH: return +1
        if f - s < -TREND_THRESH: return -1
        return 0

    def _vev_mom(self, state: TradingState, mem: dict) -> float:
        for tr in state.market_trades.get("VELVETFRUIT_EXTRACT", []):
            for party in [tr.buyer, tr.seller]:
                if party in VEV_SIGNALS:
                    d, s = VEV_SIGNALS[party]
                    mem["m_dir"], mem["m_str"], mem["m_ts"] = d, s, state.timestamp
                    mem["m_new"] = True
        if "m_ts" not in mem: return 0.0
        decay = math.exp(-(state.timestamp - mem["m_ts"]) * math.log(2) / MOM_HALFLIFE)
        skew  = mem["m_dir"] * mem["m_str"] * MOM_MAX_SKEW * decay
        if abs(skew) < MOM_MAX_SKEW * 0.05:
            for k in ("m_ts", "m_dir", "m_str"): mem.pop(k, None)
            return 0.0
        return skew

    def _signal_burst(self, od: OrderDepth, pos: int, mem: dict) -> tuple[list, int]:
        if not mem.get("m_new"): return [], pos
        mem["m_new"] = False
        direction = mem.get("m_dir", 0)
        if direction == 0: return [], pos
        orders, cap = [], BURST_SIZE
        if direction > 0:
            cap = min(cap, max(0, POS_LIMITS["VELVETFRUIT_EXTRACT"] - pos))
            for ask in sorted(od.sell_orders):
                if cap <= 0: break
                qty = min(-od.sell_orders[ask], cap)
                if qty > 0: orders.append(Order("VELVETFRUIT_EXTRACT", ask, qty)); pos += qty; cap -= qty
        else:
            cap = min(cap, max(0, POS_LIMITS["VELVETFRUIT_EXTRACT"] + pos))
            for bid in sorted(od.buy_orders, reverse=True):
                if cap <= 0: break
                qty = min(od.buy_orders[bid], cap)
                if qty > 0: orders.append(Order("VELVETFRUIT_EXTRACT", bid, -qty)); pos -= qty; cap -= qty
        return orders, pos

    def _take(self, prod: str, od: OrderDepth, fv: float, pos: int,
              edge: float, max_lots: int = 9999, trend: int = 0) -> tuple[list, int]:
        orders = []
        buy_cap, sell_cap = self._cap(prod, pos)
        buy_cap, sell_cap = min(buy_cap, max_lots), min(sell_cap, max_lots)
        for ask in sorted(od.sell_orders):
            if buy_cap <= 0: break
            vol = -od.sell_orders[ask]
            if ask <= fv - edge: qty = min(vol, buy_cap)
            elif abs(ask - fv) < 1.0 and pos < 0 and trend == 0: qty = min(vol, buy_cap, abs(pos))
            else: continue
            orders.append(Order(prod, ask, qty)); pos += qty; buy_cap -= qty
        for bid in sorted(od.buy_orders, reverse=True):
            if sell_cap <= 0: break
            vol = od.buy_orders[bid]
            if bid >= fv + edge: qty = min(vol, sell_cap)
            elif abs(bid - fv) < 1.0 and pos > 0 and trend == 0: qty = min(vol, sell_cap, abs(pos))
            else: continue
            orders.append(Order(prod, bid, -qty)); pos -= qty; sell_cap -= qty
        return orders, pos

    def _quote(self, prod: str, od: OrderDepth, fv: float, pos: int,
               half_spr: float, clip: int,
               extra_skew: float = 0.0, allow_bid=True, allow_ask=True) -> list:
        if not od.buy_orders or not od.sell_orders: return []
        best_bid, best_ask = max(od.buy_orders), min(od.sell_orders)
        if prod == "HYDROGEL_PACK":
            inv = HYDRO_INV_SKEW * math.copysign(math.sqrt(abs(pos)), pos)
        elif prod == "VELVETFRUIT_EXTRACT":
            inv = VEV_INV_SKEW * math.copysign(math.sqrt(abs(pos)), pos)
        else:
            inv = 0.0
        adj   = fv - inv + extra_skew
        bid_p = min(best_bid + 1, math.floor(adj - half_spr))
        ask_p = max(best_ask - 1, math.ceil(adj + half_spr))
        if bid_p >= ask_p: bid_p, ask_p = best_bid, best_ask
        bid_p, ask_p = max(bid_p, 1), max(ask_p, bid_p + 1)
        orders = []
        buy_cap, sell_cap = self._cap(prod, pos)
        if allow_bid and (q := min(clip, buy_cap))  > 0: orders.append(Order(prod, int(bid_p),  q))
        if allow_ask and (q := min(clip, sell_cap)) > 0: orders.append(Order(prod, int(ask_p), -q))
        return orders

    def _opt_floor(self, sym: str, S: float) -> int:
        _, mode, param = SELL_ONLY[sym]
        intr = max(0.0, S - int(sym.split("_")[1]))
        if mode == "intrinsic_plus":  return max(1, int(intr) + int(param))
        if mode == "intrinsic_minus": return max(1, int(intr) - int(param))
        return int(param)

    def _sell_option(self, sym: str, S: float, od: OrderDepth, pos: int) -> list:
        max_short = SELL_ONLY[sym][0]
        floor_p   = self._opt_floor(sym, S)
        _, sell_cap = self._cap(sym, pos)
        sell_cap  = min(sell_cap, max_short + pos)
        if sell_cap <= 0: return []
        orders = []
        for bid in sorted(od.buy_orders, reverse=True):
            if bid < floor_p or sell_cap <= 0: break
            qty = min(od.buy_orders[bid], sell_cap)
            orders.append(Order(sym, bid, -qty)); sell_cap -= qty
        if sell_cap > 0: orders.append(Order(sym, floor_p, -sell_cap))
        return orders

    def _delta_hedge(self, S: float, T: float, positions: dict,
                     vev_pos: int, vev_od: OrderDepth) -> list:
        all_opts  = list(ITM_PARAMS.keys()) + list(SELL_ONLY.keys())
        net_delta = sum(bs_delta(S, float(sym.split("_")[1]), T) * positions.get(sym, 0)
                        for sym in all_opts)
        diff = -int(round(net_delta)) - vev_pos
        if diff == 0: return []
        orders = []
        buy_cap, sell_cap = self._cap("VELVETFRUIT_EXTRACT", vev_pos)
        if diff > 0:
            cap = min(diff, buy_cap)
            for ask in sorted(vev_od.sell_orders):
                if cap <= 0: break
                qty = min(-vev_od.sell_orders[ask], cap)
                orders.append(Order("VELVETFRUIT_EXTRACT", ask, qty)); cap -= qty
        else:
            cap = min(-diff, sell_cap)
            for bid in sorted(vev_od.buy_orders, reverse=True):
                if cap <= 0: break
                qty = min(vev_od.buy_orders[bid], cap)
                orders.append(Order("VELVETFRUIT_EXTRACT", bid, -qty)); cap -= qty
        return orders

    def _vev_stop(self, od: OrderDepth, pos: int, mem: dict, fv: float) -> list:
        if abs(pos) < 20: return []
        if (fv - mem.get("vev_entry", fv)) * (-1 if pos > 0 else 1) <= STOP_LOSS_TICKS: return []
        if pos > 0:
            ask = min(od.sell_orders) if od.sell_orders else None
            return [Order("VELVETFRUIT_EXTRACT", ask, -min(pos, 30))] if ask else []
        bid = max(od.buy_orders) if od.buy_orders else None
        return [Order("VELVETFRUIT_EXTRACT", bid, min(abs(pos), 30))] if bid else []

    # ==========================================================================
    # MAIN RUN
    # ==========================================================================
    def run(self, state: TradingState):
        try: mem = json.loads(state.traderData) if state.traderData else {}
        except: mem = {}
        result: dict[Symbol, list[Order]] = {}

        # 1. VEV spot + TTE calibration (T init = 2.7 giorni reali)
        vev_od = state.order_depths.get("VELVETFRUIT_EXTRACT", OrderDepth())
        S = self._mid(vev_od) or mem.get("S", 5_250.0)
        mem["S"] = S
        T_prev = mem.get("T_ema")
        T = T_prev or 2.7 / 252.0
        for cs, cK in [("VEV_5300", 5300), ("VEV_5400", 5400)]:
            cm = self._mid(state.order_depths.get(cs, OrderDepth()))
            if cm and cm > max(S - cK, 0.0) + 0.1:
                T_raw = calibrate_tte(cm, S, cK)
                T = T_raw if T_prev is None else 0.2 * T_raw + 0.8 * T_prev
                break
        mem["T_ema"] = T

        # 2. VEV trend + momentum
        trend = self._vev_trend(S, mem)
        skew  = self._vev_mom(state, mem)

        # 3. HYDROGEL_PACK
        hydro_od  = state.order_depths.get("HYDROGEL_PACK", OrderDepth())
        hydro_pos = state.position.get("HYDROGEL_PACK", 0)
        if hydro_od.buy_orders or hydro_od.sell_orders:
            fv  = self._hydro_fv(hydro_od, mem)
            mom = self._hydro_mom(state, mem)
            tk, p2 = self._take("HYDROGEL_PACK", hydro_od, fv + mom, hydro_pos,
                                 edge=HYDRO_TAKE_EDGE, max_lots=HYDRO_MAX_TAKE)
            result["HYDROGEL_PACK"] = tk + self._quote(
                "HYDROGEL_PACK", hydro_od, fv, p2,
                half_spr=HYDRO_HALF_SPR, clip=HYDRO_CLIP, extra_skew=mom,
            )

        # 4. Deep ITM options -- SOLO quote passive, niente take
        for sym, (hs, clip) in ITM_PARAMS.items():
            od  = state.order_depths.get(sym, OrderDepth())
            if not od.buy_orders and not od.sell_orders: continue
            pos = state.position.get(sym, 0)
            fv  = bs_call(S, float(sym.split("_")[1]), T)
            result[sym] = self._quote(sym, od, fv, pos, half_spr=hs, clip=clip,
                                       allow_bid=(trend >= 0), allow_ask=(trend <= 0))

        # 5. Sell-only options -- theta collection, nessun filtro trend
        for sym in SELL_ONLY:
            od  = state.order_depths.get(sym, OrderDepth())
            if not od.buy_orders and not od.sell_orders: continue
            pos = state.position.get(sym, 0)
            if pos <= -SELL_ONLY[sym][0]: continue
            orders = self._sell_option(sym, S, od, pos)
            if orders: result[sym] = orders

        # 6. VELVETFRUIT_EXTRACT
        vev_pos = state.position.get("VELVETFRUIT_EXTRACT", 0)

        # (a) delta hedge -- sempre prioritario
        dh = self._delta_hedge(S, T, state.position, vev_pos, vev_od)
        if dh:
            result["VELVETFRUIT_EXTRACT"] = dh
            vev_pos += sum(o.quantity for o in dh)

        fv  = self._vev_fv(vev_od, mem)
        adj = fv + skew
        if abs(vev_pos) < 5 or "vev_entry" not in mem: mem["vev_entry"] = adj

        # (b) signal burst -- 100 lot immediati su segnale fresco
        burst, vev_pos = self._signal_burst(vev_od, vev_pos, mem)
        if burst:
            result["VELVETFRUIT_EXTRACT"] = result.get("VELVETFRUIT_EXTRACT", []) + burst

        # (c) stop-loss
        stop = self._vev_stop(vev_od, vev_pos, mem, adj)
        if stop:
            result["VELVETFRUIT_EXTRACT"] = stop
        else:
            # (d) directional takes + passive quotes
            takes, p2 = self._take("VELVETFRUIT_EXTRACT", vev_od, adj, vev_pos,
                                    edge=VEV_TAKE_EDGE, max_lots=VEV_TAKE_MAX)
            if trend == -1: takes = [o for o in takes if o.quantity < 0]; p2 = vev_pos + sum(o.quantity for o in takes)
            if trend == +1: takes = [o for o in takes if o.quantity > 0]; p2 = vev_pos + sum(o.quantity for o in takes)
            result["VELVETFRUIT_EXTRACT"] = takes + self._quote(
                "VELVETFRUIT_EXTRACT", vev_od, adj, p2,
                half_spr=VEV_HALF_SPR, clip=VEV_CLIP,
                allow_bid=(trend >= 0), allow_ask=(trend <= 0),
            )

        trader_data = json.dumps(mem, separators=(",", ":"))
        logger.flush(state, result, 0, trader_data)
        return result, 0, trader_data