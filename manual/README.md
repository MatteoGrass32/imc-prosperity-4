# Manual rounds

Alongside the algorithmic leg, each round had a manual challenge: a single one-shot
decision, scored once, with no chance to iterate. These are the MATLAB scripts I wrote to
size those decisions instead of guessing them.

## Round 4: pricing an option book and sizing it

The challenge listed eleven contracts on one underlying at 50 with a volatility of 2.51,
quoted two-sided, and asked for a book. Six were vanilla puts and calls across strikes at
a three-week expiry, two were vanillas at two weeks, and three were exotic: a chooser, a
digital put paying 10 below 40, and a down-and-out put struck at 45 that dies if the path
ever touches 35.

**[`MontecarloSim.m`](round4_options/MontecarloSim.m)** prices all eleven under GBM.
1,000 runs of 1,000,000 paths, discretised at four steps per trading day, with
**antithetic variates**: half the normals are drawn, the other half are their negatives, so
the sampling error on the symmetric part of the payoff cancels. The barrier is priced off
the running path minimum rather than the terminal value, which is the whole point of that
contract. Output is a theoretical price against the market mid, and the edge.

**[`AllocazioneOttima.m`](round4_options/AllocazioneOttima.m)** turns those prices into
positions. Deltas come from bump-and-revalue, repricing at 50.1 and 49.9, and the two sets
of paths are built from the **same normals**, so the difference between them is signal and
not Monte Carlo noise. It buys where theo clears the ask by a minimum edge, sells where it
clears the bid, skips otherwise, then hedges the net delta on the underlying, capped at 200
lots, and charges itself the half-spread for doing so. It reports the expected PnL of the
book net of that hedging cost, rather than the gross number.

**[`MonteSim_Interv_Conf.m`](round4_options/MonteSim_Interv_Conf.m)** and
**[`AllocOttima_Interv_Conf90.m`](round4_options/AllocOttima_Interv_Conf90.m)** /
**[`AllocOttima_Interv_Conf95.m`](round4_options/AllocOttima_Interv_Conf95.m)** are the
version that matters. The pricer returns a confidence interval per contract instead of a
point estimate, and the allocator changes its rule accordingly:

```matlab
% before: trade if the point estimate clears the quote
if theos(i) > asks(i) + min_edge

% after: trade only if the whole interval clears the quote
if ci_low(i) > asks(i)
```

Nothing is traded unless the entire interval sits on one side of the market. On this book
the two rules disagree about exactly one contract out of eleven, and it is the right one.
`AC_60_C` prices at 8.7908 against a bid of 8.80, so the point estimate sells it on an edge
of about nine thousandths. Its 95% interval runs to 8.8011, which crosses the bid. The
point estimate was claiming an edge smaller than its own error bar, and the interval rule
drops the trade. Every other decision is unchanged.

What is left is a book of five positions against six skips, and the split is not random.
All six skips are three-week vanillas, quoted tightly enough that no interval clears them.
All three exotics trade, against quotes that were off by 0.30 on the chooser, 0.23 on the
digital, and 18% of the price on the barrier. The two remaining trades are the two-week
vanillas, at 0.12 each. The mispricing sat where the pricing was hard, which is the reason
to build a path-dependent Monte Carlo instead of looking up Black-Scholes.

The 95% variant also swaps the Monte Carlo deltas for closed-form Black-Scholes ones, since
for the vanillas there was no reason to estimate what can be computed exactly.

Figures for both variants are in [`round4_options/figures/`](round4_options/figures).

This is the same idea the algorithmic side of this repository learned the hard way, and it
is worth stating plainly: a point estimate that clears a threshold by less than its own
uncertainty is not an edge. The
[25% out-of-sample haircut](../results/official_submissions.md#the-out-of-sample-haircut)
measured on the algorithmic rounds is what that mistake costs when it is made at scale.

## Round 3: two sealed bids against a known distribution

Counterparties hold reserve prices uniform on 670 to 920 in steps of 5, the product resells
at 920, and you submit two bids. The second bid is penalised by
`((920 - avgB2) / (920 - B2))^3` if it falls below the average second bid of every other
player, which makes it a game against the field rather than against the distribution.

**[`Bid1.m`](round3_bids/Bid1.m)** solves the first bid twice over: once analytically, by
accumulating the probability mass below each candidate and taking the expected value
directly, and once by simulating 10,000 draws of the counterparty pool. The two agree,
which is the only reason to trust either. The file also carries the clarifications
collected before committing, on how the two bids interact and what the penalty applies to.

**[`Bid1and2_Simulation.m`](round3_bids/Bid1and2_Simulation.m)** searches the joint pair.
It grids B1 and B2 over 700 to 900, draws 500 populations of 1,000 counterparties, samples
a distribution for the field's average second bid, and computes the penalty per simulation
rather than once at the mean, since the penalty is convex and averaging the inputs first
would flatter the result.

## Round 5: allocation under a quadratic fee

**[`portafoglio.m`](round5_portfolio/portafoglio.m)** is short because the structure did the
work. The fee on an allocation of `p` percent of budget is `(p/100)^2 * budget`, quadratic,
so it prices concentration directly. The script nets that fee against the gross return of
each of the nine positions and reports the book. The reason it stays small is that once the
fee is quadratic, the interesting decision is how flat to spread rather than what to pick.

## Result

The manual leg was the weaker half of the campaign: 1290th overall against 696th on the
algorithmic side. Round 4 was its best round, 670th, which is also the round with the
most work behind it on this page.
