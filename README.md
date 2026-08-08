# IMC Prosperity 4

Trading strategies and research for [IMC Prosperity 4](https://prosperity.imc.com/), a
five-round algorithmic trading competition. Team **FeynmanKac** finished **755th out of
18,803 teams** (top 4%), **11th in Italy**, with **259,496 seashells**.

The last round was the best one: **249th worldwide on the algorithmic leg**.

![Final leaderboard](results/leaderboard_final.png)

This repository holds my own traders, my research notes, and a backtester that runs them
on the real competition data. Everything reported below is reproducible from a clone with
two commands.

## Quickstart

```bash
git clone https://github.com/MatteoGrass32/imc-prosperity-4.git
cd imc-prosperity-4
make backtest
```

`make backtest` builds the virtualenv on first run and backtests the final round 5 trader
on day 2. The datasets are committed (gzipped) so there is nothing to download.

```bash
make backtest DAY=5-4                                    # another day
make backtest TRADER=traders/round4_trader.py DAY=4-3    # another round
make visualize                                           # Streamlit view of the last run
```

Each run prints per-product PnL, then Sharpe, Sortino, max drawdown and Calmar, then mean
and mean-absolute inventory per product.

## Round 5: 50 products, 10 clusters

Round 5 replaced everything with 50 new products, all with a position limit of 10. Handled
one at a time that is 50 separate research problems on a competition clock. The products
came in 10 labelled groups of 5, so the tractable move was to stop trading products and
start trading clusters, and to spend the research budget on deciding what kind of structure
each cluster had rather than on tuning any single instrument.

The per-cluster work is in [`research/notes/`](research/notes): base statistics,
autocorrelation at lags 1/5/10, price ratios with their coefficient of variation, ADF
tests on those ratios, FFT for dominant periods, cross-correlation and lead-lag. Figures
are in [`research/figures/`](research/figures), the notebook is
[`research/prosperity_r5_analysis.ipynb`](research/prosperity_r5_analysis.ipynb).

That triage produced three kinds of cluster, and
[`traders/round5_final.py`](traders/round5_final.py) implements one strategy per cluster
accordingly:

- **Cross-sectional relationships that held.** TG01 Galaxy Sounds prices each member off a
  regression against a chosen reference instrument, sometimes from another cluster.
- **Ratios that oscillated but did not mean-revert cleanly.** TG02 Sleeping Pods showed
  oscillation amplitudes of 150 to 260 points against a spread of 19, so the trade paid,
  but ADF p-values of 0.11 to 0.52 said the ratios were not stationary. Traded with a
  trend filter on top of the skew rather than as a pure pair.
- **Structure that was drifting.** TG04 Pebbles, discussed below.

Ten standalone single-cluster traders are in [`traders/clusters/`](traders/clusters). They
are how each strategy was developed and tested in isolation before being merged into the
final book.

Results, day by day and cluster by cluster: [`results/`](results/README.md).

| | PnL | Sharpe (ann.) | Max drawdown |
|---|--:|--:|--:|
| Day 5-2 | 292,473 | 74.92 | 28,294 |
| Day 5-3 | 332,886 | 86.52 | 25,694 |
| Day 5-4 | 444,286 | 109.40 | 20,150 |

## What went wrong in round 4

Round 4 was the team's worst algorithmic round, 1051st, and the only one where the overall
rank moved down. It is the more useful half of this repository.

The round 4 book traded two underlyings and a 10-strike option chain. Backtested on the
three round 4 days it returns 4,722, then -17,345, then 85,297. The PnL is not the problem.
The problem is the column next to it:

| Day | PnL | Max drawdown | Calmar |
|---|--:|--:|--:|
| 4-1 | 4,722 | 76,578 | 0.06 |
| 4-2 | -17,345 | 84,499 | -0.21 |
| 4-3 | 85,297 | 79,599 | 1.07 |

Drawdown is essentially constant at 76k to 85k regardless of the outcome. The book was
putting up the same large risk every day and getting paid for it on one day out of three.
The round 3 version of the same strategy, on the same instruments, made 127,782 across its
three days with drawdowns of 7.6k to 22.6k. The rewrite kept 57% of the PnL and multiplied
the average drawdown by six.

The reason is a regime change that the research had already flagged and the strategy
ignored. The relationships were fitted on the training days as mean-reverting, and out of
sample they trended. The clearest record of it is in the TG04 notes:

```
Day 2  spread_mean=+1937  max=+5194  min=-1015
Day 3  spread_mean=+4328  max=+6361  min=+2409
Day 4  spread_mean=+5831  max=+9050  min=+2399
```

A spread whose mean moves monotonically from +1937 to +5831 across three days is not
oscillating around a level, it is going somewhere. The stationarity tests said the same
thing in advance: ADF p-values of 0.36 to 0.58 on the TG04 ratios, 0.11 to 0.52 on TG02.
The signal was measured and written down before the round, and the position sizing was
built as if it had not been.

What changed for round 5 was not the models, it was where the risk control sits. Limits and
thresholds are declared per cluster in one config block instead of being scattered through
the signal code, clusters whose ratios failed ADF get a trend filter before any
mean-reversion trade fires, and the hard shorts are explicit in that config instead of
emerging from the signal. The result is in the drawdown column: round 5 makes 14.7 times
the round 4 PnL on a third of the average drawdown.

This is the same failure mode as distribution shift in a deployed machine learning model. A
relationship that is real in the training window, a deployment window where it no longer
holds, and a system with no mechanism for noticing. The fix is not a better estimate of the
relationship, it is sizing that degrades when the relationship stops describing the data.

## Layout

```
traders/
  round5_final.py        final round 5 book, 10 cluster strategies
  round4_trader.py       options market making on the VEV chain
  round3_trader.py       earlier version of the same
  clusters/              the 10 single-cluster traders, developed in isolation
research/
  notes/                 per-cluster statistics, ADF, FFT, lead-lag
  figures/               correlation, lead-lag, z-score and ratio plots
  prosperity_r5_analysis.ipynb
data/                    competition data, rounds 1 to 5, gzipped
results/                 backtest tables and raw run output
prosperity4bt/           backtesting engine (see NOTICE.md)
```

## Attribution

The backtesting engine (`prosperity4bt/`), `visualizer.py` and `quick_plot.py` are not my
work. They come from the shared environment my team built during the competition and are
redistributed here under their MIT licence, with three small changes of mine. Details and
licence in [NOTICE.md](NOTICE.md).

`traders/`, `research/` and `results/` are mine. Data belongs to IMC Trading.
