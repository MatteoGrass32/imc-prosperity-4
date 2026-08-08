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

## What each submission was actually scored on

Three different evaluations, and they are easy to confuse:

| | Data | Length |
|---|---|---|
| Local backtest | the three days shipped with the round, all visible | 3 full days |
| Practice submission | the **first 10%** of the last of those same days | 1,000 of 10,000 ticks |
| Official round result | the **next day**, never seen | 1 full day |

Checked rather than assumed. Parsing `activitiesLog` out of each submission artefact:

| Submission | Day scored | Unique ticks | Fraction of a day |
|---|--:|--:|--:|
| 218516 (round 1 practice) | 0 | 1,000 | 10% |
| 272854 (round 1 final) | 1 | 10,000 | 100% |
| 359813 (round 2 final) | 2 | 10,000 | 100% |
| 485634 (round 3 final) | 3 | 10,000 | 100% |
| 536645 (round 4 practice) | 3 | 1,000 | 10% |
| 542442 (round 4 final) | 4 | 10,000 | 100% |
| 569164 (round 5 practice) | 4 | 1,000 | 10% |
| 581571 (round 5 final) | 5 | 10,000 | 100% |

Every round ships three days and is scored on the fourth. The practice submission re-runs
the last day you already have and stops a tenth of the way in: comparing its mid-prices
against the local CSV gives 1000 identical values out of 1000. The reported profit is the
raw PnL at the last tick of the run, with no scaling, confirmed by summing the
`profit_and_loss` column at the final timestamp.

So a practice submission is a smoke test on visible data, not an out-of-sample result, and
practice against final is not a like-for-like comparison: different day, and ten times the
duration.

## The comparison that does work

The local backtester and IMC's engine agree closely enough to be used interchangeably. Run
on the identical 10% segment the platform scored:

| Round | Local | IMC | Difference |
|---|--:|--:|--:|
| 5 | 83,978 | 83,926 | 0.06% |
| 4 | 44,256 | 44,127 | 0.29% |

Which makes three visible days against the one unseen day that counted a fair comparison:

| Round | Visible days, backtested locally | Mean | Unseen day, official | Change |
|---|---|--:|--:|--:|
| 1 | 95,057 / 95,580 / 94,589 | 95,075 | 95,348 | **0%** |
| 2 | 99,968 / 99,624 / 99,392 | 99,661 | 102,858 | **+3%** |
| 3 | 34,247 / 50,290 / 43,245 | 42,594 | 26,928 | **-37%** |
| 4 | 4,722 / -17,345 / 85,297 | 24,225 | 32,771 | **+35%** |
| 5 | 292,473 / 332,886 / 444,286 | 356,548 | 62,953 | **-82%** |

Discussed in the main [README](../README.md#how-the-strategies-held-up-out-of-sample). The
short version is that the ordering tracks how much each strategy estimated from the data:
the two rounds that quote around a fair value reproduce out of sample, and the round built
on fitted cross-sectional relationships gives back four fifths of its backtest.

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

The final round 1 submission scored 95,348. The code for all seven is in
[`../traders/iterations/`](../traders/iterations/README.md).

## Round 2: what the round 1 strategy was worth once the products changed

| Attempt | Submission | Profit |
|---|---|--:|
| Round 1 strategy adapted to the new products | 275149 | 8,654 |
| Written for round 2 from its own data | 359813 | **102,858** |

Same round, same evaluation, twelve times the result. The edge was a property of round 1's
products rather than a technique that carried over, which is the cheapest possible version
of the lesson that rounds 3 and 4 later paid for at full price.
