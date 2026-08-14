# Round 1: market making, and seven submissions

← [back to the README](../../README.md) · [round 2](round2.md) · [round 3](round3.md) · [round 4](round4.md)

Two products, quoting both sides. [`traders/round1_final.py`](../../traders/round1_final.py)
scored **95,348** on the unseen day.

The seven submissions leading to it are in
[`traders/iterations/`](../../traders/iterations/README.md), and their shape is the
interesting part: 1,639, then 1,815, then **9,383**, then 9,552, 9,552, 9,890, 9,890.

One change did it, and the data says why. The two products are not the same kind of object:

| Product | Mean mid | Drift per day |
|---|--:|--:|
| `ASH_COATED_OSMIUM` | ~9,984 | -16.5, -1.0, -6.0 |
| `INTARIAN_PEPPER_ROOT` | 10,483 to 12,474 | +1003.0, +999.5, +1001.5 |

Osmium sits on a fair value near 10,000. Pepper root climbs by a thousand a day, every day,
and ends the third session 30% above where it opened the first. Versions 1 and 2 market made
both of them, pepper root through an EMA-anchored quoter. Quoting a drift like that means
selling into it all day.

Version 3 stopped treating it as a market making problem. Pepper root moved to a
`DirectionalTrendStrategy`, commented in the file as drift exploitation, while osmium stayed
a market maker but went from a fixed 8-tick half-spread to pennying at a minimum edge of 2.
That is 5.2x. The four submissions after it added a dual-layer quoting scheme, aggressive
taking, tiered quotes and a retuned EMA, and produced 5.4% between them, with two returning
a number identical to the submission before them to the last decimal.

The gain was in classifying the instrument, not in tuning the quoter.

## Backtest

Three visible days, each run on its own and each starting flat:

| Day | PnL | Sharpe (ann.) | Max drawdown | Calmar |
|---|--:|--:|--:|--:|
| `1--2` | 95,057 | 59.16 | 1,816 | 52.3 |
| `1--1` | 95,580 | 57.14 | 1,601 | 59.7 |
| `1-0` | 94,589 | 53.53 | 1,607 | 58.9 |

A max drawdown between 1,601 and 1,816 puts the Calmar in the high fifties, the tightest
result in this repository. That matters for the
[out-of-sample section](../../README.md#how-the-strategies-held-up-out-of-sample), where
round 1 reproduces to within 0%.

These numbers were wrong until the mark-to-market fix described in
[`NOTICE.md`](../../NOTICE.md): 35 ticks on day 0 have an empty book and a reported mid of 0,
and marking inventory there booked a spurious -960,764. Final PnL never moved, but max
drawdown used to read 1,356,627 and the annualised Sharpe 0.23.

Full local backtests in [`results/README.md`](../../results/README.md). Official scoring,
with submission ids, in
[`results/official_submissions.md`](../../results/official_submissions.md).
