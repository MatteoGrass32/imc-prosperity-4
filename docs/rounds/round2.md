# Round 2: same products, and what a strategy is worth once they change

← [back to the README](../../README.md) · [round 1](round1.md) · [round 3](round3.md) · [round 4](round4.md)

New products, same shape of problem. [`traders/round2_final.py`](../../traders/round2_final.py)
scored **102,858** on the unseen day.

The first attempt was the round 1 strategy adapted to the new products,
[`traders/iterations/round2_from_round1.py`](../../traders/iterations/round2_from_round1.py).
It scored **8,654**. Same round, same evaluation, twelve times less. Whatever made round 1
work was a property of round 1's products and did not travel. Rounds 3 and 4 later paid for
the same lesson at a much higher price.

## Backtest

Three visible days, each run on its own and each starting flat:

| Day | PnL | Sharpe (ann.) | Max drawdown | Calmar |
|---|--:|--:|--:|--:|
| `2--1` | 99,968 | 61.58 | 1,494 | 66.9 |
| `2-0` | 99,624 | 57.71 | 1,755 | 56.8 |
| `2-1` | 99,392 | 54.31 | 1,687 | 58.9 |

Together with round 1 these are the steadiest results in the repository by a wide margin:
six days spanning 5.7% from worst to best, a max drawdown under 2% of the day's PnL every
time, and a Calmar between 52 and 67. They are also the two rounds that reproduced out of
sample, which is not a coincidence — see
[the out-of-sample section](../../README.md#how-the-strategies-held-up-out-of-sample).

The same mark-to-market caveat as round 1 applies: 38 ticks on day 1 have an empty book.
Details in [`NOTICE.md`](../../NOTICE.md).

Full local backtests in [`results/README.md`](../../results/README.md). Official scoring,
with submission ids, in
[`results/official_submissions.md`](../../results/official_submissions.md).
