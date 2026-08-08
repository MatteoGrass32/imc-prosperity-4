import json
from datamodel import TradingState, Order
from typing import List

class Trader:
    def __init__(self):
        # Parametri differenziati basati sui log empirici
        self.alpha_fast_standard = 0.02
        self.alpha_fast_aggressivo = 0.04
        self.alpha_slow = 0.003

        # PANEL_1X2 escluso dal trading
        self.all_products = ["PANEL_1X4", "PANEL_2X2", "PANEL_2X4", "PANEL_4X4"]

    def get_mid(self, product, state: TradingState):
        depth = state.order_depths.get(product)
        if not depth or not depth.buy_orders or not depth.sell_orders:
            return None
        return (max(depth.buy_orders) + min(depth.sell_orders)) / 2.0

    def run(self, state: TradingState):
        result = {}
        data   = {}
        if state.traderData:
            try:
                data = json.loads(state.traderData)
            except:
                pass

        ema_fast = data.get("ema_fast", {})
        ema_slow = data.get("ema_slow", {})

        for p in self.all_products:
            mid = self.get_mid(p, state)
            if mid is None:
                continue

            # Applica l'alpha aggressivo SOLO al PANEL_1X4 (il nostro mostro di volatilità)
            af = self.alpha_fast_aggressivo if p == "PANEL_1X4" else self.alpha_fast_standard

            ef = ema_fast.get(p, mid)
            es = ema_slow.get(p, mid)
            
            ef = af * mid + (1 - af) * ef
            es = self.alpha_slow * mid + (1 - self.alpha_slow) * es
            
            ema_fast[p] = ef
            ema_slow[p] = es

            depth = state.order_depths.get(p)
            if not depth or not depth.buy_orders or not depth.sell_orders:
                continue

            best_bid = max(depth.buy_orders)
            best_ask = min(depth.sell_orders)
            pos = state.position.get(p, 0)
            orders: List[Order] = []

            # --- LOGICA IBRIDA DEFINITIVA ---

            if p == "PANEL_2X4":
                # Trend rialzista fortissimo: Long fisso senza limiti (10)
                target = 10
                
            elif p == "PANEL_2X2":
                # Trend ribassista costante: Short fisso senza limiti (-10)
                target = -10
                
            elif p == "PANEL_1X4":
                # Volatilità e inversione al Day3: EMA aggressiva a taglia piena (10)
                diff = ef - es
                spread = abs(mid) if abs(mid) > 1 else 1
                signal = (diff / spread)
                target = int(signal * 10 * 300)
                target = max(-10, min(10, target))
                
            else:
                # PANEL_4X4: EMA standard smussata e protetta (size 5)
                diff = ef - es
                spread = abs(mid) if abs(mid) > 1 else 1
                signal = (diff / spread)
                target = int(signal * 5 * 200)
                target = max(-5, min(5, target))

            # --- PIAZZAMENTO ORDINI ---

            diff_pos = target - pos
            if diff_pos > 0:
                orders.append(Order(p, best_ask, diff_pos))
            elif diff_pos < 0:
                orders.append(Order(p, best_bid, diff_pos))

            if orders:
                result[p] = orders

        data["ema_fast"] = ema_fast
        data["ema_slow"] = ema_slow

        return result, 0, json.dumps(data)