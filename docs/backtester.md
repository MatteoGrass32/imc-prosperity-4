# The backtester, and why every round needed a new one

← [back to the README](../README.md)

This was the recurring cost of the competition and it is worth being explicit about, because
the strategy code is shaped by it.

Every round replaced the tradable universe. Not added to it, replaced it. Round 5 said so
outright: you can no longer trade products from previous rounds. And each new universe came
with its own position limits, which are the binding constraint on everything a market maker
does. A backtester that does not know a product does not refuse to run. It falls back to a
default limit and produces numbers that look fine and are wrong.

There were three universes across the five rounds:

| Rounds | Products | Position limit |
|---|---|--:|
| 1, 2 | `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT` | 80 |
| 3, 4 | `HYDROGEL_PACK`, `VELVETFRUIT_EXTRACT`, plus the `VEV_*` option chain | 200 and 300 |
| 5 | 50 products in 10 groups of 5 | 10 |

During the competition, moving between them meant editing the engine, and the edits were
easy to get wrong or forget. In this repository that is consolidated into one file,
[`prosperity4bt/rounds.py`](../prosperity4bt/rounds.py), which holds every product and limit
keyed by round. Selecting a round is now the `DAY` argument and nothing else. Adding a
sixth round would mean one dict.

## Four defects in the tooling

Two about limits:

- The engine shipped with the **tutorial** products, `EMERALDS` and `TOMATOES`, which appear
  in no round 1 to 5 dataset. Every product that was actually traded fell through to the
  default of 80. That is correct for rounds 1 and 2 by coincidence, far too loose for round
  5, where the real limit is 10, and far too tight for rounds 3 and 4, where it is 200 and
  300. Round 5 backtests ran effectively unconstrained and rounds 3 and 4 ran clipped.
- `visualizer.py` kept its **own second copy** of the limits, also tutorial-only, with a
  fallback of 20. The red inventory lines were therefore drawn at 20 in every round of the
  competition, against true limits of 80, 200, 300 and 10. Both files now read the one
  registry, so they cannot disagree again.

And two worse ones, both of which made a run's output lie about the run:

- **Inventory was marked to a price of zero whenever the book was empty.** The round 1 and
  round 2 data contain ticks with no bids and no asks at all, 35 of them on round 1 day 0,
  and the feed reports a mid price of 0 there. Marking 80 units of pepper root at 0 books a
  one-tick loss of **-960,764** in a day that ends at +94,589. Final PnL survives it, because
  the last tick has a real price, but everything path-dependent does not: max drawdown read
  **1,356,627** against a true **1,607**, and annualised Sharpe read **0.23** against a true
  **53.5**. Round 1 looked like a wild ride and is in fact the steadiest thing in this
  repository. There is no price at those ticks, so the engine now carries the last real one.
- **The trade history was not valid JSON.** Every trade object was written with a trailing
  comma, so `json.loads` rejected the whole block and nothing could read our own fills back
  out of a run. That is why the position panel in the charts exists now and did not before.

Rounds 3, 4 and 5 have no empty books, so none of their numbers move. Verified by re-running
them before and after: 85,297 and a 79,599 drawdown on round 4 day 3, 292,473 and 28,294 on
round 5 day 2, identical either way. No PnL reported anywhere in this repository changes,
because the round 5 book self-limits to 10 internally and was never relying on the engine to
stop it. What changes is that the risk numbers are now right, and that round 1 and round 2
have a risk profile at all.

## Provenance

The engine itself is not mine. It is the environment my team built during the competition,
vendored under its MIT licence with those changes plus a repaired `requirements.txt`, which
was missing four packages the engine imports and without which it does not start. Details in
[NOTICE.md](../NOTICE.md). Round 5 was also run against a separate Rust backtester,
[GeyzsoN/prosperity_rust_backtester](https://github.com/GeyzsoN/prosperity_rust_backtester),
which is not reproduced here.
