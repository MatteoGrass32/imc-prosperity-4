from datamodel import Order, TradingState, OrderDepth
from typing import Dict, List


class Trader:
    """
    Statistical Arbitrage su ROBOT usando MICROCHIP come oracle.
    FairValue(robot) = alpha + b_oval * OVAL + b_square * SQUARE  [OLS offline]
    """

    def __init__(self):
        self.models = {
            "ROBOT_VACUUMING": (8883.57,   0.2096, -0.1053, 227.85),
            "ROBOT_MOPPING":   (10467.18, -0.2101,  0.1729, 480.70),
            "ROBOT_DISHES":    (12052.99, -0.2806,  0.0192, 310.83),
            "ROBOT_LAUNDRY":   (6119.02,   0.3793,  0.0442, 306.61),
            "ROBOT_IRONING":   (6538.64,   0.3789, -0.0689, 352.55),
        }
        self.position_limit = 10
        self.spread_margins = {p: 2 for p in self.models}

        # ── Protezioni specifiche per LAUNDRY ─────────────────────────────
        # 1. Position limit ridotto: max ±5 invece di ±10
        self.laundry_limit  = 5
        # 2. Spread più largo: ±4 invece di ±2 → meno fill, più selettivo
        self.spread_margins["ROBOT_LAUNDRY"] = 4
        # 3. Z threshold più alta: entra solo su segnali forti (|z| > 1.5)
        self.laundry_z_threshold = 1.5

    def get_mid(self, product, state: TradingState):
        if product not in state.order_depths:
            return None
        depth = state.order_depths[product]
        if not depth.buy_orders or not depth.sell_orders:
            return None
        return (max(depth.buy_orders) + min(depth.sell_orders)) / 2.0

    def run(self, state: TradingState):
        result = {}

        oval_mid   = self.get_mid("MICROCHIP_OVAL",   state)
        square_mid = self.get_mid("MICROCHIP_SQUARE", state)
        if oval_mid is None or square_mid is None:
            return result, 0, ""

        for product, (alpha, b_oval, b_square, std_err) in self.models.items():
            if product not in state.order_depths:
                continue
            depth = state.order_depths[product]
            if not depth.buy_orders or not depth.sell_orders:
                continue

            best_bid  = max(depth.buy_orders)
            best_ask  = min(depth.sell_orders)
            mid_price = (best_bid + best_ask) / 2.0
            pos       = state.position.get(product, 0)

            fair_value = alpha + b_oval * oval_mid + b_square * square_mid
            z_score    = (mid_price - fair_value) / std_err

            # Parametri specifici per LAUNDRY, standard per gli altri
            is_laundry  = (product == "ROBOT_LAUNDRY")
            pos_lim     = self.laundry_limit if is_laundry else self.position_limit
            z_threshold = self.laundry_z_threshold if is_laundry else 1.0

            target = int(-z_score * 4)
            target = max(-pos_lim, min(pos_lim, target))

            orders: List[Order] = []
            diff = target - pos

            if z_score < -z_threshold and diff > 0:
                orders.append(Order(product, best_ask, diff))
            elif z_score > z_threshold and diff < 0:
                orders.append(Order(product, best_bid, diff))
            else:
                margin   = self.spread_margins[product]
                my_bid   = int(round(fair_value - margin - pos * 0.5))
                my_ask   = int(round(fair_value + margin - pos * 0.5))
                buy_lim  =  pos_lim - pos
                sell_lim = -pos_lim - pos
                if buy_lim > 0:
                    orders.append(Order(product, min(my_bid, best_bid + 1),  buy_lim))
                if sell_lim < 0:
                    orders.append(Order(product, max(my_ask, best_ask - 1), sell_lim))

            if orders:
                result[product] = orders

        return result, 0, ""