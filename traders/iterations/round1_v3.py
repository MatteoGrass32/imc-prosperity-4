from datamodel import OrderDepth, TradingState, Order
#from prosperity4bt.datamodel import OrderDepth, TradingState, Order

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

    # Static Mid-Price for standard calculations
    def mid_price(self):
        bb, ba = self.best_bid(), self.best_ask()
        if bb is not None and ba is not None:
            return (bb + ba) / 2
        return None

    # Dynamic VWAP to capture true market gravity
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
#  STRATEGY 1 — STATIC MARKET MAKING (Pennying & Strategic Orders)
# ─────────────────────────────────────────────

class MarketMakingStrategy(Strategy):
    """
    Used for ASH_COATED_OSMIUM.
    Focuses on pennying the spread to maximize fills in a volatile market.
    """
    PARAMS = {
        "ASH_COATED_OSMIUM": {"fair_value": 10000, "min_edge": 2, "quote_size": 20},
    }

    def run(self) -> List[Order]:
        params = self.PARAMS.get(self.product, {
            "fair_value": self.mid_price() or 10000,
            "min_edge": 2,
            "quote_size": 20,
        })

        fv = params["fair_value"]
        min_edge = params["min_edge"]
        size = params["quote_size"]
        
        # 1. Inventory Skewing: Adjusts center price to reduce exposure
        if abs(self.position) > 30: 
            skew = 0.25 * self.position
        elif abs(self.position) > 15: 
            skew = 0.15 * self.position
        else:
            skew = 0.05 * self.position 

        base_fv = fv - skew

        # 2. STRATEGIC ORDERS HINT (Order Book Pennying)
        # Aim: Place attractive orders that "fit" the book (Inspired by AI Orin)
        market_bid = self.best_bid()
        market_ask = self.best_ask()

        max_bid_we_accept = math.floor(base_fv - min_edge)
        min_ask_we_accept = math.ceil(base_fv + min_edge)

        # Pennying logic: Outbid competition by 1 tick while staying within safety margins
        if market_bid is not None:
            bid_price = min(max_bid_we_accept, market_bid + 1)
        else:
            bid_price = max_bid_we_accept

        if market_ask is not None:
            ask_price = max(min_ask_we_accept, market_ask - 1)
        else:
            ask_price = min_ask_we_accept

        buy_qty = self.clamp_buy(size)
        sell_qty = self.clamp_sell(size)
        orders: List[Order] = []

        if buy_qty > 0:
            orders.append(Order(self.product, bid_price, +buy_qty))
        if sell_qty > 0:
            orders.append(Order(self.product, ask_price, -sell_qty))

        return orders

# ─────────────────────────────────────────────
#  STRATEGY 3 — DIRECTIONAL TREND RIDER (Drift Exploitation)
# ─────────────────────────────────────────────

class DirectionalTrendStrategy(Strategy):
    """
    Used for INTARIAN_PEPPER_ROOT.
    Hoards inventory to profit from the deterministic upward drift.
    """
    PARAMS = {
        "INTARIAN_PEPPER_ROOT": {
            "spread": 5, 
            "target_position": 75, 
            "skew_factor": 0.25      
        },
    }

    def run(self) -> List[Order]:
        params = self.PARAMS.get(self.product, {"spread": 5, "target_position": 75, "skew_factor": 0.25})
        
        fv = self.vwap_price() 
        if fv is None:
            return []

        target_pos = params["target_position"]
        half_spread = params["spread"]
        
        # Asymmetric Skewing based on target offset (Spotting Trends Hint)
        position_offset = self.position - target_pos
        skew = position_offset * params["skew_factor"]
        
        bid_price = math.floor(fv - half_spread - skew)
        ask_price = math.ceil (fv + half_spread - skew)

        orders: List[Order] = []
        buy_qty = self.clamp_buy(80)
        sell_qty = self.clamp_sell(80)

        # Aggressive Taker component to fill inventory during drift
        if self.od.sell_orders:
            for ask_p, ask_vol in sorted(self.od.sell_orders.items()):
                if ask_p <= (fv - skew) and buy_qty > 0:
                    take_vol = min(buy_qty, abs(ask_vol))
                    if take_vol > 0:
                        orders.append(Order(self.product, ask_p, take_vol))
                        buy_qty -= take_vol
                else:
                    break 

        # Remaining capacity as passive orders
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
        "ASH_COATED_OSMIUM": MarketMakingStrategy,
        "INTARIAN_PEPPER_ROOT": DirectionalTrendStrategy,
    }
    # Default to MarketMaking if not specified
    cls = routing.get(product, MarketMakingStrategy)
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
        return result, 0, traderData