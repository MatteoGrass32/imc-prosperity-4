from datamodel import Order, OrderDepth, TradingState
from typing import Dict, List
from collections import deque
import numpy as np


class Trader:
    LIMIT = 10

    HARD_LONG  = {"OXYGEN_SHAKE_GARLIC"}
    HARD_SHORT = {"OXYGEN_SHAKE_EVENING_BREATH"}

    # (direction, window, t_entry, t_exit)
    CONFIGS = {
        "OXYGEN_SHAKE_CHOCOLATE":      (+1, 60, 0.08, 0.02),
        "OXYGEN_SHAKE_MORNING_BREATH": (-1, 60, 0.08, 0.03),
        "OXYGEN_SHAKE_MINT":           (-1, 60, 0.15, 0.03),
    }

    def __init__(self):
        all_products = self.HARD_LONG | self.HARD_SHORT | set(self.CONFIGS.keys())
        self.prices: Dict[str, deque] = {
            p: deque(maxlen=self.CONFIGS[p][1]) if p in self.CONFIGS else deque(maxlen=60)
            for p in all_products
        }
        self._xs:   Dict[str, np.ndarray] = {}
        self._dens: Dict[str, float]      = {}
        for p, (_, w, _, _) in self.CONFIGS.items():
            x             = np.arange(w)
            x_mean        = (w - 1) / 2
            self._xs[p]   = x
            self._dens[p] = float(np.sum((x - x_mean) ** 2))

    def mid(self, depth: OrderDepth):
        if not depth.buy_orders or not depth.sell_orders:
            return None
        return (max(depth.buy_orders) + min(depth.sell_orders)) / 2

    def _passive_order(self, symbol: str, depth: OrderDepth,
                       pos: int, target: int) -> List[Order]:
        best_bid = max(depth.buy_orders)
        best_ask = min(depth.sell_orders)
        orders   = []
        diff     = target - pos
        if diff > 0:
            orders.append(Order(symbol, min(best_bid + 1, best_ask - 1), diff))
        elif diff < 0:
            orders.append(Order(symbol, max(best_ask - 1, best_bid + 1), diff))
        return orders

    def _slope(self, p: str, hist: list) -> float:
        x      = self._xs[p]
        x_mean = (len(x) - 1) / 2
        y      = np.array(hist)
        return float(np.sum((x - x_mean) * (y - y.mean())) / self._dens[p])

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        result = {}

        for p in self.prices:
            depth = state.order_depths.get(p)
            if depth:
                m = self.mid(depth)
                if m:
                    self.prices[p].append(m)

        # ── Hard long ─────────────────────────────────────────────────────
        for p in self.HARD_LONG:
            depth = state.order_depths.get(p)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue
            pos = state.position.get(p, 0)
            orders = self._passive_order(p, depth, pos, +self.LIMIT)
            if orders:
                result[p] = orders

        # ── Hard short ────────────────────────────────────────────────────
        for p in self.HARD_SHORT:
            depth = state.order_depths.get(p)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue
            pos = state.position.get(p, 0)
            orders = self._passive_order(p, depth, pos, -self.LIMIT)
            if orders:
                result[p] = orders

        # ── Slope rolling con doppio threshold (isteresi) ─────────────────
        for p, (direction, w, t_entry, t_exit) in self.CONFIGS.items():
            depth = state.order_depths.get(p)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue

            pos  = state.position.get(p, 0)
            hist = list(self.prices[p])
            if len(hist) < w:
                target = 0  # esplicito flat durante warmup
                if target != pos:
                    result[p] = self._passive_order(p, depth, pos, target)
                continue

            s = self._slope(p, hist)

            entry = (direction > 0 and s >=  t_entry) or \
                    (direction < 0 and s <= -t_entry)
            keep  = (direction > 0 and s >=  t_exit)  or \
                    (direction < 0 and s <= -t_exit)

            if entry:
                target = self.LIMIT * direction
            elif not keep:
                target = 0
            else:
                target = pos  # isteresi: mantieni senza fare nuovi trade

            if target != pos:
                result[p] = self._passive_order(p, depth, pos, target)

        return result, 0, ""