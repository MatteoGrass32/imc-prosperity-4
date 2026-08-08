from datamodel import Order, OrderDepth, TradingState
from typing import Dict, List
from collections import deque
import numpy as np

class Trader:
    LIMIT = 10

    CONFIGS = {
        "UV_VISOR_AMBER":   (-1, 50, 0.02),
        "UV_VISOR_MAGENTA": (+1, 50, 0.03),
        "UV_VISOR_ORANGE":  (-1, 50, 0.07),  # ← 0.05→0.07: taglia fake-out Day 2
        "UV_VISOR_RED":     (+1, 50, 0.02),
        "UV_VISOR_YELLOW":  (-1, 50, 0.10),  # ← 0.06→0.10: Day 1 -10k → ~-1.8k
    }

    def __init__(self):
        all_products = set(self.CONFIGS.keys())
        self.prices: Dict[str, deque] = {p: deque(maxlen=50) for p in all_products}
        self.n      = 50
        self.x      = np.arange(self.n)
        self.x_mean = (self.n - 1) / 2
        self.den    = np.sum((self.x - self.x_mean) ** 2)

    def mid(self, depth: OrderDepth):
        if not depth.buy_orders or not depth.sell_orders:
            return None
        return (max(depth.buy_orders) + min(depth.sell_orders)) / 2

    def _passive_order(self, symbol: str, depth: OrderDepth,
                       pos: int, target: int) -> List[Order]:
        best_bid, best_ask = max(depth.buy_orders), min(depth.sell_orders)
        orders = []
        diff   = target - pos
        if diff > 0:
            orders.append(Order(symbol, min(best_bid + 1, best_ask - 1), diff))
        elif diff < 0:
            orders.append(Order(symbol, max(best_ask - 1, best_bid + 1), diff))
        return orders

    def _slope(self, hist: list) -> float:
        y   = np.array(hist)
        num = np.sum((self.x - self.x_mean) * (y - y.mean()))
        return num / self.den

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        result = {}

        for p, (dir_hist, _, threshold) in self.CONFIGS.items():
            depth = state.order_depths.get(p)
            if not depth:
                continue

            m = self.mid(depth)
            if m:
                self.prices[p].append(m)
            if len(self.prices[p]) < self.n:
                continue

            pos           = state.position.get(p, 0)
            current_slope = self._slope(list(self.prices[p]))

            confirms = (dir_hist > 0 and current_slope >=  threshold) or \
                       (dir_hist < 0 and current_slope <= -threshold)

            target = self.LIMIT * dir_hist if confirms else 0

            if target != pos:
                result[p] = self._passive_order(p, depth, pos, target)

        return result, 0, ""