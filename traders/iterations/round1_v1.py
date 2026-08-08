from datamodel import OrderDepth, TradingState, Order
# when uploading bot, change to above line and comment out the line below
#from prosperity4bt.datamodel import OrderDepth, TradingState, Order
from typing import List, Dict, Any
import json
import math

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────

# RICORDA: Verifica i limiti di posizione esatti sul manuale del Round 1!
POSITION_LIMITS: Dict[str, int] = {
    "EMERALDS": 80,
    "TOMATOES": 80,
    "INTARIAN_PEPPER_ROOT": 80,
    "ASH_COATED_OSMIUM": 80
}

# ─────────────────────────────────────────────
#  BASE STRATEGY
# ─────────────────────────────────────────────

class Strategy:
    def __init__(self, product: str, state: TradingState, memory: Dict[str, Any]):
        self.product  = product
        self.state    = state
        self.memory   = memory
        self.position = state.position.get(product, 0)
        self.limit    = POSITION_LIMITS.get(product, 20)
        self.od: OrderDepth = state.order_depths.get(product, OrderDepth())

    def best_bid(self):
        return max(self.od.buy_orders) if self.od.buy_orders else None

    def best_ask(self):
        return min(self.od.sell_orders) if self.od.sell_orders else None

    def mid_price(self):
        bb, ba = self.best_bid(), self.best_ask()
        if bb is not None and ba is not None:
            return (bb + ba) / 2
        return None

    def buy_capacity(self):
        return self.limit - self.position

    def sell_capacity(self):
        return self.limit + self.position

    def clamp_buy(self, qty: int) -> int:
        return min(qty, self.buy_capacity())

    def clamp_sell(self, qty: int) -> int:
        return min(qty, self.sell_capacity())

    def run(self) -> List[Order]:
        raise NotImplementedError

# ─────────────────────────────────────────────
#  STRATEGY 1 — MARKET MAKING (stable products)
# ─────────────────────────────────────────────

class MarketMakingStrategy(Strategy):
    PARAMS = {
        "EMERALDS": {
            "fair_value":   10000,
            "spread":       8,
            "quote_size":   20,
        },
        "ASH_COATED_OSMIUM": {
            "fair_value":   10000, # L'Osmio si comporta come gli Smeraldi
            "spread":       8,
            "quote_size":   20,
        },
    }

    def run(self) -> List[Order]:
        params = self.PARAMS.get(self.product, {
            "fair_value":   self.mid_price() or 10000,
            "spread":       8,
            "quote_size":   20,
        })

        fv          = params["fair_value"]
        half_spread = params["spread"]
        size        = params["quote_size"]
        
        if abs(self.position) > 30: # Aggressive
            skew = 0.25 * self.position
        elif abs(self.position) > 15: # Moderate
            skew = 0.15 * self.position
        else:
            skew = 0.05 * self.position # Soft

        bid_price = math.floor(fv - half_spread - skew)
        ask_price = math.ceil (fv + half_spread - skew)

        orders: List[Order] = []

        buy_qty = self.clamp_buy(size)
        if buy_qty > 0:
            orders.append(Order(self.product, bid_price, +buy_qty))

        sell_qty = self.clamp_sell(size)
        if sell_qty > 0:
            orders.append(Order(self.product, ask_price, -sell_qty))

        return orders

# ─────────────────────────────────────────────
#  STRATEGY 2 — EMA MARKET MAKING (noisy products)
# ─────────────────────────────────────────────

class EMAMarketMakingStrategy(Strategy):
    PARAMS = {
        "TOMATOES": {
            "alpha":        0.5,
            "spread":       5,
            "quote_size":   80,
        },
        "INTARIAN_PEPPER_ROOT": {
            "alpha":        0.5,   # La radice di pepe ha un forte trend, serve l'EMA
            "spread":       5,
            "quote_size":   80,
        },
    }

    def run(self) -> List[Order]:
        params = self.PARAMS.get(self.product, {
            "alpha": 0.5, 
            "spread": 5, 
            "quote_size": 20, 
            "skew_factor": 0.3
        })
  
        mid = self.mid_price()
        if mid is None:
            return []

        key      = f"ema_{self.product}"
        alpha    = params["alpha"]
        prev_ema = self.memory.get(key, mid)
        ema      = alpha * mid + (1 - alpha) * prev_ema
        self.memory[key] = ema

        half_spread = params["spread"]
        size        = params["quote_size"]

        if abs(self.position) > 30: # Aggressive 
            skew = 0.25 * self.position
        elif abs(self.position) > 15: # Moderate
            skew = 0.15 * self.position
        else:
            skew = 0.05 * self.position # Soft

        bid_price = math.floor(ema - half_spread - skew)
        ask_price = math.ceil (ema + half_spread - skew)

        orders: List[Order] = []

        buy_qty = self.clamp_buy(size)
        if buy_qty > 0:
            orders.append(Order(self.product, bid_price, +buy_qty))

        sell_qty = self.clamp_sell(size)
        if sell_qty > 0:
            orders.append(Order(self.product, ask_price, -sell_qty))

        return orders

# ─────────────────────────────────────────────
#  PRODUCT → STRATEGY ROUTING
# ─────────────────────────────────────────────

def get_strategy(product: str, state: TradingState, memory: Dict) -> Strategy:
    # Qui diciamo al bot come trattare ogni specifico prodotto
    routing = {
        "EMERALDS": MarketMakingStrategy,
        "ASH_COATED_OSMIUM": MarketMakingStrategy,
        "TOMATOES": EMAMarketMakingStrategy,
        "INTARIAN_PEPPER_ROOT": EMAMarketMakingStrategy,
    }
    cls = routing.get(product, EMAMarketMakingStrategy)
    return cls(product, state, memory)

# ─────────────────────────────────────────────
#  TRADER
# ─────────────────────────────────────────────

class Trader:
    def run(self, state: TradingState):
        try:
            memory: Dict[str, Any] = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            memory = {}

        result: Dict[str, List[Order]] = {}

        for product in state.order_depths:
            strategy = get_strategy(product, state, memory)
            try:
                orders = strategy.run()
            except Exception as e:
                print(f"[ERROR] {product}: {e}")
                orders = []
            result[product] = orders

        traderData = json.dumps(memory)
        
        # Obbligatorio per la sintassi di sistema
        conversions = 0

        return result, conversions, traderData
