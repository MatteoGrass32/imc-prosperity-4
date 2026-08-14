# IMC Prosperity 4

[IMC Prosperity 4](https://prosperity.imc.com/) is a five-round algorithmic trading
competition. Team **FeynmanKac** finished **755th of 18,803** (top 4%), **11th in Italy**,
with 259,496 seashells. The last round was the best: **249th worldwide** on the algorithmic
leg.

![Final leaderboard](results/leaderboard_final.png)

Each round had two halves. The **algorithmic** half was a trading bot, submitted and scored
on market data. The **manual** half was one decision, taken once, scored once. This
repository has both, plus the backtester needed to re-run the algorithmic side.

Round 5 is the round worth reading, and it has [its own section](#round-5-50-products-10-clusters)
below. Rounds 1 to 4 get [a page each](#the-other-rounds).

---

## Running a backtest

```bash
git clone https://github.com/MatteoGrass32/imc-prosperity-4.git
cd imc-prosperity-4
make setup                  # creates .venv, installs deps; the datasets are already here
make backtest               # the round 5 trader on round 5 day 2, plus its chart
make backtest-all           # every round on every day it shipped, 15 runs, ~2 min
```

`make backtest` prints per-product PnL, then Sharpe, Sortino, max drawdown and Calmar, then
mean and mean-absolute inventory per product, and writes `plots/run_5-2.html`. `make
backtest-all` adds a summary table against each round's official result and leaves ~350 MB
of logs and charts behind, all gitignored and all removed by `make clean`; narrow it with
`ARGS="--rounds 4 5"` or `ARGS=--no-plots`.

Pick a strategy and a day with `TRADER` and `DAY`, where `DAY` is `<round>-<day>`:

```bash
make backtest TRADER=traders/round5_final.py DAY=5-4
make backtest TRADER=traders/round1_final.py DAY=1--2     # day -2, note the two dashes
```

Every day below was visible while the strategy was being written. The day each round was
actually scored on is not in this repository and never was, which is the subject of
[the out-of-sample section](#how-the-strategies-held-up-out-of-sample):

| Round | Days shipped, all visible | Scored on | Trader |
|---|---|--:|---|
| 1 | `1--2`, `1--1`, `1-0` | day 1 | `traders/round1_final.py` |
| 2 | `2--1`, `2-0`, `2-1` | day 2 | `traders/round2_final.py` |
| 3 | `3-0`, `3-1`, `3-2` | day 3 | `traders/round3_trader.py` |
| 4 | `4-1`, `4-2`, `4-3` | day 4 | `traders/round4_trader.py` |
| 5 | `5-2`, `5-3`, `5-4` | day 5 | `traders/round5_final.py` |

`make` only wraps one command, so this is the same thing, and the same four arguments run it
from an IDE with the interpreter pointed at `.venv`:

```bash
.venv/bin/python -m prosperity4bt traders/round5_final.py 5-2 --data ./data --out ./run.log
```

### What `final_pnl` means

Every per-day figure in this repository is one day, run on its own, **starting flat**. No day
inherits the previous day's cash or position. Hand the same command a whole round instead of
a day and it stitches the days end to end, so `final_pnl` becomes the running total:

```
per day:                          whole round in one invocation:
1--2   final_pnl:  95,057         Round 1 day -2:  95,057
1--1   final_pnl:  95,580         Round 1 day -1:  95,580
1-0    final_pnl:  94,589         Round 1 day  0:  94,589
                                  final_pnl:      285,226   <- the sum
```

Where [`results/README.md`](results/README.md) shows a total it is the second kind: the sum
of independent days, not an equity curve anyone could have traded.

### Tick charts

`make backtest` writes one automatically; `make plot` charts the newest run and opens it, or
point `plot_run.py` at a specific log. Each chart is a single self-contained HTML file with
three panels sharing a tick axis: total PnL, PnL per series, and position per series with the
round's limit drawn on it. Positions are reconstructed from our own fills, so that last panel
is a direct check on whether the book ever pushed against a limit.

Round 5's fifty products are grouped into their ten clusters, with a filter above the chart
to isolate one cluster and see its five products against the limit. Ticks are thinned to a
point budget, which is what makes this usable at all: fifty products across ten thousand
ticks is a million points, and charting that raw produces a 20,000 pixel tall figure in a
21 MB page that will hang a browser.

`make visualize` starts the Streamlit visualiser that came with the team environment on the
most recent `.log`. Stop it with Ctrl+C.

---

## The backtester

Every round **replaced** the tradable universe rather than adding to it, and each new
universe brought its own position limits — the binding constraint on everything a market
maker does. A backtester that does not know a product does not refuse to run: it falls back
to a default and produces numbers that look fine and are wrong.

| Rounds | Products | Position limit |
|---|---|--:|
| 1, 2 | `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT` | 80 |
| 3, 4 | `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, plus the `VEV_*` option chain | 200 and 300 |
| 5 | 50 products in 10 groups of 5 | 10 |

All of it now lives in one file, [`prosperity4bt/rounds.py`](prosperity4bt/rounds.py), keyed
by round. Consolidating it turned up four real defects in the tooling, two of which made a
run's output lie about the run: inventory marked to a price of zero on empty books, which
put a spurious -960,764 into round 1 and reported a max drawdown of 1.36 million against a
true 1,607, and a trade history that was not valid JSON, which is why the position panel in
the charts exists now and did not before. Neither changes any final PnL in this repository.

**Full write-up, including what moved and what did not: [`docs/backtester.md`](docs/backtester.md).**

---

## Round 5: 50 products, 10 clusters

Round 5 replaced everything with 50 new products, all limited to 10. Handled one at a time
that is 50 research problems on a competition clock. They came in 10 labelled groups of 5,
so the move was to stop trading products and start trading clusters, spending the research
budget on classifying each cluster rather than tuning any single instrument.

That work is in [`research/notes/`](research/notes): base statistics, autocorrelation at
lags 1, 5 and 10, price ratios with their coefficient of variation, ADF on those ratios,
FFT for dominant periods, cross-correlation and lead-lag. Figures in
[`research/figures/`](research/figures), notebook in
[`research/prosperity_r5_analysis.ipynb`](research/prosperity_r5_analysis.ipynb).

It produced three kinds of cluster, and
[`traders/round5_final.py`](traders/round5_final.py) runs one strategy per cluster:

- **Relationships that held.** TG01 Galaxy Sounds prices each member off a regression
  against a reference instrument, in some cases from a different cluster.
- **Ratios that oscillated without mean-reverting.** TG02 Sleeping Pods oscillated 152 to
  263 points against a spread of 19, so the trade paid, but ADF p-values of 0.11 to 0.52
  said the ratios were not stationary. Traded with a trend filter on top of the skew rather
  than as a pure pair.
- **Structure that was drifting.** TG04 Pebbles, the cluster in the
  [post-mortem below](#how-the-strategies-held-up-out-of-sample).

What changed from round 4 was not the models but where the risk control sits. Limits and
thresholds are declared per cluster in one config block instead of being scattered through
the signal code, clusters whose ratios failed ADF get a trend filter before any
mean-reversion trade fires, and the hard shorts are explicit in that config.

Backtested on the three days that shipped with the round, each run on its own:

| | PnL | Sharpe (ann.) | Max drawdown |
|---|--:|--:|--:|
| Day 5-2 | 292,473 | 74.92 | 28,294 |
| Day 5-3 | 332,886 | 86.52 | 25,694 |
| Day 5-4 | 444,286 | 109.40 | 20,150 |

14.7 times the round 4 PnL on a third of the average drawdown, and the best-looking
backtest of the competition by a wide margin. On the unseen day it scored **62,953**, 249th
worldwide for the round, which is 82% below what those three days predicted. See
[below](#how-the-strategies-held-up-out-of-sample).

The ten cluster strategies are in [`traders/clusters/`](traders/clusters), each as
submitted. Each was also submitted on its own, trading only its five products, so each has
an isolated score. The ten in isolation sum to 81,881 against 83,926 for the combined book:
merging them cost nothing and gained 2.5%, which is the evidence that the decomposition was
a real partition of the problem rather than a convenient one.

---

## The other rounds

One page each, with the strategy, the local backtest and what it was worth out of sample:

| Round | What it was | Official | Backtest mean | Held up? |
|---|---|--:|--:|---|
| [1](docs/rounds/round1.md) | market making two products | 95,348 | 95,075 | yes, **0%** |
| [2](docs/rounds/round2.md) | new products, same shape of problem | 102,858 | 99,661 | yes, **+3%** |
| [3](docs/rounds/round3.md) | two underlyings and a ten-strike option chain | 26,928 | 42,594 | **-37%** |
| [4](docs/rounds/round4.md) | round 3 rewritten, and a sizing failure | 32,771 | 24,225 | **+35%**, noisy |

Two of them carry a lesson that outlived the round. Round 2's first attempt was round 1's
strategy pointed at the new products, and it scored 8,654 against the 102,858 of a strategy
written from round 2's own data — twelve times less, in the same round, under the same
evaluation. And round 4 kept 57% of round 3's PnL on the same instruments while multiplying
the average drawdown by six, which is a sizing failure rather than a signal one.

---

## How the strategies held up out of sample

Prosperity scores you three times, on three different things, and conflating them is easy:

| | Data | Length |
|---|---|---|
| Local backtest | the three days shipped with the round, all visible | 3 full days |
| Practice submission on the site | the **first 10%** of the last of those same days | 1,000 of 10,000 ticks |
| Official round result | the **next day**, never seen | 1 full day |

One thing to get straight before reading any of the numbers, because the day names invite
the opposite conclusion: IMC numbers days continuously across the whole competition rather
than restarting at 1 each round. Round 5 ships days 2, 3 and 4 and is scored on day 5; round
1 ships days -2, -1 and 0 and is scored on day 1. So the **highest-numbered day in any
`data/` folder is the last day you could see, not the day you were scored on**. The scoring
day was never released and is not in this repository. Every "unseen day" figure below comes
from IMC's own evaluation, traceable by submission id in
[`results/official_submissions.md`](results/official_submissions.md), which confirms it by
parsing the submission artefacts: the round 5 final ran 10,000 ticks on day 5, while the
round 5 practice ran 1,000 ticks on day 4.

That also makes the practice submission not an out-of-sample test at all. It re-runs data
you already have, and only a tenth of it. Verified: its log reproduces the local CSV tick for
tick, 1000 of 1000 mid-prices identical, and the reported profit is the raw PnL after 1,000
ticks with no extrapolation.

That leaves the local backtest and the official result as the only comparable pair, and they
are only comparable if the two engines agree. They do. Run on the identical 10% segment the
platform used:

| Round | This backtester | IMC's | Difference |
|---|--:|--:|--:|
| 5 | 83,978 | 83,926 | 0.06% |
| 4 | 44,256 | 44,127 | 0.29% |

So the numbers below are like for like: three visible days against the one unseen day that
counted, same strategy file, engines agreeing to within a third of a percent.

| Round | Visible days | Mean | Unseen day | Change |
|---|---|--:|--:|--:|
| 1 | 95,057 / 95,580 / 94,589 | 95,075 | 95,348 | **0%** |
| 2 | 99,968 / 99,624 / 99,392 | 99,661 | 102,858 | **+3%** |
| 3 | 34,247 / 50,290 / 43,245 | 42,594 | 26,928 | **-37%** |
| 4 | 4,722 / -17,345 / 85,297 | 24,225 | 32,771 | **+35%** |
| 5 | 292,473 / 332,886 / 444,286 | 356,548 | 62,953 | **-82%** |

The ordering is the interesting part, because it is almost exactly the ordering of how much
fitting each strategy did.

Rounds 1 and 2 quote a spread around a fair value and ride a drift. There is nothing in them
estimated from the data beyond a level and a slope, and they reproduce out of sample to
within 3%. Round 3 prices an option chain off a volatility taken as given, and loses 37%.
Round 5 is built on relationships estimated across 50 products, regressions of one
instrument on another, ratio levels, lead-lag, and it gives back 82%.

The in-sample risk numbers point the same way, which is the part that would have been
usable at the time. Rounds 1 and 2 run a max drawdown under 2% of the day's PnL, a Calmar
between 52 and 67, and six days spanning 5.7% from worst to best. Round 5's three days span
52% and rise monotonically, which reads as a strategy improving and is equally consistent
with a strategy fitting.

The research had already flagged why. The Pebbles cluster carried the largest position in
the book, and its own notes show a spread that walks in one direction across all three
visible days rather than oscillating:

```
Day 2  spread_mean=+1937  max=+5194  min=-1015
Day 3  spread_mean=+4328  max=+6361  min=+2409
Day 4  spread_mean=+5831  max=+9050  min=+2399
```

The stationarity tests said the same: ADF p-values of 0.36 to 0.58 on the TG04 ratios, 0.11
to 0.52 on TG02. Not stationary, on the clusters the book leaned on hardest. It was
measured, written down, and then sized as though it had not been.

Two honest caveats. Round 4's visible days range from -17,345 to +85,297, so its +35% is
noise around a mean that means very little. And 62,953 was still good for **249th in the
world that day**, which says the field degraded too and that some of round 5's fall belongs
to the day rather than to the strategy. Separating those two would need other teams'
numbers, which I do not have.

What survives both caveats is the shape: the strategy with the most estimated parameters
produced the best backtest and the worst generalisation, and the evidence that it would was
already sitting in the research notes before the round was submitted.

---

## The manual challenges

One decision per round, scored once, no iteration and no second try. Different enough from
the algorithmic side that they get their own page, one section per round:
**[`manual/README.md`](manual/README.md)**.

Round 2 was an allocation across three levers where one lever paid out on your rank against
every other team, so it was a game against the field. Round 3 was two sealed bids against a
known reserve distribution with a penalty for undercutting the field's average. Round 4 was
an option book to price and size, including three exotics. Round 5 was an allocation under a
quadratic fee.

The manual leg was the weaker half overall, 1290th against 696th on the algorithmic side.

---

## Layout

```
traders/
  round1_final.py .. round5_final.py   one per round, as submitted
  clusters/          the 10 round 5 cluster strategies, as submitted
    later_iterations/  TG01 and TG05 as reworked afterwards
  iterations/        the seven round 1 submissions, and the round 2 carry-over
docs/
  rounds/            rounds 1 to 4, one page each
  backtester.md      what the engine got wrong and what changed
research/            per-cluster statistics, figures, round 5 notebook
manual/              MATLAB for the manual rounds, one folder per round
data/                competition data, rounds 1 to 5, gzipped
results/             local backtests, official scoring, leaderboard screenshots
prosperity4bt/       the backtesting engine
  rounds.py          products and position limits, keyed by round
plot_run.py          tick charts for a run, one self-contained HTML file
visualizer.py        Streamlit charts for a run
```

## Attribution

Prosperity is a team competition and FeynmanKac was three people, so every leaderboard
figure on this page is a team result.

FeynmanKac was one of two teams from BlackSwan Quants. We talked through a lot of strategy
with the other one, Stockastici, over the course of the competition, and their repository is
at [Emaflick/Prosperity-4-Stockastici](https://github.com/Emaflick/Prosperity-4-Stockastici).
Where the two repositories reach similar conclusions about the same products, that is why.
The code here is written by me.

The code is a different matter and worth being precise about. The backtesting engine
(`prosperity4bt/`), `visualizer.py` and `quick_plot.py` are not mine: they come from the
shared environment the team built during the competition and are redistributed here under
their MIT licence, with the changes described above and in [NOTICE.md](NOTICE.md).
Everything under `traders/`, `research/`, `manual/`, `results/` and `docs/` is my own work.

Data belongs to IMC Trading.
