# Backtest results

Every number on this page was produced by the backtester in this repository, on the data
in `data/`, with the commands shown. Nothing is hand-copied from the competition site
except the leaderboard screenshots, which are labelled as such.

All of it is **in sample**: the three days shipped with each round were visible while the
strategy was being written. How these figures compare against the unseen day each round was
actually scored on is in
[`official_submissions.md`](official_submissions.md#the-comparison-that-does-work), and for
round 5 the gap is large.

To reproduce a single run:

```bash
make backtest TRADER=traders/round5_final.py DAY=5-4
```

Full stdout of each run is kept under [`raw/`](raw).

## Round 5: `traders/round5_final.py`

50 products, position limit 10 on all of them, three days of data.

| Day | PnL | Sharpe (ann.) | Sortino | Max drawdown | Calmar |
|---|--:|--:|--:|--:|--:|
| 5-2 | 292,473 | 74.92 | 0.0694 | 28,294 | 10.34 |
| 5-3 | 332,886 | 86.52 | 0.0805 | 25,694 | 12.96 |
| 5-4 | 444,286 | 109.40 | 0.1022 | 20,150 | 22.05 |
| **Total** | **1,069,645** | | | | |

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
| **Total** | **72,674** | | | |

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
| **Total** | **127,782** | | | |

Worth reading next to round 4. Same market, smaller and steadier PnL, average drawdown
13.1k against 80.2k. The round 4 rewrite kept 57% of the PnL and multiplied the average
drawdown by six.

## Note on position limits

The upstream backtester shipped with round 1 limits only, so anything else silently fell
back to a default of 80. `prosperity4bt/data.py` now carries the real limits: 10 for all
50 round 5 products (round 5 wiki), 200 for the two round 3/4 underlyings and 300 for the
VEV option chain. Without this, round 5 runs are unconstrained and round 3/4 runs are
clipped to a limit that never existed.
