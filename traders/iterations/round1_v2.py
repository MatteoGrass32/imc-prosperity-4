from datamodel import OrderDepth, TradingState, Order
#from prosperity4bt.datamodel import OrderDepth, TradingState, Order
# switch comments for internal backtest

from typing import List, Dict, Any
import json
import math

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────

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

    # Static Mid-Price (For perfectly mean-reverting products)
    def mid_price(self):
        bb, ba = self.best_bid(), self.best_ask()
        if bb is not None and ba is not None:
            return (bb + ba) / 2
        return None

    # Dynamic VWAP (Volume-Weighted Average Price to capture true market depth and trend direction)
    def vwap_price(self):
        total_value, total_vol = 0, 0
        for price, vol in self.od.buy_orders.items():
            total_value += price * vol
            total_vol += vol
        for price, vol in self.od.sell_orders.items():
            total_value += price * abs(vol)
            total_vol += abs(vol)
        
        if total_vol > 0:
            return total_value / total_vol
        return self.mid_price() 

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
#  STRATEGY 1 — STATIC MARKET MAKING (Mean Reverting)
# ─────────────────────────────────────────────

class MarketMakingStrategy(Strategy):
    PARAMS = {
        "EMERALDS": {"fair_value": 10000, "spread": 8, "quote_size": 20},
        "ASH_COATED_OSMIUM": {"fair_value": 10000, "spread": 8, "quote_size": 20},
    }

    def run(self) -> List[Order]:
        params = self.PARAMS.get(self.product, {
            "fair_value": self.mid_price() or 10000,
            "spread": 8,
            "quote_size": 20,
        })

        fv          = params["fair_value"]
        half_spread = params["spread"]
        size        = params["quote_size"]
        
        # Avellaneda-style Inventory Skewing
        if abs(self.position) > 30: 
            skew = 0.25 * self.position
        elif abs(self.position) > 15: 
            skew = 0.15 * self.position
        else:
            skew = 0.05 * self.position 

        bid_price = math.floor(fv - half_spread - skew)
        ask_price = math.ceil (fv + half_spread - skew)

        orders: List[Order] = []
        buy_qty = self.clamp_buy(size)
        sell_qty = self.clamp_sell(size)

        # Passive Market Making Only
        if buy_qty > 0:
            orders.append(Order(self.product, bid_price, +buy_qty))
        if sell_qty > 0:
            orders.append(Order(self.product, ask_price, -sell_qty))

        return orders

# ─────────────────────────────────────────────
#  STRATEGY 2 — EMA MARKET MAKING (Trend Following)
# ─────────────────────────────────────────────

class EMAMarketMakingStrategy(Strategy):
    PARAMS = {
        "TOMATOES": {
            "alpha": 0.25, 
            "spread": 5, 
            "quote_size": 80
        },
        "INTARIAN_PEPPER_ROOT": {
            # Lowered alpha to capture slow/steady growth, directly inspired by AI Orin's 'Spotting Trends' hint
            "alpha": 0.25, 
            "spread": 5, 
            "quote_size": 80
        }, 
    }

    def run(self) -> List[Order]:
        params = self.PARAMS.get(self.product, {
            "alpha": 0.25, 
            "spread": 5, 
            "quote_size": 20
        })
  
        # 1. Base pricing via VWAP
        mid = self.vwap_price() 
        if mid is None:
            return []

        # 2. Update Exponential Moving Average (EMA)
        key      = f"ema_{self.product}"
        alpha    = params["alpha"]
        prev_ema = self.memory.get(key, mid)
        ema      = alpha * mid + (1 - alpha) * prev_ema
        self.memory[key] = ema

        half_spread = params["spread"]
        size        = params["quote_size"]

        # 3. Inventory Skewing
        if abs(self.position) > 30: 
            skew = 0.25 * self.position
        elif abs(self.position) > 15: 
            skew = 0.15 * self.position
        else:
            skew = 0.05 * self.position 

        orders: List[Order] = []
        buy_qty = self.clamp_buy(size)
        sell_qty = self.clamp_sell(size)

        # 4. Aggressive Taker (Arbitrage against EMA)
        if self.od.sell_orders:
            for ask_p, ask_vol in sorted(self.od.sell_orders.items()):
                if ask_p < ema and buy_qty > 0:
                    take_vol = min(buy_qty, abs(ask_vol))
                    if take_vol > 0:
                        orders.append(Order(self.product, ask_p, take_vol))
                        buy_qty -= take_vol
                else:
                    break 

        if self.od.buy_orders:
            for bid_p, bid_vol in sorted(self.od.buy_orders.items(), reverse=True):
                if bid_p > ema and sell_qty > 0:
                    take_vol = min(sell_qty, bid_vol)
                    if take_vol > 0:
                        orders.append(Order(self.product, bid_p, -take_vol))
                        sell_qty -= take_vol
                else:
                    break

        # 5. Passive Market Making
        bid_price = math.floor(ema - half_spread - skew)
        ask_price = math.ceil (ema + half_spread - skew)

        if buy_qty > 0:
            orders.append(Order(self.product, bid_price, +buy_qty))
        if sell_qty > 0:
            orders.append(Order(self.product, ask_price, -sell_qty))

        return orders

# ─────────────────────────────────────────────
#  PRODUCT → STRATEGY ROUTING
# ─────────────────────────────────────────────

def get_strategy(product: str, state: TradingState, memory: Dict) -> Strategy:
    routing = {
        "EMERALDS": MarketMakingStrategy,
        "ASH_COATED_OSMIUM": MarketMakingStrategy,
        "TOMATOES": EMAMarketMakingStrategy,
        "INTARIAN_PEPPER_ROOT": EMAMarketMakingStrategy,
    }
    cls = routing.get(product, EMAMarketMakingStrategy)
    return cls(product, state, memory)

# ─────────────────────────────────────────────
#  TRADER ENTRY POINT
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
        conversions = 0

        return result, conversions, traderData