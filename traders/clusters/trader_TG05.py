from datamodel import Order, TradingState, OrderDepth
from typing import Dict, List


class Trader:
    """
    Statistical Arbitrage su ROBOT 
    Logica: FairValue(robot) = alpha + b_oval * OVAL + b_square * SQUARE  [OLS offline]
    Se il prezzo reale diverge dal FV → mean reversion sul residuo.
    """

    def __init__(self):
        # Coefficienti OLS stimati offline sui 3 giorni storici
        # Formato: (alpha, b_OVAL, b_SQUARE, std_err_residuo)
        self.models = {
            "ROBOT_VACUUMING": (8883.57,   0.2096, -0.1053, 227.85),
            "ROBOT_MOPPING":   (10467.18, -0.2101,  0.1729, 480.70),
            "ROBOT_DISHES":    (12052.99, -0.2806,  0.0192, 310.83),
            "ROBOT_LAUNDRY":   (6119.02,   0.3793,  0.0442, 306.61),
            "ROBOT_IRONING":   (6538.64,   0.3789, -0.0689, 352.55),
        }
        self.position_limit = 10
        self.spread_margins = {p: 2 for p in self.models}

    def get_mid(self, product, state: TradingState):
        if product not in state.order_depths:
            return None
        depth = state.order_depths[product]
        if not depth.buy_orders or not depth.sell_orders:
            return None
        return (max(depth.buy_orders) + min(depth.sell_orders)) / 2.0

    def run(self, state: TradingState):
        result = {}

        # I MICROCHIP sono i driver del fair value — senza di loro non operiamo
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

            # Fair value teorico dai microchip
            fair_value = alpha + b_oval * oval_mid + b_square * square_mid

            # z > 0: robot sopravvalutato → vendi | z < 0: sottovalutato → compra
            z_score = (mid_price - fair_value) / std_err

            # Target proporzionale allo z-score, pieno a |z| = 2.5
            target = int(-z_score * 4)
            target = max(-self.position_limit, min(self.position_limit, target))

            orders: List[Order] = []
            diff = target - pos

            if z_score < -1 and diff > 0:
                # Sottovalutato con segnale forte: market order aggressivo
                orders.append(Order(product, best_ask, diff))
            elif z_score > 1 and diff < 0:
                # Sopravvalutato con segnale forte: market order aggressivo
                orders.append(Order(product, best_bid, diff))
            else:
                # Segnale debole: market making passivo attorno al fair value
                # pos * 0.5 skewa le quote per facilitare il ribilanciamento
                margin   = self.spread_margins[product]
                my_bid   = int(round(fair_value - margin - pos * 0.5))
                my_ask   = int(round(fair_value + margin - pos * 0.5))
                buy_lim  =  self.position_limit - pos
                sell_lim = -self.position_limit - pos
                if buy_lim > 0:
                    orders.append(Order(product, min(my_bid, best_bid + 1),  buy_lim))
                if sell_lim < 0:
                    orders.append(Order(product, max(my_ask, best_ask - 1), sell_lim))

            if orders:
                result[product] = orders

        return result, 0, ""