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
#  STRATEGY 1 — HYBRID DUAL-LAYER MARKET MAKING (ASH_COATED_OSMIUM)
#  Combines EMA-based Fair Value with Aggressive Taking and Tiered Quotes
# ─────────────────────────────────────────────

class MarketMakingStrategy(Strategy):
    def run(self) -> List[Order]:
        orders: List[Order] = []
        
        # 1. DYNAMIC FAIR VALUE (Your stable EMA mix)
        mid = self.mid_price() or 10000
        ema_key = f"ema_{self.product}"
        alpha = 0.35
        prev_ema = self.memory.get(ema_key, mid)
        ema = alpha * mid + (1 - alpha) * prev_ema
        self.memory[ema_key] = ema
        fv = 0.7 * mid + 0.3 * ema

        # 2. INVENTORY SKEW & CAPACITY
        # Using your linear skew for the safety net
        skew = 0.05 * self.position
        base_fv = fv - skew
        
        buy_capacity = self.buy_capacity()
        sell_capacity = self.sell_capacity()

        # 3. STEP 1: LIQUIDITY TAKING (Arbitrage)
        # Scan the book for "free money" crossing our skewed Fair Value
        if self.od.sell_orders:
            for ask_p, ask_v in sorted(self.od.sell_orders.items()):
                if ask_p < math.floor(base_fv) and buy_capacity > 0:
                    take_vol = min(buy_capacity, abs(ask_v))
                    orders.append(Order(self.product, ask_p, take_vol))
                    buy_capacity -= take_vol
                else: break

        if self.od.buy_orders:
            for bid_p, bid_v in sorted(self.od.buy_orders.items(), reverse=True):
                if bid_p > math.ceil(base_fv) and sell_capacity > 0:
                    take_vol = min(sell_capacity, bid_v)
                    orders.append(Order(self.product, bid_p, -take_vol))
                    sell_capacity -= take_vol
                else: break

        # 4. STEP 2: DUAL-LAYER PENNYING
        # Use remaining capacity to fill the book at two depth levels
        market_bid = self.best_bid()
        market_ask = self.best_ask()
        
        # Safety limits (min_edge = 2)
        max_bid_limit = math.floor(base_fv - 2)
        min_ask_limit = math.ceil(base_fv + 2)

        # Dynamic Pegging (Competitive prices)
        my_bid = min(max_bid_limit, (market_bid + 1) if market_bid else max_bid_limit)
        my_ask = max(min_ask_limit, (market_ask - 1) if market_ask else min_ask_limit)

        # Split remaining capacity into Tight (50%) and Deep (50%)
        if buy_capacity > 0:
            tight_buy = buy_capacity // 2
            deep_buy = buy_capacity - tight_buy
            if tight_buy > 0:
                orders.append(Order(self.product, my_bid, tight_buy))
            if deep_buy > 0:
                # Place deep order 2 ticks behind for "fat finger" protection
                orders.append(Order(self.product, my_bid - 2, deep_buy))

        if sell_capacity > 0:
            tight_sell = sell_capacity // 2
            deep_sell = sell_capacity - tight_sell
            if tight_sell > 0:
                orders.append(Order(self.product, my_ask, -tight_sell))
            if deep_sell > 0:
                # Place deep order 2 ticks behind
                orders.append(Order(self.product, my_ask + 2, -deep_sell))

        return orders
# ─────────────────────────────────────────────
#  STRATEGY 2 — PROTECTED TREND RIDER (For Pepper)
# ─────────────────────────────────────────────
class DirectionalTrendStrategy(Strategy):
    """
    Directional strategy with an Emergency Exit trigger.
    If the price drops sharply below a slow EMA, it liquidates the position.
    """
    def run(self) -> List[Order]:
        fv = self.vwap_price() 

        # --- TREND SAFETY GUARD (Cataclysm Protection) ---
        ema_slow_key = f"ema_slow_{self.product}"
        # A slower alpha (0.05) to track the long-term trend
        prev_ema_slow = self.memory.get(ema_slow_key, fv)
        ema_slow = 0.05 * fv + (0.95) * prev_ema_slow
        self.memory[ema_slow_key] = ema_slow

        target_pos = 75
        # If price falls 20 ticks below slow EMA, we assume trend is dead
        if fv < (ema_slow - 20):
            target_pos = 0 # EMERGENCY LIQUIDATION

        # --- STANDARD LOGIC ---
        position_offset = self.position - target_pos
        skew = position_offset * 0.25
        
        bid_price = math.floor(fv - 5 - skew)
        ask_price = math.ceil (fv + 5 - skew)

        orders: List[Order] = []
        buy_qty = self.clamp_buy(80)
        sell_qty = self.clamp_sell(80)

        # Do not buy if we are in Emergency Mode (target_pos = 0)
        if self.od.sell_orders and target_pos > 0:
            for ask_p, ask_vol in sorted(self.od.sell_orders.items()):
                if ask_p <= (fv - skew) and buy_qty > 0:
                    take_vol = min(buy_qty, abs(ask_vol))
                    orders.append(Order(self.product, ask_p, take_vol))
                    buy_qty -= take_vol
                else: break 

        if buy_qty > 0 and target_pos > 0:
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