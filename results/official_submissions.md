# Official submission results

These numbers come from IMC's own evaluation, not from the local backtester. Every row is
backed by the submission artefact (`<id>.json` plus its log) produced by the competition
platform. The submission id is included so each figure is traceable.

## Per round

| Round | Submission | Profit (seashells) |
|---|---|--:|
| Tutorial | 94320 | 705 |
| 1 | 272854 | 95,348 |
| 2 | 359813 | 102,858 |
| 3 | 485634 | 26,928 |
| 4 | 542442 | 32,771 |
| 5 | 581571 | 62,953 |

Round 4 and round 5 match the leaderboard screenshots in this folder exactly.

## The out-of-sample haircut

Prosperity lets you submit against a practice evaluation while a round is open, then scores
the final submission on data you have never seen. In rounds 4 and 5 the same file was run
through both. Verified by diff: the practice and final submissions are byte-identical
Python.

| Round | Code | Practice | Final | Change |
|---|---|--:|--:|--:|
| 4 | `traders/round4_trader.py` | 44,127 (sub 536645) | 32,771 (sub 542442) | **-25.7%** |
| 5 | `traders/round5_final.py` | 83,926 (sub 569164) | 62,953 (sub 581571) | **-25.0%** |

Two independent rounds, two different strategies, two different sets of instruments, and
the same 25% haircut to within a percentage point. That number is worth more than either
of the raw PnLs. It is a measurement of how much of the edge was fitted to the days that
were visible, and it is stable enough to be treated as a planning assumption rather than
as bad luck. Anything that looked marginal in practice should have been assumed to be
negative in the final evaluation, and was not.

## Round 5: are the clusters additive?

Each of the ten cluster strategies was also submitted on its own, trading only its own five
products, against the same round 5 evaluation. That gives an isolated result per cluster and
a check on whether the combined book gained or lost anything by merging them.

| Cluster | Submission | Profit | Trader |
|---|---|--:|---|
| TG01 Galaxy Sounds | 562660 | 14,191 | `traders/clusters/trader_TG01.py` |
| TG04 Purification Pebbles | 558820 | 10,845 | `traders/clusters/trader_TG04.py` |
| TG07 Instant Translators | 567043 | 10,796 | `traders/clusters/trader_TG07_v3.py` |
| TG02 Vertical Sleeping Pods | 549521 | 9,527 | `traders/clusters/trader_TG02.py` |
| TG09 Liquid Breath Oxygen Shakes | 564088 | 9,053 | `traders/clusters/trader_TG09_v2.py` |
| TG05 Domestic Robotics | 564983 | 7,561 | `traders/clusters/trader_TG05.py` |
| TG08 Construction Panels | 567699 | 6,713 | `traders/clusters/trader_TG08.py` |
| TG06 UV-Visors | 562535 | 5,887 | `traders/clusters/trader_TG06_v2.py` |
| TG03 Organic Microchip Modules | 560268 | 5,308 | `traders/clusters/trader_TG03_v2.py` |
| TG10 Protein Snack Packs | 568342 | 1,998 | `traders/clusters/trader_TG10_v3.py` |
| **Sum of the ten in isolation** | | **81,881** | |
| **Combined book** | 569164 | **83,926** | `traders/round5_final.py` |

The combined book beats the sum of its parts by 2.5%. Merging ten strategies that share
nothing except a position-limit regime cost nothing and gained slightly, which is the
evidence that the cluster decomposition was a real partition of the problem and not an
arbitrary one. It also says the aggregate result is not carried by an interaction effect:
the ranking of clusters by contribution is stable between the isolated submissions and the
local per-cluster backtest in [`README.md`](README.md).

`traders/clusters/later_iterations/` holds versions of TG01 and TG05 written after their
submissions. They are not the code behind the numbers above.

## Round 1: what seven iterations bought

Round 1 was submitted seven times against the practice evaluation before the round closed.

| Version | Submission | Profit | Change |
|---|---|--:|--:|
| 1 | 167820 | 1,639 | |
| 2 | 169917 | 1,815 | +10.7% |
| 3 | 172252 | 9,383 | **+417%** |
| 4 | 189851 | 9,552 | +1.8% |
| 5 | 211154 | 9,552 | 0.0% |
| 6 | 216211 | 9,890 | +3.5% |
| 7 | 218516 | 9,890 | 0.0% |

One change did everything. Going from version 2 to version 3 meant dropping a fixed
8-tick half-spread quoted symmetrically around a static fair value, and replacing it with
pennying at a minimum edge of 2 while splitting the two products onto separate strategies
instead of one shared config. That is 5.2x. The four iterations after it, which included a
dual-layer quoting scheme and a retuned EMA, produced 5.4% between them, and two of them
returned a result identical to the submission before them down to the last decimal.

The final round 1 submission scored 95,348.
