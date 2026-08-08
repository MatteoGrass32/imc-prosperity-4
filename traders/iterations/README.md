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

`diff round1_v2.py round1_v3.py` is the one worth reading. Two things change. The quoting
rule goes from a fixed 8-tick half-spread around a static fair value to pennying at a
minimum edge of 2, and the two products stop sharing a config:

```python
# v2: one shared config, quote a fixed distance from fair value
"EMERALDS":          {"fair_value": 10000, "spread": 8, "quote_size": 20},
"ASH_COATED_OSMIUM": {"fair_value": 10000, "spread": 8, "quote_size": 20},
bid_price = math.floor(fv - half_spread - skew)

# v3: one strategy per product, quote just inside the book
"ASH_COATED_OSMIUM": {"fair_value": 10000, "min_edge": 2, "quote_size": 20},
```

That is 5.2x. The four submissions after it, which between them added a dual-layer quoting
scheme, aggressive taking, tiered quotes and a retuned EMA, produced 5.4% in total, and two
of them returned a number identical to the submission before them to the last decimal.

The lesson is not that the later work was bad. It is that the first version was quoting a
spread wide enough that it was rarely the best price, so nothing else mattered until that
was fixed, and once it was fixed the remaining ideas were competing for what little was
left. The final round 1 submission scored 95,348.

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
