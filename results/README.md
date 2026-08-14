# Backtest results

Every number on this page was produced by the backtester in this repository, on the data
in `data/`, with the commands shown. Nothing is hand-copied from the competition site
except the leaderboard screenshots, which are labelled as such.

All of it is **in sample**: the three days shipped with each round were visible while the
strategy was being written. How these figures compare against the unseen day each round was
actually scored on is in
[`official_submissions.md`](official_submissions.md#the-comparison-that-does-work), and for
round 5 the gap is large.

The day names make that easy to misread, so it is worth stating plainly. IMC numbers days
continuously across the competition instead of restarting at 1 each round, so round 5's
three visible days are numbered 2, 3 and 4 and its scoring day is day 5. **Day 5-4 is the
third training day, not the held-out one.** No table on this page contains the scoring day
of any round: that data was never released and is not in this repository.

Two reading notes on the numbers themselves:

- **Each day is a separate run that starts flat.** No day inherits the previous day's cash
  or position, so a day's PnL is that day alone.
- **A `Total` row is the sum of independent days**, not an equity curve anyone could have
  traded. It happens to equal what the engine reports if you hand it a whole round rather
  than a single day, because that mode stitches the days end to end — see
  [the README](../README.md#what-final_pnl-means).

To reproduce a single run:

```bash
make backtest TRADER=traders/round5_final.py DAY=5-4
```

Full stdout of each run is kept under [`raw/`](raw).

## Rounds 1 and 2: `traders/round1_final.py`, `traders/round2_final.py`

Two products, position limit 80. One is a market maker around a fair value near 10,000, the
other rides a drift of a thousand a day.

| Day | PnL | Sharpe (ann.) | Max drawdown | Calmar |
|---|--:|--:|--:|--:|
| 1--2 | 95,057 | 59.16 | 1,816 | 52.3 |
| 1--1 | 95,580 | 57.14 | 1,601 | 59.7 |
| 1-0 | 94,589 | 53.53 | 1,607 | 58.9 |
| 2--1 | 99,968 | 61.58 | 1,494 | 66.9 |
| 2-0 | 99,624 | 57.71 | 1,755 | 56.8 |
| 2-1 | 99,392 | 54.31 | 1,687 | 58.9 |

These are the steadiest results in the repository by a wide margin: six days spanning 5.7%
from worst to best, with a max drawdown under 2% of the day's PnL every time and a Calmar
between 52 and 67. They are also the two rounds that reproduced out of sample, which is not
a coincidence and is the subject of
[`official_submissions.md`](official_submissions.md#the-comparison-that-does-work).

Worth knowing if you are comparing against anything written earlier: these numbers were
wrong until the mark-to-market fix described in [`../NOTICE.md`](../NOTICE.md). The round 1
and round 2 data contain ticks where the book is empty and the feed reports a mid of 0, and
marking inventory at 0 booked a one-tick loss of nearly a million. Final PnL was never
affected, but this table used to read a max drawdown of 1.36 million and a Sharpe of 0.23.

## Round 5: `traders/round5_final.py`

50 products, position limit 10 on all of them, three days of data.

| Day | PnL | Sharpe (ann.) | Sortino | Max drawdown | Calmar |
|---|--:|--:|--:|--:|--:|
| 5-2 | 292,473 | 74.92 | 0.0694 | 28,294 | 10.34 |
| 5-3 | 332,886 | 86.52 | 0.0805 | 25,694 | 12.96 |
| 5-4 | 444,286 | 109.40 | 0.1022 | 20,150 | 22.05 |
| **Sum of the three** | **1,069,645** | | | | |

All three of these days were visible while the strategy was being written. The day it was
scored on, day 5, is not here and never was; it returned 62,953.

PnL is positive on all three days, drawdown shrinks as PnL grows, and even the weakest day
returns 10x its own max drawdown. This is the behaviour the round 4 book did not have.

### Where the PnL comes from

| Cluster | Day 2 | Day 3 | Day 4 | Total |
|---|--:|--:|--:|--:|
| TG04 Purification Pebbles | 42,306 | 118,007 | 81,655 | **241,968** |
| TG01 Galaxy Sounds | 56,837 | 57,234 | 67,284 | **181,355** |
| TG05 Domestic Robotics | 40,781 | 45,655 | 76,025 | **162,461** |
| TG03 Organic Microchip Modules | 29,553 | 38,615 | 31,596 | **99,764** |
| TG09 Liquid Breath Oxygen Shakes | 40,729 | -1,417 | 42,266 | **81,578** |
| TG02 Vertical Sleeping Pods | 17,437 | 6,714 | 43,063 | **67,214** |
| TG06 UV-Visors | 12,352 | 6,587 | 43,143 | **62,082** |
| TG10 Protein Snack Packs | 17,043 | 23,800 | 19,781 | **60,624** |
| TG07 Instant Translators | 27,571 | 3,420 | 25,603 | **56,594** |
| TG08 Construction Panels | 7,865 | 34,273 | 13,871 | **56,009** |
| **All 50 products** | **292,474** | **332,888** | **444,287** | **1,069,649** |

Two clusters, TG04 and TG01, carry 40% of the book. TG04 is the one where the structure
was strongest and also the one where it was least stable, which is discussed in the main
README.

## Round 4: `traders/round4_trader.py`

Two underlyings plus a 10-strike option chain (position limits 200 and 300).

| Day | PnL | Sharpe (ann.) | Max drawdown | Calmar |
|---|--:|--:|--:|--:|
| 4-1 | 4,722 | 0.77 | 76,578 | 0.06 |
| 4-2 | **-17,345** | **-2.79** | 84,499 | -0.21 |
| 4-3 | 85,297 | 14.11 | 79,599 | 1.07 |
| **Sum of the three** | **72,674** | | | |

The interesting column is the drawdown one. It sits between 76k and 85k on every day,
independent of whether the day made or lost money, and on day 1 it is 16x the PnL. The
book was taking a large, roughly constant amount of risk and being paid for it only
sometimes. The competition agreed: round 4 was the team's worst algorithmic round
(1051st) and the only one where the overall rank moved down.

## Round 3: `traders/round3_trader.py`

Same instruments as round 4, earlier version of the strategy.

| Day | PnL | Sharpe (ann.) | Max drawdown | Calmar |
|---|--:|--:|--:|--:|
| 3-0 | 34,247 | 36.91 | 7,658 | 4.47 |
| 3-1 | 50,290 | 40.03 | 9,116 | 5.52 |
| 3-2 | 43,245 | 19.40 | 22,610 | 1.91 |
| **Sum of the three** | **127,782** | | | |

Worth reading next to round 4. Same market, smaller and steadier PnL, average drawdown
13.1k against 80.2k. The round 4 rewrite kept 57% of the PnL and multiplied the average
drawdown by six.

## Note on position limits

The upstream backtester shipped with round 1 limits only, so anything else silently fell
back to a default of 80. [`prosperity4bt/rounds.py`](../prosperity4bt/rounds.py) now carries
the real limits, and `data.py` and `visualizer.py` both read that one registry: 10 for all
50 round 5 products (round 5 wiki), 200 for the two round 3/4 underlyings and 300 for the
VEV option chain. Without this, round 5 runs are unconstrained and round 3/4 runs are
clipped to a limit that never existed.
