import json
import math
from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict

class Trader:
    def __init__(self):
        self.limit = 10
        self.products = [
            'SNACKPACK_CHOCOLATE',
            'SNACKPACK_PISTACHIO',
            'SNACKPACK_RASPBERRY',
            'SNACKPACK_STRAWBERRY',
            'SNACKPACK_VANILLA'
        ]
        
        # --- PARAMETRI LOGICA 1 (EMA / Pesi) per Vanilla & Strawberry ---
        self.avg_prices = {
            'SNACKPACK_CHOCOLATE': 10000.0,
            'SNACKPACK_PISTACHIO': 9500.0,
            'SNACKPACK_RASPBERRY': 10000.0,
            'SNACKPACK_STRAWBERRY': 10500.0,
            'SNACKPACK_VANILLA': 10000.0
        }
        total_avg = sum(self.avg_prices.values())
        self.weights = {p: self.avg_prices[p] / total_avg for p in self.products}
        
        self.alpha = 0.05
        self.edge = 1.0
        self.risk_factor = 3.0

    def get_mid_price(self, order_depth: OrderDepth):
        if not order_depth or not order_depth.sell_orders or not order_depth.buy_orders:
            return None
        best_ask = min(order_depth.sell_orders.keys())
        best_bid = max(order_depth.buy_orders.keys())
        return (best_ask + best_bid) / 2.0

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        result = {}
        conversions = 0
        
        # ─── 1. GESTIONE STATO EMA (TraderData) ─────────────────────────────
        if state.traderData:
            try:
                data = json.loads(state.traderData)
            except:
                data = {"ema_weights": self.weights.copy()}
        else:
            data = {"ema_weights": self.weights.copy()}

        # ─── 2. CALCOLO PREZZI CLUSTER ──────────────────────────────────────
        current_prices = {}
        for p in self.products:
            mid = self.get_mid_price(state.order_depths.get(p))
            if mid is not None:
                current_prices[p] = mid
        
        if not current_prices:
            return result, conversions, json.dumps(data)

        cluster_sum = sum(current_prices.values())
        current_rel_weights = {p: current_prices[p] / cluster_sum for p in current_prices}

        # ─── 3. LOGICA DI TRADING IBRIDA A 3 VIE ────────────────────────────
        for product in self.products:
            order_depth = state.order_depths.get(product)
            if not order_depth or not order_depth.buy_orders or not order_depth.sell_orders:
                continue
                
            pos = state.position.get(product, 0)
            orders: List[Order] = []
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())

            # Aggiornamento universale dei pesi EMA
            if product in current_prices:
                if product in data["ema_weights"]:
                    data["ema_weights"][product] = self.alpha * current_rel_weights[product] + (1 - self.alpha) * data["ema_weights"][product]
                else:
                    data["ema_weights"][product] = current_rel_weights[product]

            # ---------------------------------------------------------------
            # GRUPPO A: VANILLA & STRAWBERRY (Logica Pesi Relativi Esatta)
            # ---------------------------------------------------------------
            if product in ["SNACKPACK_VANILLA", "SNACKPACK_STRAWBERRY"]:
                if product in current_prices:
                    weight_dev = current_rel_weights[product] - data["ema_weights"][product]
                    target_pos = -weight_dev * 5000.0
                    target_pos = max(min(target_pos, self.limit), -self.limit)
                    
                    fair_val = current_prices[product] + (target_pos - pos) * self.risk_factor
                    
                    bid_price = min(int(math.floor(fair_val - self.edge)), best_bid + 1)
                    ask_price = max(int(math.ceil(fair_val + self.edge)), best_ask - 1)
                    
                    if pos < self.limit:
                        orders.append(Order(product, bid_price, self.limit - pos))
                    if pos > -self.limit:
                        orders.append(Order(product, ask_price, -self.limit - pos))

            # ---------------------------------------------------------------
            # GRUPPO B: RASPBERRY (Logica Simmetrica + Salvavita Dispettoso)
            # ---------------------------------------------------------------
            elif product == "SNACKPACK_RASPBERRY":
                skew = 0
                if pos >= 8:
                    skew = -1
                elif pos <= -8:
                    skew = +1

                buy_price  = int(best_bid + 1 + skew)
                sell_price = int(best_ask - 1 + skew)
                
                # Sanity check
                if buy_price >= best_ask: buy_price = best_ask - 1
                if sell_price <= best_bid: sell_price = best_bid + 1

                buy_qty = max(0, self.limit - pos)
                sell_qty = max(0, self.limit + pos) 

                # --- LA PROTEZIONE ---
                # Se lo spread collassa (es. scende sotto i 3 tick dai normali ~17),
                # il mercato sta subendo un "toxic flow". Modalità "Reduce-Only".
                if best_ask - best_bid < 3:
                    if pos >= 0: buy_qty = 0   # Niente nuovi acquisti se flat/lunghi
                    if pos <= 0: sell_qty = 0  # Niente nuove vendite se flat/corti

                if buy_qty > 0:
                    orders.append(Order(product, buy_price, int(buy_qty)))
                if sell_qty > 0:
                    orders.append(Order(product, sell_price, int(-sell_qty)))

            # ---------------------------------------------------------------
            # GRUPPO C: CHOCOLATE & PISTACHIO (Logica Asimmetrica "Tightrope")
            # ---------------------------------------------------------------
            else:
                buy_price = int(best_bid + 1)
                sell_price = int(best_ask - 1)

                if pos >= 9:
                    sell_price -= 1
                elif pos <= -9:
                    buy_price += 1

                # Sanity check
                if buy_price >= best_ask: buy_price = best_ask - 1
                if sell_price <= best_bid: sell_price = best_bid + 1

                buy_qty = max(0, self.limit - pos)
                sell_qty = max(0, self.limit + pos) 

                if buy_qty > 0:
                    orders.append(Order(product, buy_price, int(buy_qty)))
                if sell_qty > 0:
                    orders.append(Order(product, sell_price, int(-sell_qty)))

            if orders:
                result[product] = orders
            
        return result, conversions, json.dumps(data)