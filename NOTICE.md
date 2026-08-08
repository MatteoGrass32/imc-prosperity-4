# Third-party code

## `prosperity4bt/`, `visualizer.py`, `quick_plot.py`

The backtesting engine and the Streamlit visualiser are **not my work**. They come from
[blackswan-quants/prosperity4_imc](https://github.com/blackswan-quants/prosperity4_imc),
the shared environment my team built for the competition, and are redistributed here
under their MIT licence (Copyright (c) 2026 BlackswanQuants). A copy of that licence is
in [`LICENSE-prosperity4bt`](LICENSE-prosperity4bt).

They are vendored rather than linked so that this repository stays runnable on its own.
I made the following changes on top of the upstream code.

### Corrections

1. **Positions were marked to a price of zero on empty books.** A handful of ticks in the
   round 1 and round 2 data carry no bids and no asks at all, and the feed reports a mid
   price of 0 for them: 35 ticks on round 1 day 0, 38 on round 2 day 1. The runner marked
   inventory at that 0, which books a one-tick loss the size of the entire position. On
   round 1 that is a spurious **-960,764** in a run that ends the day at +94,589, and it
   wrecks every path-dependent metric: max drawdown read 1,356,627 instead of **1,607**,
   and annualised Sharpe read 0.23 instead of **53.5**. `mark_price()` in
   `prosperity4bt/runner.py` now carries the last real mid through those ticks. Final PnL
   is unchanged, on every round, and rounds 3 to 5 are unaffected because their data has
   no empty books.
2. **The trade history was invalid JSON.** `TradeRow.__str__` in `prosperity4bt/models.py`
   emitted a trailing comma after the last field of every trade object, so `json.loads`
   refused the whole `Trade History:` block and nothing could read our own fills back out
   of a run. Comma removed.
3. **Position limits held only the tutorial products.** Upstream shipped `EMERALDS` and
   `TOMATOES`, which appear in no round 1 to 5 dataset, so every product that was actually
   traded fell through to a default of 80. Round 5 therefore backtested effectively
   unconstrained against a real limit of 10, and rounds 3 and 4 were clipped against real
   limits of 200 and 300. Now in `prosperity4bt/rounds.py`, keyed by round.
4. **`visualizer.py` kept a second copy of those same limits**, with its own fallback of
   20, so the red inventory lines were drawn at 20 in every round of the competition. It
   now reads the one registry.
5. **`requirements.txt` was missing four packages the engine imports**: `orjson`,
   `ipython`, `tqdm` and `numpy`. Without them it does not start at all.

### Additions

1. `prosperity4bt/rounds.py`, new: products and position limits keyed by round, so the
   engine and the charts cannot disagree about what a limit is.
2. `prosperity4bt/file_reader.py` now transparently decompresses `.gz` datasets, so the
   raw CSVs (156 MB) can be committed gzipped (40 MB).
3. `plot_run.py` and `run_all.py`, both mine, described in the
   [README](README.md#running-a-backtest).

`quick_plot.py` is upstream and left as it was found. It builds one subplot per product
with no downsampling, which on a round 5 run means 50 stacked panels, a million points and
a 20,000 pixel figure in a 21 MB page, and it puts prices near 10,000 and PnL near 3,000 on
one shared axis. `plot_run.py` replaces it.

## Datasets under `data/`

Market data released by IMC during Prosperity 4. Reproduced here for reproducibility of
the backtests; all rights belong to IMC Trading.

## Everything else

`traders/`, `research/`, `manual/`, `results/`, `plot_run.py` and `run_all.py` are mine.
