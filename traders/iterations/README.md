# Iteration history

Kept because the shape of these two sequences is more informative than either endpoint.
Every profit figure is from IMC's own evaluation; submission ids are in
[`../../results/official_submissions.md`](../../results/official_submissions.md).

## Round 1, seven submissions

| File | Profit | Change |
|---|--:|--:|
| [`round1_v1.py`](round1_v1.py) | 1,639 | |
| [`round1_v2.py`](round1_v2.py) | 1,815 | +10.7% |
| [`round1_v3.py`](round1_v3.py) | 9,383 | **+417%** |
| [`round1_v4.py`](round1_v4.py) | 9,552 | +1.8% |
| [`round1_v5.py`](round1_v5.py) | 9,552 | 0.0% |
| [`round1_v6.py`](round1_v6.py) | 9,890 | +3.5% |
| [`round1_v7.py`](round1_v7.py) | 9,890 | 0.0% |

`diff round1_v2.py round1_v3.py` is the one worth reading, and the data explains it. The
two products behave nothing alike:

| Product | Mean mid | Drift per day (days -2, -1, 0) |
|---|--:|--:|
| `ASH_COATED_OSMIUM` | ~9,984 | -16.5, -1.0, -6.0 |
| `INTARIAN_PEPPER_ROOT` | 10,483 to 12,474 | +1003.0, +999.5, +1001.5 |

Osmium oscillates around a fair value near 10,000. Pepper root goes up by a thousand a day
with almost no variation, opening at 9,998 on the first day and closing at 13,000 on the
third.

Versions 1 and 2 market made both, pepper root through an EMA-anchored quoter, which against
a drift that size means selling into it for the whole session. Version 3 changed the
classification rather than the parameters:

```python
# v2 routing: both products are market making problems
"ASH_COATED_OSMIUM":    MarketMakingStrategy,      # fixed 8-tick half-spread
"INTARIAN_PEPPER_ROOT": EMAMarketMakingStrategy,

# v3 routing: one of them is not
"ASH_COATED_OSMIUM":    MarketMakingStrategy,      # now pennying at min_edge 2
"INTARIAN_PEPPER_ROOT": DirectionalTrendStrategy,  # "DIRECTIONAL TREND RIDER (Drift Exploitation)"
```

v2 also still routed the tutorial products, `EMERALDS` and `TOMATOES`, which appear in no
round 1 dataset. v3 dropped them.

That is 5.2x. The four submissions after it, which between them added a dual-layer quoting
scheme, aggressive taking, tiered quotes and a retuned EMA, produced 5.4% in total, and two
of them returned a number identical to the submission before them to the last decimal.

The later work was not bad work. It was tuning a quoter after the only decision that
mattered had already been made, which was noticing that one of the two products should not
have been quoted at all. The final round 1 submission scored 95,348.

Two files, `round1_v2.py` and `round1_v5.py`, had a stray leading space on line 1 in the
archived copies, which makes them fail to parse. Removed here. The submitted versions
obviously ran, since they have results.

## Round 2, and what carrying a strategy over is worth

Round 2 introduced new products. The first attempt was the round 1 strategy adapted to
them, [`round2_from_round1.py`](round2_from_round1.py), which scored **8,654**. The
strategy written for round 2 from its own data,
[`../round2_final.py`](../round2_final.py), scored **102,858**.

Twelve times, for the same round and the same evaluation. Whatever made round 1 work was a
property of round 1's products, not a technique that travelled. This is the cheap version of
the lesson that rounds 3 and 4 later paid full price for.
