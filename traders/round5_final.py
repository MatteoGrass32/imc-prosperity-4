from datamodel import Order, TradingState, OrderDepth
import collections
from typing import List, Dict
from collections import deque
import numpy as np
import json
import math


class Trader:
    def __init__(self):
        # ============================================================
        # STRATEGIA 1 — GALAXY SOUNDS
        # ============================================================
        self.gs_products = [
            "GALAXY_SOUNDS_BLACK_HOLES",
            "GALAXY_SOUNDS_DARK_MATTER",
            "GALAXY_SOUNDS_PLANETARY_RINGS",
            "GALAXY_SOUNDS_SOLAR_FLAMES",
            "GALAXY_SOUNDS_SOLAR_WINDS",
        ]
        self.gs_configs = {
            "GALAXY_SOUNDS_BLACK_HOLES": ("PEBBLES_S", 20559.43, -1.0179, 446.23),
            "GALAXY_SOUNDS_DARK_MATTER": ("UV_VISOR_YELLOW", 6144.54, 0.3725, 211.76),
            "GALAXY_SOUNDS_PLANETARY_RINGS": ("GALAXY_SOUNDS_DARK_MATTER", 8025.67, 0.2608, 297.89),
            "GALAXY_SOUNDS_SOLAR_WINDS": ("PANEL_1X4", 15490.14, -0.5376, 302.85),
            "GALAXY_SOUNDS_SOLAR_FLAMES": ("GALAXY_SOUNDS_SOLAR_WINDS", 14003.29, -0.2789, 424.10),
        }
        self.gs_pos_limit = 10

        # ============================================================
        # STRATEGIA 2 — SLEEP PODS
        # ============================================================
        self.sp_limit = 10
        self.sp_skew_thresh = 9
        self.sp_trend_window = 50
        self.sp_products = [
            "SLEEP_POD_COTTON",
            "SLEEP_POD_NYLON",
            "SLEEP_POD_POLYESTER",
            "SLEEP_POD_LAMB_WOOL",
            "SLEEP_POD_SUEDE",
        ]
        self.sp_trend_filter = {"SLEEP_POD_LAMB_WOOL", "SLEEP_POD_COTTON", "SLEEP_POD_SUEDE"}
        self.sp_price_history: Dict[str, deque] = {
            p: deque(maxlen=self.sp_trend_window) for p in self.sp_products
        }

        # ============================================================
        # STRATEGIA 3 — MICROCHIPS
        # ============================================================
        self.mc_limit = 10
        self.mc_hard_short = {"MICROCHIP_OVAL"}
        self.mc_configs = {
            "MICROCHIP_SQUARE":    (+1, 80, 15, 5, 4.5, 40),
            "MICROCHIP_CIRCLE":    (+1, 100, 10, 10, 8.0, None),
            "MICROCHIP_TRIANGLE":  (-1, 100, 10, 10, 5.0, None),
            "MICROCHIP_RECTANGLE": (-1, 100, 10, 10, 5.0, 50),
        }
        mc_all_products = self.mc_hard_short | set(self.mc_configs.keys())
        mc_max_w = max(cfg[1] for cfg in self.mc_configs.values())
        self.mc_prices: Dict[str, deque] = {
            p: deque(maxlen=mc_max_w) for p in mc_all_products
        }

        # ============================================================
        # STRATEGIA 4 — PEBBLES
        # ============================================================
        self.peb_limit = 10
        self.peb_window = 200
        self.peb_z_entry = 1.5
        self.peb_z_exit = 0
        self.peb_trend_w = 50
        self.peb_leader = "PEBBLES_XL"
        self.peb_basket = ["PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L"]
        self.peb_all = self.peb_basket + [self.peb_leader]
        self.peb_mm_only = {"PEBBLES_S", "PEBBLES_L"}
        self.peb_trend_filter = {"PEBBLES_M", "PEBBLES_XS"}
        self.peb_prices: Dict[str, deque] = {
            p: deque(maxlen=max(self.peb_window, self.peb_trend_w)) for p in self.peb_all
        }
        self.peb_spread_hist: deque = deque(maxlen=self.peb_window)

        # ============================================================
        # STRATEGIA 5 — ROBOT
        # ============================================================
        self.rob_models = {
            "ROBOT_VACUUMING": (8883.57,   0.2096, -0.1053, 227.85),
            "ROBOT_MOPPING":   (10467.18, -0.2101,  0.1729, 480.70),
            "ROBOT_DISHES":    (12052.99, -0.2806,  0.0192, 310.83),
            "ROBOT_LAUNDRY":   (6119.02,   0.3793,  0.0442, 306.61),
            "ROBOT_IRONING":   (6538.64,   0.3789, -0.0689, 352.55),
        }
        self.rob_position_limit = 10
        self.rob_spread_margins = {p: 2 for p in self.rob_models}
        self.rob_laundry_limit = 5
        self.rob_spread_margins["ROBOT_LAUNDRY"] = 4
        self.rob_laundry_z_threshold = 1.5

        # ============================================================
        # STRATEGIA 6 — UV VISORS
        # ============================================================
        self.uv_limit = 10
        self.uv_configs = {
            "UV_VISOR_AMBER":   (-1, 50, 0.02),
            "UV_VISOR_MAGENTA": (+1, 50, 0.03),
            "UV_VISOR_ORANGE":  (-1, 50, 0.07),
            "UV_VISOR_RED":     (+1, 50, 0.02),
            "UV_VISOR_YELLOW":  (-1, 50, 0.10),
        }
        self.uv_n = 50
        self.uv_prices: Dict[str, deque] = {
            p: deque(maxlen=50) for p in self.uv_configs.keys()
        }
        self.uv_x = np.arange(self.uv_n)
        self.uv_x_mean = (self.uv_n - 1) / 2
        self.uv_den = np.sum((self.uv_x - self.uv_x_mean) ** 2)

        # ============================================================
        # STRATEGIA 7 — TRANSLATORS
        # ============================================================
        self.trans_ols_models = {
            "TRANSLATOR_SPACE_GRAY": (15096.53, -0.2793, 0.1305, 0.0542, -0.1333, -0.2910, 105.19),
            "TRANSLATOR_VOID_BLUE":  (17267.87, -0.0033, -0.3355, -0.3905, -0.1370, 0.1691, 90.82),
        }
        self.trans_microchips = [
            "MICROCHIP_CIRCLE", "MICROCHIP_OVAL",
            "MICROCHIP_RECTANGLE", "MICROCHIP_SQUARE", "MICROCHIP_TRIANGLE"
        ]
        self.trans_ols_limit = 10
        self.trans_ols_spread_margins = {
            "TRANSLATOR_SPACE_GRAY": 2,
            "TRANSLATOR_VOID_BLUE": 3,
        }
        self.trans_ema_trade = {
            "TRANSLATOR_ASTRO_BLACK",
            "TRANSLATOR_ECLIPSE_CHARCOAL",
            "TRANSLATOR_GRAPHITE_MIST",
        }
        self.trans_all = [
            "TRANSLATOR_ASTRO_BLACK",
            "TRANSLATOR_ECLIPSE_CHARCOAL",
            "TRANSLATOR_GRAPHITE_MIST",
            "TRANSLATOR_SPACE_GRAY",
            "TRANSLATOR_VOID_BLUE",
        ]
        self.trans_ema_limits = {p: 10 for p in self.trans_ema_trade}
        self.trans_alpha = 0.01
        self.trans_entry_z = 1.5
        self.trans_exit_z = 0.2

        # ============================================================
        # STRATEGIA 8 — PANELS
        # ============================================================
        self.pnl_alpha_fast_standard = 0.02
        self.pnl_alpha_fast_aggressive = 0.04
        self.pnl_alpha_slow = 0.003
        self.pnl_products = ["PANEL_1X4", "PANEL_2X2", "PANEL_2X4", "PANEL_4X4"]

        # ============================================================
        # STRATEGIA 9 — OXYGEN SHAKES
        # ============================================================
        self.oxy_limit = 10
        self.oxy_hard_long = {"OXYGEN_SHAKE_GARLIC"}
        self.oxy_hard_short = {"OXYGEN_SHAKE_EVENING_BREATH"}
        self.oxy_configs = {
            "OXYGEN_SHAKE_CHOCOLATE":      (+1, 60, 0.08, 0.02),
            "OXYGEN_SHAKE_MORNING_BREATH": (-1, 60, 0.08, 0.03),
            "OXYGEN_SHAKE_MINT":           (-1, 60, 0.15, 0.03),
        }
        oxy_all_products = self.oxy_hard_long | self.oxy_hard_short | set(self.oxy_configs.keys())
        self.oxy_prices: Dict[str, deque] = {
            p: deque(maxlen=self.oxy_configs[p][1]) if p in self.oxy_configs else deque(maxlen=60)
            for p in oxy_all_products
        }
        self.oxy_xs: Dict[str, np.ndarray] = {}
        self.oxy_dens: Dict[str, float] = {}
        for p, (_, w, _, _) in self.oxy_configs.items():
            x = np.arange(w)
            x_mean = (w - 1) / 2
            self.oxy_xs[p] = x
            self.oxy_dens[p] = float(np.sum((x - x_mean) ** 2))

        # ============================================================
        # STRATEGIA 10 — SNACKPACKS
        # ============================================================
        self.snp_limit = 10
        self.snp_products = [
            'SNACKPACK_CHOCOLATE',
            'SNACKPACK_PISTACHIO',
            'SNACKPACK_RASPBERRY',
            'SNACKPACK_STRAWBERRY',
            'SNACKPACK_VANILLA'
        ]
        self.snp_avg_prices = {
            'SNACKPACK_CHOCOLATE': 10000.0,
            'SNACKPACK_PISTACHIO': 9500.0,
            'SNACKPACK_RASPBERRY': 10000.0,
            'SNACKPACK_STRAWBERRY': 10500.0,
            'SNACKPACK_VANILLA': 10000.0
        }
        snp_total_avg = sum(self.snp_avg_prices.values())
        self.snp_weights = {p: self.snp_avg_prices[p] / snp_total_avg for p in self.snp_products}
        self.snp_alpha = 0.05
        self.snp_edge = 1.0
        self.snp_risk_factor = 3.0

    def get_mid_price(self, order_depth: OrderDepth):
        if order_depth is None or not order_depth.buy_orders or not order_depth.sell_orders:
            return None
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        return (best_bid + best_ask) / 2

    def _get_mid(self, product: str, state: TradingState):
        return self.get_mid_price(state.order_depths.get(product))

    # ============================================================
    # STRATEGIA 1 — GALAXY
    # ============================================================
    def _run_galaxy(self, state: TradingState, result: Dict[str, List[Order]]):
        mids = {}
        for p, depth in state.order_depths.items():
            m = self.get_mid_price(depth)
            if m is not None:
                mids[p] = m

        for target in self.gs_products:
            if target not in self.gs_configs or target not in state.order_depths:
                continue

            oracle, alpha, beta, std = self.gs_configs[target]
            oracle_mid = mids.get(oracle)
            target_mid = mids.get(target)
            if oracle_mid is None or target_mid is None:
                continue

            fair_target = alpha + beta * oracle_mid
            current_pos = state.position.get(target, 0)
            target_depth = state.order_depths[target]
            buy_orders = collections.OrderedDict(sorted(target_depth.buy_orders.items(), reverse=True))
            sell_orders = collections.OrderedDict(sorted(target_depth.sell_orders.items()))
            z_score = (target_mid - fair_target) / std

            target_pos = current_pos
            if z_score < -1.0:
                target_pos = self.gs_pos_limit
            elif z_score > 1.0:
                target_pos = -self.gs_pos_limit
            elif abs(z_score) < 0.2:
                target_pos = 0

            diff = target_pos - current_pos
            orders: List[Order] = []

            if diff > 0:
                for price, vol in sell_orders.items():
                    if price <= fair_target:
                        buy_qty = min(diff, -vol)
                        if buy_qty > 0:
                            orders.append(Order(target, price, buy_qty))
                            diff -= buy_qty
                    if diff <= 0:
                        break
                if diff > 0:
                    orders.append(Order(target, max(target_depth.buy_orders.keys()) + 1, diff))

            elif diff < 0:
                need = -diff
                for price, vol in buy_orders.items():
                    if price >= fair_target:
                        sell_qty = min(need, vol)
                        if sell_qty > 0:
                            orders.append(Order(target, price, -sell_qty))
                            need -= sell_qty
                    if need <= 0:
                        break
                if need > 0:
                    orders.append(Order(target, min(target_depth.sell_orders.keys()) - 1, -need))

            if orders:
                result[target] = orders

    # ============================================================
    # STRATEGIA 2 — SLEEP PODS
    # ============================================================
    def _run_sleep_pods(self, state: TradingState, result: Dict[str, List[Order]]):
        for symbol in self.sp_products:
            depth = state.order_depths.get(symbol)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue

            best_bid = max(depth.buy_orders)
            best_ask = min(depth.sell_orders)
            mid = (best_bid + best_ask) / 2
            pos = state.position.get(symbol, 0)
            self.sp_price_history[symbol].append(mid)

            buy_price = best_bid + 1
            sell_price = best_ask - 1

            if pos >= self.sp_skew_thresh:
                sell_price -= 1
            elif pos <= -self.sp_skew_thresh:
                buy_price += 1

            if buy_price >= sell_price:
                buy_price = best_bid
                sell_price = best_ask

            buy_qty = max(0, self.sp_limit - pos)
            sell_qty = max(0, self.sp_limit + pos)

            if symbol in self.sp_trend_filter:
                hist = self.sp_price_history[symbol]
                if len(hist) >= self.sp_trend_window:
                    trend = hist[-1] - hist[0]
                    if trend > 0:
                        buy_qty = 0
                        if pos > 0:
                            sell_qty = pos
                    elif trend < 0:
                        sell_qty = 0
                        if pos < 0:
                            buy_qty = -pos

            orders: List[Order] = []
            if buy_qty > 0:
                orders.append(Order(symbol, buy_price, int(buy_qty)))
            if sell_qty > 0:
                orders.append(Order(symbol, sell_price, -int(sell_qty)))

            if orders:
                result[symbol] = orders

    # ============================================================
    # STRATEGIA 3 — MICROCHIPS
    # ============================================================
    def _mc_passive_order(self, symbol: str, depth: OrderDepth, pos: int, target: int) -> List[Order]:
        best_bid = max(depth.buy_orders)
        best_ask = min(depth.sell_orders)
        diff = target - pos
        orders: List[Order] = []
        if diff > 0:
            orders.append(Order(symbol, best_bid + 1, diff))
        elif diff < 0:
            orders.append(Order(symbol, best_ask - 1, diff))
        return orders

    def _run_microchips(self, state: TradingState, result: Dict[str, List[Order]]):
        for p in self.mc_prices:
            depth = state.order_depths.get(p)
            if depth:
                m = self.get_mid_price(depth)
                if m is not None:
                    self.mc_prices[p].append(m)

        for p in self.mc_hard_short:
            depth = state.order_depths.get(p)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue
            pos = state.position.get(p, 0)
            orders = self._mc_passive_order(p, depth, pos, -self.mc_limit)
            if orders:
                result[p] = orders

        for p, (direction, trend_w, s_start, s_end, threshold, short_w) in self.mc_configs.items():
            depth = state.order_depths.get(p)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue
            pos = state.position.get(p, 0)
            hist = list(self.mc_prices[p])
            if len(hist) < trend_w:
                continue

            start_val = np.mean(hist[:s_start])
            end_val = np.mean(hist[-s_end:])
            long_trend = end_val - start_val

            long_confirms = (
                (direction > 0 and long_trend > threshold) or
                (direction < 0 and long_trend < -threshold)
            )

            target = 0
            if long_confirms:
                if short_w is not None:
                    short_hist = hist[-short_w:]
                    short_start = np.mean(short_hist[:5])
                    short_end = np.mean(short_hist[-5:])
                    short_trend = short_end - short_start
                    short_confirms = (
                        (direction > 0 and short_trend > 0) or
                        (direction < 0 and short_trend < 0)
                    )
                    target = self.mc_limit * direction if short_confirms else 0
                else:
                    target = self.mc_limit * direction

            if pos != target:
                orders = self._mc_passive_order(p, depth, pos, target)
                if orders:
                    result[p] = orders

    # ============================================================
    # STRATEGIA 4 — PEBBLES
    # ============================================================
    def _run_pebbles(self, state: TradingState, result: Dict[str, List[Order]]):
        mids = {}
        for p in self.peb_all:
            depth = state.order_depths.get(p)
            if depth:
                m = self.get_mid_price(depth)
                if m is not None:
                    self.peb_prices[p].append(m)
                    mids[p] = m

        z = 0.0
        if len(mids) == len(self.peb_all):
            basket_avg = np.mean([mids[p] for p in self.peb_basket])
            spread = mids[self.peb_leader] - basket_avg
            self.peb_spread_hist.append(spread)
            if len(self.peb_spread_hist) >= self.peb_window:
                arr = np.array(self.peb_spread_hist)
                std = arr.std()
                if std > 0:
                    z = (spread - arr.mean()) / std

        for p in self.peb_all:
            depth = state.order_depths.get(p)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue

            best_bid = max(depth.buy_orders)
            best_ask = min(depth.sell_orders)
            pos = state.position.get(p, 0)
            orders: List[Order] = []

            if p == self.peb_leader:
                if z > self.peb_z_entry and pos > -self.peb_limit:
                    qty = self.peb_limit + pos
                    if qty > 0:
                        orders.append(Order(p, best_bid, -qty))
                elif z < -self.peb_z_entry and pos < self.peb_limit:
                    qty = self.peb_limit - pos
                    if qty > 0:
                        orders.append(Order(p, best_ask, qty))
                elif abs(z) < self.peb_z_exit and pos != 0:
                    if pos > 0:
                        orders.append(Order(p, best_bid, -pos))
                    else:
                        orders.append(Order(p, best_ask, -pos))
                else:
                    buy_qty = max(0, self.peb_limit - pos)
                    sell_qty = max(0, self.peb_limit + pos)
                    if buy_qty > 0:
                        orders.append(Order(p, best_bid + 1, int(buy_qty)))
                    if sell_qty > 0:
                        orders.append(Order(p, best_ask - 1, -int(sell_qty)))

            elif p in self.peb_mm_only:
                buy_qty = max(0, self.peb_limit - pos)
                sell_qty = max(0, self.peb_limit + pos)
                if buy_qty > 0:
                    orders.append(Order(p, best_bid + 1, int(buy_qty)))
                if sell_qty > 0:
                    orders.append(Order(p, best_ask - 1, -int(sell_qty)))

            elif p in self.peb_trend_filter:
                hist = self.peb_prices[p]
                buy_qty = max(0, self.peb_limit - pos)
                sell_qty = max(0, self.peb_limit + pos)

                if len(hist) >= self.peb_trend_w:
                    trend = hist[-1] - hist[-self.peb_trend_w]
                    if trend > 0:
                        buy_qty = 0
                        sell_qty = min(self.peb_limit, pos + 5) if pos > 0 else self.peb_limit + pos
                    elif trend < 0:
                        sell_qty = 0
                        if pos < 0:
                            buy_qty = -pos

                if buy_qty > 0:
                    orders.append(Order(p, best_bid + 1, int(buy_qty)))
                if sell_qty > 0:
                    orders.append(Order(p, best_ask - 1, -int(sell_qty)))

            if orders:
                result[p] = orders

    # ============================================================
    # STRATEGIA 5 — ROBOT
    # ============================================================
    def _run_robot(self, state: TradingState, result: Dict[str, List[Order]]):
        oval_mid = self.get_mid_price(state.order_depths.get("MICROCHIP_OVAL"))
        square_mid = self.get_mid_price(state.order_depths.get("MICROCHIP_SQUARE"))
        if oval_mid is None or square_mid is None:
            return

        for product, (alpha, b_oval, b_square, std_err) in self.rob_models.items():
            if product not in state.order_depths:
                continue

            depth = state.order_depths[product]
            if not depth.buy_orders or not depth.sell_orders:
                continue

            best_bid = max(depth.buy_orders)
            best_ask = min(depth.sell_orders)
            mid_price = (best_bid + best_ask) / 2.0
            pos = state.position.get(product, 0)

            fair_value = alpha + b_oval * oval_mid + b_square * square_mid
            z_score = (mid_price - fair_value) / std_err

            is_laundry = (product == "ROBOT_LAUNDRY")
            pos_lim = self.rob_laundry_limit if is_laundry else self.rob_position_limit
            z_threshold = self.rob_laundry_z_threshold if is_laundry else 1.0

            target = int(-z_score * 4)
            target = max(-pos_lim, min(pos_lim, target))
            diff = target - pos
            orders: List[Order] = []

            if z_score < -z_threshold and diff > 0:
                orders.append(Order(product, best_ask, diff))
            elif z_score > z_threshold and diff < 0:
                orders.append(Order(product, best_bid, diff))
            else:
                margin = self.rob_spread_margins[product]
                my_bid = int(round(fair_value - margin - pos * 0.5))
                my_ask = int(round(fair_value + margin - pos * 0.5))
                buy_lim = pos_lim - pos
                sell_lim = -pos_lim - pos
                if buy_lim > 0:
                    orders.append(Order(product, min(my_bid, best_bid + 1), buy_lim))
                if sell_lim < 0:
                    orders.append(Order(product, max(my_ask, best_ask - 1), sell_lim))

            if orders:
                result[product] = orders

    # ============================================================
    # STRATEGIA 6 — UV VISORS
    # ============================================================
    def _uv_passive_order(self, symbol: str, depth: OrderDepth, pos: int, target: int) -> List[Order]:
        best_bid = max(depth.buy_orders)
        best_ask = min(depth.sell_orders)
        diff = target - pos
        orders: List[Order] = []
        if diff > 0:
            orders.append(Order(symbol, min(best_bid + 1, best_ask - 1), diff))
        elif diff < 0:
            orders.append(Order(symbol, max(best_ask - 1, best_bid + 1), diff))
        return orders

    def _uv_slope(self, hist: list) -> float:
        y = np.array(hist)
        num = np.sum((self.uv_x - self.uv_x_mean) * (y - y.mean()))
        return num / self.uv_den

    def _run_uv_visors(self, state: TradingState, result: Dict[str, List[Order]]):
        for p, (dir_hist, _, threshold) in self.uv_configs.items():
            depth = state.order_depths.get(p)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue

            m = self.get_mid_price(depth)
            if m is not None:
                self.uv_prices[p].append(m)

            if len(self.uv_prices[p]) < self.uv_n:
                continue

            pos = state.position.get(p, 0)
            current_slope = self._uv_slope(list(self.uv_prices[p]))
            confirms = (
                (dir_hist > 0 and current_slope >= threshold) or
                (dir_hist < 0 and current_slope <= -threshold)
            )
            target = self.uv_limit * dir_hist if confirms else 0

            if target != pos:
                orders = self._uv_passive_order(p, depth, pos, target)
                if orders:
                    result[p] = orders

    # ============================================================
    # STRATEGIA 7 — TRANSLATORS
    # ============================================================
    def _run_translators(self, state: TradingState, result: Dict[str, List[Order]], root_data: dict):
        trans_data = root_data.get("translators", {})
        ema_state = trans_data.get("ema", {})
        m2_state = trans_data.get("m2", {})

        mc_mids = {mc: self._get_mid(mc, state) for mc in self.trans_microchips}
        if None not in mc_mids.values():
            for product, coeffs in self.trans_ols_models.items():
                depth = state.order_depths.get(product)
                if not depth or not depth.buy_orders or not depth.sell_orders:
                    continue

                alpha, betas, std_err = coeffs[0], coeffs[1:6], coeffs[6]
                best_bid = max(depth.buy_orders)
                best_ask = min(depth.sell_orders)
                mid_price = (best_bid + best_ask) / 2.0
                pos = state.position.get(product, 0)
                margin = self.trans_ols_spread_margins[product]
                pos_lim = self.trans_ols_limit

                fair_value = alpha + sum(b * mc_mids[mc] for b, mc in zip(betas, self.trans_microchips))
                z_score = (mid_price - fair_value) / std_err

                target = int(-z_score * 4)
                target = max(-pos_lim, min(pos_lim, target))
                diff = target - pos
                orders = []

                if z_score < -1.0 and diff > 0:
                    orders.append(Order(product, best_ask, diff))
                elif z_score > 1.0 and diff < 0:
                    orders.append(Order(product, best_bid, diff))
                else:
                    my_bid = int(round(fair_value - margin - pos * 0.5))
                    my_ask = int(round(fair_value + margin - pos * 0.5))
                    if pos_lim - pos > 0:
                        orders.append(Order(product, min(my_bid, best_bid + 1), pos_lim - pos))
                    if -pos_lim - pos < 0:
                        orders.append(Order(product, max(my_ask, best_ask - 1), -pos_lim - pos))

                if orders:
                    result[product] = orders

        all_mids = {}
        for p in self.trans_all:
            m = self._get_mid(p, state)
            if m is not None:
                all_mids[p] = m

        if len(all_mids) >= 3:
            basket_mean = sum(all_mids.values()) / len(all_mids)
            signals, stds = {}, {}

            for p in self.trans_all:
                if p not in all_mids:
                    continue
                rel_price = all_mids[p] - basket_mean
                curr_ema = ema_state.get(p, rel_price)
                new_ema = self.trans_alpha * rel_price + (1 - self.trans_alpha) * curr_ema
                ema_state[p] = new_ema

                diff = rel_price - new_ema
                curr_m2 = m2_state.get(p, 70.0 ** 2)
                new_m2 = self.trans_alpha * (diff ** 2) + (1 - self.trans_alpha) * curr_m2
                m2_state[p] = new_m2

                stds[p] = math.sqrt(new_m2)
                signals[p] = diff

            for p in self.trans_ema_trade:
                if p not in signals or p not in stds:
                    continue
                z = signals[p] / stds[p] if stds[p] > 0 else 0
                pos = state.position.get(p, 0)
                limit = self.trans_ema_limits[p]
                depth = state.order_depths.get(p)
                if not depth or not depth.buy_orders or not depth.sell_orders:
                    continue

                best_ask = min(depth.sell_orders)
                best_bid = max(depth.buy_orders)
                orders = []

                if z < -self.trans_entry_z:
                    qty = limit - pos
                    if qty > 0:
                        orders.append(Order(p, min(best_bid + 1, best_ask - 1), qty))
                elif z > self.trans_entry_z:
                    qty = -limit - pos
                    if qty < 0:
                        orders.append(Order(p, max(best_ask - 1, best_bid + 1), qty))
                elif abs(z) < self.trans_exit_z:
                    if pos > 0:
                        orders.append(Order(p, max(best_ask - 1, best_bid + 1), -pos))
                    elif pos < 0:
                        orders.append(Order(p, min(best_bid + 1, best_ask - 1), -pos))

                if orders:
                    result[p] = orders

        trans_data["ema"] = ema_state
        trans_data["m2"] = m2_state
        root_data["translators"] = trans_data

    # ============================================================
    # STRATEGIA 8 — PANELS
    # ============================================================
    def _run_panels(self, state: TradingState, result: Dict[str, List[Order]], root_data: dict):
        panel_data = root_data.get("panels", {})
        ema_fast = panel_data.get("ema_fast", {})
        ema_slow = panel_data.get("ema_slow", {})

        for p in self.pnl_products:
            mid = self._get_mid(p, state)
            if mid is None:
                continue

            af = self.pnl_alpha_fast_aggressive if p == "PANEL_1X4" else self.pnl_alpha_fast_standard

            ef = ema_fast.get(p, mid)
            es = ema_slow.get(p, mid)

            ef = af * mid + (1 - af) * ef
            es = self.pnl_alpha_slow * mid + (1 - self.pnl_alpha_slow) * es

            ema_fast[p] = ef
            ema_slow[p] = es

            depth = state.order_depths.get(p)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue

            best_bid = max(depth.buy_orders)
            best_ask = min(depth.sell_orders)
            pos = state.position.get(p, 0)
            orders: List[Order] = []

            if p == "PANEL_2X4":
                target = 10
            elif p == "PANEL_2X2":
                target = -10
            elif p == "PANEL_1X4":
                diff = ef - es
                spread = abs(mid) if abs(mid) > 1 else 1
                signal = diff / spread
                target = int(signal * 10 * 300)
                target = max(-10, min(10, target))
            else:
                diff = ef - es
                spread = abs(mid) if abs(mid) > 1 else 1
                signal = diff / spread
                target = int(signal * 5 * 200)
                target = max(-5, min(5, target))

            diff_pos = target - pos
            if diff_pos > 0:
                orders.append(Order(p, best_ask, diff_pos))
            elif diff_pos < 0:
                orders.append(Order(p, best_bid, diff_pos))

            if orders:
                result[p] = orders

        panel_data["ema_fast"] = ema_fast
        panel_data["ema_slow"] = ema_slow
        root_data["panels"] = panel_data

    # ============================================================
    # STRATEGIA 9 — OXYGEN SHAKES
    # ============================================================
    def _oxy_passive_order(self, symbol: str, depth: OrderDepth, pos: int, target: int) -> List[Order]:
        best_bid = max(depth.buy_orders)
        best_ask = min(depth.sell_orders)
        orders: List[Order] = []
        diff = target - pos
        if diff > 0:
            orders.append(Order(symbol, min(best_bid + 1, best_ask - 1), diff))
        elif diff < 0:
            orders.append(Order(symbol, max(best_ask - 1, best_bid + 1), diff))
        return orders

    def _oxy_slope(self, p: str, hist: list) -> float:
        x = self.oxy_xs[p]
        x_mean = (len(x) - 1) / 2
        y = np.array(hist)
        return float(np.sum((x - x_mean) * (y - y.mean())) / self.oxy_dens[p])

    def _run_oxygen_shakes(self, state: TradingState, result: Dict[str, List[Order]]):
        for p in self.oxy_prices:
            depth = state.order_depths.get(p)
            if depth:
                m = self.get_mid_price(depth)
                if m is not None:
                    self.oxy_prices[p].append(m)

        for p in self.oxy_hard_long:
            depth = state.order_depths.get(p)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue
            pos = state.position.get(p, 0)
            orders = self._oxy_passive_order(p, depth, pos, +self.oxy_limit)
            if orders:
                result[p] = orders

        for p in self.oxy_hard_short:
            depth = state.order_depths.get(p)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue
            pos = state.position.get(p, 0)
            orders = self._oxy_passive_order(p, depth, pos, -self.oxy_limit)
            if orders:
                result[p] = orders

        for p, (direction, w, t_entry, t_exit) in self.oxy_configs.items():
            depth = state.order_depths.get(p)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue

            pos = state.position.get(p, 0)
            hist = list(self.oxy_prices[p])
            if len(hist) < w:
                target = 0
                if target != pos:
                    result[p] = self._oxy_passive_order(p, depth, pos, target)
                continue

            s = self._oxy_slope(p, hist)

            entry = (direction > 0 and s >= t_entry) or \
                    (direction < 0 and s <= -t_entry)
            keep = (direction > 0 and s >= t_exit) or \
                   (direction < 0 and s <= -t_exit)

            if entry:
                target = self.oxy_limit * direction
            elif not keep:
                target = 0
            else:
                target = pos

            if target != pos:
                result[p] = self._oxy_passive_order(p, depth, pos, target)

    # ============================================================
    # STRATEGIA 10 — SNACKPACKS
    # ============================================================
    def _run_snackpacks(self, state: TradingState, result: Dict[str, List[Order]], root_data: dict):
        snack_data = root_data.get("snackpacks", {})
        ema_weights = snack_data.get("ema_weights", self.snp_weights.copy())

        current_prices = {}
        for p in self.snp_products:
            mid = self.get_mid_price(state.order_depths.get(p))
            if mid is not None:
                current_prices[p] = mid

        if not current_prices:
            snack_data["ema_weights"] = ema_weights
            root_data["snackpacks"] = snack_data
            return

        cluster_sum = sum(current_prices.values())
        current_rel_weights = {p: current_prices[p] / cluster_sum for p in current_prices}

        for product in self.snp_products:
            order_depth = state.order_depths.get(product)
            if not order_depth or not order_depth.buy_orders or not order_depth.sell_orders:
                continue

            pos = state.position.get(product, 0)
            orders: List[Order] = []
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())

            if product in current_prices:
                if product in ema_weights:
                    ema_weights[product] = self.snp_alpha * current_rel_weights[product] + (1 - self.snp_alpha) * ema_weights[product]
                else:
                    ema_weights[product] = current_rel_weights[product]

            if product in ["SNACKPACK_VANILLA", "SNACKPACK_STRAWBERRY"]:
                if product in current_prices:
                    weight_dev = current_rel_weights[product] - ema_weights[product]
                    target_pos = -weight_dev * 5000.0
                    target_pos = max(min(target_pos, self.snp_limit), -self.snp_limit)

                    fair_val = current_prices[product] + (target_pos - pos) * self.snp_risk_factor

                    bid_price = min(int(math.floor(fair_val - self.snp_edge)), best_bid + 1)
                    ask_price = max(int(math.ceil(fair_val + self.snp_edge)), best_ask - 1)

                    if pos < self.snp_limit:
                        orders.append(Order(product, bid_price, self.snp_limit - pos))
                    if pos > -self.snp_limit:
                        orders.append(Order(product, ask_price, -self.snp_limit - pos))

            elif product == "SNACKPACK_RASPBERRY":
                skew = 0
                if pos >= 8:
                    skew = -1
                elif pos <= -8:
                    skew = +1

                buy_price = int(best_bid + 1 + skew)
                sell_price = int(best_ask - 1 + skew)

                if buy_price >= best_ask:
                    buy_price = best_ask - 1
                if sell_price <= best_bid:
                    sell_price = best_bid + 1

                buy_qty = max(0, self.snp_limit - pos)
                sell_qty = max(0, self.snp_limit + pos)

                if best_ask - best_bid < 3:
                    if pos >= 0:
                        buy_qty = 0
                    if pos <= 0:
                        sell_qty = 0

                if buy_qty > 0:
                    orders.append(Order(product, buy_price, int(buy_qty)))
                if sell_qty > 0:
                    orders.append(Order(product, sell_price, int(-sell_qty)))

            else:
                buy_price = int(best_bid + 1)
                sell_price = int(best_ask - 1)

                if pos >= 9:
                    sell_price -= 1
                elif pos <= -9:
                    buy_price += 1

                if buy_price >= best_ask:
                    buy_price = best_ask - 1
                if sell_price <= best_bid:
                    sell_price = best_bid + 1

                buy_qty = max(0, self.snp_limit - pos)
                sell_qty = max(0, self.snp_limit + pos)

                if buy_qty > 0:
                    orders.append(Order(product, buy_price, int(buy_qty)))
                if sell_qty > 0:
                    orders.append(Order(product, sell_price, int(-sell_qty)))

            if orders:
                result[product] = orders

        snack_data["ema_weights"] = ema_weights
        root_data["snackpacks"] = snack_data

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}
        root_data = {}

        if state.traderData:
            try:
                root_data = json.loads(state.traderData)
            except:
                root_data = {}

        self._run_galaxy(state, result)
        self._run_sleep_pods(state, result)
        self._run_microchips(state, result)
        self._run_pebbles(state, result)
        self._run_robot(state, result)
        self._run_uv_visors(state, result)
        self._run_translators(state, result, root_data)
        self._run_panels(state, result, root_data)
        self._run_oxygen_shakes(state, result)
        self._run_snackpacks(state, result, root_data)

        return result, 0, json.dumps(root_data)