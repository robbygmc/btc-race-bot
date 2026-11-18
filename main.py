"""CBBTC 1-minute trend bot for make.fun btc-race-24h-20261118-1444.

Strategy (original design, written for this competition):
  * Long only, at most one position, up to 100% of equity.
  * Trend filter: only trade when the latest close is above a slow 240-minute
    exponential moving average of closes. In a falling market the bot sits in
    cash instead of riding the decline.
  * Entry (flat): the trailing 60-minute return is at least +30 bps while the
    trend filter holds. A full-size round trip costs roughly 30-40 bps in
    fees, slippage and price impact, so only a move already larger than that
    is worth chasing; the 60-minute window catches multi-hour drifts rather
    than 1-minute noise (per-minute moves average ~7 bps). Two guards keep
    the entry honest: skip a move already above +150 bps in the hour (that
    leg is mostly spent, and the fill would be at a stretched price), and
    wait 60 minutes after any exit before re-entering, so a choppy market
    cannot whipsaw the bot into paying the round-trip cost again and again.
  * Exit (holding): the trailing 60-minute return drops below -40 bps, i.e.
    the drift that justified the entry has reversed. A 150 bps trailing stop
    below the highest close since entry is a safety net for a sharp drop; it
    never fired on the dev window, it only caps the downside on the race.
  * No randomness, no wall clock, no network, no files: every decision is a
    pure function of the bars received, so two runs on the same data produce
    byte-identical action logs.

Protocol: agent-fun/bars-replay/v1, via the kit's Python shim (vendored
byte-identical under vendor/). One reply per batch, exactly one order at
most per reply (a buy or a full sell). Fills land at the next bar's open;
max_slippage_bps 200 bounds the fill against the latest close (the largest
1-minute move on the dev window was ~64 bps, so the cap never binds there
and only guards against a gap on the race window).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# Strategy constants (basis points unless noted).
TREND_BARS = 240          # slow EMA length for the trend filter
TREND_ALPHA = 2.0 / (TREND_BARS + 1)
MIN_BARS = 243            # bars of history before the first entry (bar index >= 242)
MOM_LOOKBACK = 60         # minutes for the trailing-return signal
ENTRY_BP = 30             # enter when the 60-min return is at least +30 bps
ENTRY_CAP_BP = 150        # never chase a 60-min move already above +150 bps
COOLDOWN_BARS = 60        # minutes to wait after an exit before re-entering
EXIT_BP = -40             # exit when the 60-min return falls below -40 bps
TRAIL_BP = 150            # trailing stop below the peak close since entry
MAX_SLIP_BP = 200         # max slippage vs the latest close, buy and sell


class TrendBot:
    """Keeps the close history, the slow EMA and the open-trade state."""

    def __init__(self):
        self.closes = []        # raw close prices (price_scale units), oldest first
        self.ema = None         # slow EMA of closes, float
        self.peak = 0           # highest close since the current entry
        self.last_exit = -10 ** 9  # bar index of the most recent exit

    def trailing_return_bp(self):
        """Return over the last MOM_LOOKBACK minutes, in basis points."""
        if len(self.closes) <= MOM_LOOKBACK:
            return 0.0
        now = self.closes[-1]
        then = self.closes[-1 - MOM_LOOKBACK]
        return (now - then) * 10000.0 / then

    def on_batch(self, state, batch):
        if state.warming_up:
            return []
        px = state.close(SYMBOL)
        if px is None:
            return []
        self.closes.append(px)
        if self.ema is None:
            self.ema = float(px)
        else:
            self.ema = TREND_ALPHA * px + (1.0 - TREND_ALPHA) * self.ema

        holding = state.positions.get(SYMBOL)
        if holding is not None and holding.qty > 0:
            if px > self.peak:
                self.peak = px
            if self.trailing_return_bp() < EXIT_BP:
                self.last_exit = state.seq
                return [{"side": "sell", "symbol": SYMBOL,
                         "qty": holding.qty, "max_slippage_bps": MAX_SLIP_BP}]
            if px < self.peak * (1.0 - TRAIL_BP / 10000.0):
                self.last_exit = state.seq
                return [{"side": "sell", "symbol": SYMBOL,
                         "qty": holding.qty, "max_slippage_bps": MAX_SLIP_BP}]
            return []

        # Flat: only enter with enough history, in an uptrend, on momentum.
        if len(self.closes) < MIN_BARS:
            return []
        if px <= self.ema:
            return []
        momentum = self.trailing_return_bp()
        if momentum < ENTRY_BP or momentum > ENTRY_CAP_BP:
            return []
        if state.seq - self.last_exit < COOLDOWN_BARS:
            return []
        notional = state.cash
        if notional < 1_000_000:
            return []
        self.peak = px
        return [{"side": "buy", "symbol": SYMBOL,
                 "notional_quote_units": notional, "max_slippage_bps": MAX_SLIP_BP}]


makefun_bars.run(TrendBot().on_batch)
