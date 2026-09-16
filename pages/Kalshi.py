import asyncio
import logging
import time
from collections import deque
import numpy as np
from scipy.stats import norm

# Configure logging for real-time monitoring
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("Kalshi15MinQuant")

class KalshiBTC15MinQuantEngine:
    def __init__(self, fee_drag_cents: float = 0.02, min_edge_cents: float = 0.015):
        """
        Initializes the quant engine with built-in Kalshi settlement mechanics.
        """
        self.fee_drag = fee_drag_cents
        self.min_edge = min_edge_cents
        
        # Kalshi rule: 60-second average of the index sampled once per second in the final minute
        self.final_minute_buffer = deque(maxlen=60)

    def estimate_realized_volatility(self, price_series: list[float], window_seconds: int = 60) -> float:
        """
        Calculates short-window realized volatility from high-frequency price ticks.
        """
        if len(price_series) < 2:
            return 0.50  
        
        recent_prices = np.array(price_series[-window_seconds:])
        log_returns = np.diff(np.log(recent_prices))
        
        if len(log_returns) == 0 or np.all(log_returns == 0):
            return 0.01

        sec_per_year = 365.25 * 24 * 3600
        per_second_vol = np.std(log_returns, ddof=1)
        annualized_vol = per_second_vol * np.sqrt(sec_per_year)
        
        return float(annualized_vol)

    def calculate_fair_probability(
        self, 
        current_spot: float, 
        strike_price: float, 
        sec_remaining: int, 
        realized_vol: float
    ) -> float:
        """
        Calculates the fair probability of BTC expiring above the strike price,
        accounting for Kalshi's 60-second average settlement mechanism.
        """
        if sec_remaining <= 0:
            # If window is closed, calculate using the final locked settlement average if available
            if len(self.final_minute_buffer) > 0:
                settlement_val = sum(self.final_minute_buffer) / len(self.final_minute_buffer)
                return 1.0 if settlement_val > strike_price else 0.0
            return 1.0 if current_spot > strike_price else 0.0

        # --- KALSHI RULE INTEGRATION: Final Minute Handling ---
        if sec_remaining <= 60:
            # We actively sample the current price into our rolling 60-second buffer
            self.final_minute_buffer.append(current_spot)
            
            # The final settlement value is a blend of what's *already locked in* 
            # and what is *expected* to happen in the remaining seconds of the minute.
            locked_sum = sum(self.final_minute_buffer)
            locked_count = len(self.final_minute_buffer)
            remaining_count = 60 - locked_count
            
            # Expected average projection for the remaining ticks in the final minute
            expected_future_sum = remaining_count * current_spot
            projected_settlement_mean = (locked_sum + expected_future_sum) / 60.0
            
            # Use the projected settlement mean as our drift anchor for the final minute
            effective_price_anchor = projected_settlement_mean
        else:
            # Reset buffer if we are outside the final minute window
            self.final_minute_buffer.clear()
            effective_price_anchor = current_spot

        # Scale annual volatility down to the remaining fraction of the year
        time_fraction = sec_remaining / (365.25 * 24 * 3600)
        std_dev = effective_price_anchor * realized_vol * np.sqrt(time_fraction)

        if std_dev == 0:
            return 1.0 if effective_price_anchor > strike_price else 0.0

        # Z-score calculation based on the effective settlement target
        z_score = (strike_price - effective_price_anchor) / std_dev
        prob_above = 1.0 - norm.cdf(z_score)

        return float(prob_above)

    def evaluate_orderbook(
        self, 
        fair_prob: float, 
        bid_price: float, 
        ask_price: float
    ) -> dict:
        """
        Evaluates market prices against the fair probability model,
        accounting for transaction costs, fees, and spread constraints.
        """
        signal = "HOLD"
        target_side = None
        limit_price = 0.0
        edge = 0.0

        # Evaluate Buying YES
        buy_yes_edge = fair_prob - ask_price
        if buy_yes_edge > (self.fee_drag + self.min_edge):
            signal = "EXECUTE"
            target_side = "YES"
            limit_price = ask_price
            edge = buy_yes_edge

        # Evaluate Buying NO
        no_fair_prob = 1.0 - fair_prob
        no_market_ask = 1.0 - bid_price
        buy_no_edge = no_fair_prob - no_market_ask
        
        if buy_no_edge > (self.fee_drag + self.min_edge) and buy_no_edge > edge:
            signal = "EXECUTE"
            target_side = "NO"
            limit_price = bid_price  
            edge = buy_no_edge

        return {
            "signal": signal,
            "target_side": target_side,
            "limit_price": limit_price,
            "fair_prob": fair_prob,
            "estimated_edge": edge
        }

    async def run_market_loop(self):
        """
        Asynchronous simulation loop demonstrating behavior down into the final 60 seconds.
        """
        logger.info("Starting Kalshi 15M BTC Quant Loop with Settlement Rules...")
        
        mock_price_feed = [65000.0 + np.random.normal(0, 5) for _ in range(100)]
        strike = 65010.0
        seconds_left = 75  # Starting just outside the final minute to show transition
        
        while seconds_left >= 0:
            current_spot = mock_price_feed[-1]
            new_price = current_spot + np.random.normal(0, 2.0)
            mock_price_feed.append(new_price)
            
            # 1. Compute Volatility
            vol = self.estimate_realized_volatility(mock_price_feed)
            
            # 2. Calculate Fair Value Probability (incorporates 60s rule when <= 60s)
            fair_p = self.calculate_fair_probability(current_spot, strike, seconds_left, vol)
            
            # 3. Simulate incoming Kalshi book quotes
            mock_bid = 0.48
            mock_ask = 0.52
            
            # 4. Evaluate execution logic
            decision = self.evaluate_orderbook(fair_p, mock_bid, mock_ask)
            
            if decision["signal"] == "EXECUTE":
                logger.info(f">>> EDGE FOUND [Secs Left: {seconds_left}] Side: {decision['target_side']} | Edge: {decision['estimated_edge']:.4f} | Fair Prob: {fair_p:.3f}")
            
            seconds_left -= 1
            await asyncio.sleep(0.1) # Speed up simulation loop for testing

# Execution entry point
if __name__ == "__main__":
    engine = KalshiBTC15MinQuantEngine()
    try:
        asyncio.run(engine.run_market_loop())
    except KeyboardInterrupt:
        logger.info("Quant engine manually stopped.")
