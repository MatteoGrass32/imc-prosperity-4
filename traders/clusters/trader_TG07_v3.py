import json
import math
from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict


class Trader:
    """
    TG07 HYBRID FINAL v2:
    - SPACE_GRAY + VOID_BLUE: OLS su MICROCHIP
    - ASTRO_BLACK + ECLIPSE_CHARCOAL + GRAPHITE_MIST: EMA adaptive
    Fix: basket_mean calcolato su tutti e 5 i TRANSLATOR (come nell'EMA originale)
    """

    def __init__(self):
        # --- OLS group ---
        self.ols_models = {
            "TRANSLATOR_SPACE_GRAY": (15096.53, -0.2793, +0.1305, +0.0542, -0.1333, -0.2910, 105.19),
            "TRANSLATOR_VOID_BLUE":  (17267.87, -0.0033, -0.3355, -0.3905, -0.1370, +0.1691,  90.82),
        }
        self.MICROCHIPS = [
            "MICROCHIP_CIRCLE", "MICROCHIP_OVAL",
            "MICROCHIP_RECTANGLE", "MICROCHIP_SQUARE", "MICROCHIP_TRIANGLE"
        ]
        self.ols_position_limit = 10
        self.ols_spread_margins = {
            "TRANSLATOR_SPACE_GRAY": 2,
            "TRANSLATOR_VOID_BLUE":  3,
        }

        # --- EMA group ---
        self.ema_trade = {
            "TRANSLATOR_ASTRO_BLACK",
            "TRANSLATOR_ECLIPSE_CHARCOAL",
            "TRANSLATOR_GRAPHITE_MIST",
        }
        # Tutti e 5 servono per basket_mean (come nell'originale)
        self.all_translators = [
            "TRANSLATOR_ASTRO_BLACK",
            "TRANSLATOR_ECLIPSE_CHARCOAL",
            "TRANSLATOR_GRAPHITE_MIST",
            "TRANSLATOR_SPACE_GRAY",
            "TRANSLATOR_VOID_BLUE",
        ]
        self.ema_limits = {p: 10 for p in self.ema_trade}
        self.alpha   = 0.01
        self.entry_z = 1.5
        self.exit_z  = 0.2

    # ── Helpers ────────────────────────────────────────────────────

    def get_mid(self, product, state: TradingState):
        depth = state.order_depths.get(product)
        if not depth or not depth.buy_orders or not depth.sell_orders:
            return None
        return (max(depth.buy_orders) + min(depth.sell_orders)) / 2.0

    # ── OLS strategy ───────────────────────────────────────────────

    def _run_ols(self, state: TradingState, result: dict, mc_mids: dict):
        for product, coeffs in self.ols_models.items():
            depth = state.order_depths.get(product)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue

            alpha, betas, std_err = coeffs[0], coeffs[1:6], coeffs[6]
            best_bid  = max(depth.buy_orders)
            best_ask  = min(depth.sell_orders)
            mid_price = (best_bid + best_ask) / 2.0
            pos       = state.position.get(product, 0)
            margin    = self.ols_spread_margins[product]
            pos_lim   = self.ols_position_limit

            fair_value = alpha + sum(b * mc_mids[mc] for b, mc in zip(betas, self.MICROCHIPS))
            z_score    = (mid_price - fair_value) / std_err

            target = int(-z_score * 4)
            target = max(-pos_lim, min(pos_lim, target))
            diff   = target - pos
            orders = []

            if z_score < -1.0 and diff > 0:
                orders.append(Order(product, best_ask, diff))
            elif z_score > 1.0 and diff < 0:
                orders.append(Order(product, best_bid, diff))
            else:
                my_bid = int(round(fair_value - margin - pos * 0.5))
                my_ask = int(round(fair_value + margin - pos * 0.5))
                if pos_lim - pos > 0:
                    orders.append(Order(product, min(my_bid, best_bid + 1),  pos_lim - pos))
                if -pos_lim - pos < 0:
                    orders.append(Order(product, max(my_ask, best_ask - 1), -pos_lim - pos))

            if orders:
                result[product] = orders

    # ── EMA strategy ───────────────────────────────────────────────

    def _run_ema(self, state: TradingState, result: dict, data: dict):
        ema_state = data.get("ema", {})
        m2_state  = data.get("m2", {})

        # basket_mean su TUTTI e 5 i translator (fix critico)
        all_mids = {}
        for p in self.all_translators:
            m = self.get_mid(p, state)
            if m is not None:
                all_mids[p] = m

        if len(all_mids) < 3:
            return

        basket_mean = sum(all_mids.values()) / len(all_mids)

        signals, stds = {}, {}
        for p in self.all_translators:
            if p not in all_mids:
                continue
            rel_price = all_mids[p] - basket_mean
            curr_ema  = ema_state.get(p, rel_price)
            new_ema   = self.alpha * rel_price + (1 - self.alpha) * curr_ema
            ema_state[p] = new_ema

            diff    = rel_price - new_ema
            curr_m2 = m2_state.get(p, 70.0 ** 2)
            new_m2  = self.alpha * (diff ** 2) + (1 - self.alpha) * curr_m2
            m2_state[p] = new_m2

            stds[p]    = math.sqrt(new_m2)
            signals[p] = diff

        # Esegui ordini solo sui 3 prodotti EMA
        for p in self.ema_trade:
            if p not in signals or p not in stds:
                continue
            z     = signals[p] / stds[p] if stds[p] > 0 else 0
            pos   = state.position.get(p, 0)
            limit = self.ema_limits[p]
            depth = state.order_depths.get(p)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue

            best_ask = min(depth.sell_orders)
            best_bid = max(depth.buy_orders)
            orders   = []

            if z < -self.entry_z:
                qty = limit - pos
                if qty > 0:
                    orders.append(Order(p, min(best_bid + 1, best_ask - 1), qty))
            elif z > self.entry_z:
                qty = -limit - pos
                if qty < 0:
                    orders.append(Order(p, max(best_ask - 1, best_bid + 1), qty))
            elif abs(z) < self.exit_z:
                if pos > 0:
                    orders.append(Order(p, max(best_ask - 1, best_bid + 1), -pos))
                elif pos < 0:
                    orders.append(Order(p, min(best_bid + 1, best_ask - 1), -pos))

            if orders:
                result[p] = orders

        data["ema"] = ema_state
        data["m2"]  = m2_state

    # ── Main ───────────────────────────────────────────────────────

    def run(self, state: TradingState):
        result = {}
        data   = {}
        if state.traderData:
            try:
                data = json.loads(state.traderData)
            except:
                data = {}

        # OLS block
        mc_mids = {mc: self.get_mid(mc, state) for mc in self.MICROCHIPS}
        if None not in mc_mids.values():
            self._run_ols(state, result, mc_mids)

        # EMA block
        self._run_ema(state, result, data)

        return result, 0, json.dumps(data)