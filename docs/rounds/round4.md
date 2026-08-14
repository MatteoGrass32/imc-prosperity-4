# Round 4: the same instruments, rewritten, and a risk problem

← [back to the README](../../README.md) · [round 1](round1.md) · [round 2](round2.md) · [round 3](round3.md)

[`traders/round4_trader.py`](../../traders/round4_trader.py) is the [round 3](round3.md)
strategy rewritten on the same instruments. Scored **32,771** on the unseen day, the team's
worst algorithmic round at 1051st, and the only round where the overall rank moved down.

## Backtest

Three visible days, each run on its own and each starting flat:

| Day | PnL | Sharpe (ann.) | Max drawdown | Calmar |
|---|--:|--:|--:|--:|
| `4-1` | 4,722 | 0.77 | 76,578 | 0.06 |
| `4-2` | **-17,345** | **-2.79** | 84,499 | -0.21 |
| `4-3` | 85,297 | 14.11 | 79,599 | 1.07 |

The PnL is not really the problem. The column next to it is: drawdown sits between 76k and
85k on every day regardless of the outcome, and on day 1 it is 16 times the PnL. Against
round 3 on the same instruments, the rewrite kept 57% of the PnL and multiplied the average
drawdown by six. The book was putting up the same large risk every day and being paid for it
once in three.

That is a sizing failure rather than a signal failure, and it is worth separating from the
question of whether the strategy generalised. On that second question round 4 does better
than this section suggests — see
[the out-of-sample section](../../README.md#how-the-strategies-held-up-out-of-sample), with
the caveat that visible days ranging from -17,345 to +85,297 make its mean nearly
meaningless.

Full local backtests in [`results/README.md`](../../results/README.md). Official scoring,
with submission ids, in
[`results/official_submissions.md`](../../results/official_submissions.md).
