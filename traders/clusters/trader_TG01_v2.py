from datamodel import Order, TradingState, OrderDepth
import collections
from typing import List, Dict
import json
import math

class Trader:
    def __init__(self):
        self.products = [
            "GALAXY_SOUNDS_BLACK_HOLES",
            "GALAXY_SOUNDS_DARK_MATTER",
            "GALAXY_SOUNDS_PLANETARY_RINGS",
            "GALAXY_SOUNDS_SOLAR_FLAMES",
            "GALAXY_SOUNDS_SOLAR_WINDS"
        ]

        # RIMOSSO RINGS dalle configs oracolo, ora usa una logica a sé.
        self.configs = {
            "GALAXY_SOUNDS_BLACK_HOLES": ("PEBBLES_S", 20559.43, -1.0179, 446.23),
            "GALAXY_SOUNDS_DARK_MATTER": ("UV_VISOR_YELLOW", 6144.54, 0.3725, 211.76),
            "GALAXY_SOUNDS_SOLAR_WINDS": ("PANEL_1X4", 15490.14, -0.5376, 302.85),
            "GALAXY_SOUNDS_SOLAR_FLAMES": ("GALAXY_SOUNDS_SOLAR_WINDS", 14003.29, -0.2789, 424.10)
        }

        self.pos_limit = 10
        self.entry_z = 1.0
        self.exit_z = 0.2

        self.max_trade_z_by_product = {
            "GALAXY_SOUNDS_BLACK_HOLES": 2.5,
            "GALAXY_SOUNDS_DARK_MATTER": 2.5,
            "GALAXY_SOUNDS_SOLAR_FLAMES": 3.5,
            "GALAXY_SOUNDS_SOLAR_WINDS": 2.5,
        }

        self.disabled_products = set() # Tutto attivo

    def get_mid_price(self, order_depth: OrderDepth):
        if not order_depth or not order_depth.buy_orders or not order_depth.sell_orders:
            return None
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        return (best_bid + best_ask) / 2

    def run(self, state: TradingState):
        result = {}
        conversions = 0
        traderData = state.traderData or ""

        mids = {}
        for p in state.order_depths:
            mids[p] = self.get_mid_price(state.order_depths[p])

        for target in self.products:
            if target in self.disabled_products:
                continue
            if target not in state.order_depths:
                continue

            target_depth = state.order_depths[target]
            if not target_depth.buy_orders or not target_depth.sell_orders:
                continue

            best_bid = max(target_depth.buy_orders.keys())
            best_ask = min(target_depth.sell_orders.keys())
            current_pos = state.position.get(target, 0)
            target_mid = mids.get(target)

            # ==========================================
            # LOGICA MARKET MAKING PER RINGS
            # ==========================================
            if target == "GALAXY_SOUNDS_PLANETARY_RINGS":
                orders = []
                buy_qty = self.pos_limit - current_pos
                sell_qty = -self.pos_limit - current_pos
                
                # Partiamo cercando di prezzare appena all'interno dello spread per essere competitivi
                base_bid = best_bid + 1
                base_ask = best_ask - 1
                
                # Skewing dell'Inventario (Inventory Management)
                # Più posizioni abbiamo da un lato, più spostiamo le nostre quote per scoraggiare nuovi 
                # ordini da quella parte e incoraggiare l'uscita
                skew_multiplier = 1.5 
                skew = current_pos * skew_multiplier
                
                base_bid -= skew
                base_ask -= skew
                
                # Assicuriamoci di non quotare a prezzi incrociati o illogici
                my_bid = min(base_bid, best_ask - 1)
                my_ask = max(base_ask, best_bid + 1)
                
                if buy_qty > 0:
                    orders.append(Order(target, int(math.floor(my_bid)), buy_qty))
                if sell_qty < 0:
                    orders.append(Order(target, int(math.ceil(my_ask)), sell_qty))
                    
                result[target] = orders
                continue

            # ==========================================
            # LOGICA STAT-ARB ORIGINALE PER GLI ALTRI
            # ==========================================
            if target not in self.configs:
                continue

            oracle, alpha, beta, std = self.configs[target]
            oracle_mid = mids.get(oracle)

            if oracle_mid is None or target_mid is None:
                continue

            fair_target = alpha + beta * oracle_mid
            
            buy_orders = collections.OrderedDict(sorted(target_depth.buy_orders.items(), reverse=True))
            sell_orders = collections.OrderedDict(sorted(target_depth.sell_orders.items()))

            spread = target_mid - fair_target
            z_score = spread / std
            max_trade_z = self.max_trade_z_by_product[target]

            orders = []

            if abs(z_score) > max_trade_z:
                target_pos = 0
            elif z_score < -self.entry_z:
                target_pos = self.pos_limit
            elif z_score > self.entry_z:
                target_pos = -self.pos_limit
            elif abs(z_score) < self.exit_z:
                target_pos = 0
            else:
                target_pos = current_pos

            diff = target_pos - current_pos

            if diff > 0:
                need = diff
                for price, vol in sell_orders.items():
                    if price <= fair_target:
                        buy_qty = min(need, -vol)
                        if buy_qty > 0:
                            orders.append(Order(target, price, buy_qty))
                            need -= buy_qty
                    if need <= 0:
                        break

                if need > 0:
                    if target == "GALAXY_SOUNDS_SOLAR_FLAMES":
                        passive_bid = best_bid + 1
                    else:
                        passive_bid = min(best_bid + 1, best_ask - 1) if best_ask - best_bid > 1 else best_bid
                    orders.append(Order(target, passive_bid, need))

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
                    if target == "GALAXY_SOUNDS_SOLAR_FLAMES":
                        passive_ask = best_ask - 1
                    else:
                        passive_ask = max(best_ask - 1, best_bid + 1) if best_ask - best_bid > 1 else best_ask
                    orders.append(Order(target, passive_ask, -need))

            result[target] = orders

        return result, conversions, traderData