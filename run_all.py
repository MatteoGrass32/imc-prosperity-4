"""Backtest every round on every day it shipped, then chart each run.

    python run_all.py                # everything
    python run_all.py --rounds 4 5   # a subset
    python run_all.py --no-plots     # numbers only

Writes logs to runs/ and charts to plots/, both gitignored, and prints a summary table
comparing each round against the official result it was scored on.

A full pass is fifteen runs, takes about two minutes, and leaves roughly 350 MB behind:
270 MB of logs and 80 MB of charts. Round 5 is most of both, since each of its days is
36 MB of market data and produces a 40 MB log. `make clean` removes all of it.
"""

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

ROUNDS = {
    1: ("traders/round1_final.py", ["1--2", "1--1", "1-0"]),
    2: ("traders/round2_final.py", ["2--1", "2-0", "2-1"]),
    3: ("traders/round3_trader.py", ["3-0", "3-1", "3-2"]),
    4: ("traders/round4_trader.py", ["4-1", "4-2", "4-3"]),
    5: ("traders/round5_final.py", ["5-2", "5-3", "5-4"]),
}

# What IMC scored the same file on, on the unseen day after the ones above.
OFFICIAL = {1: 95_348, 2: 102_858, 3: 26_928, 4: 32_771, 5: 62_953}

METRICS = ("final_pnl", "annualized_sharpe", "max_drawdown_abs")


def run_one(python: str, trader: str, day: str, log: Path) -> dict[str, float]:
    log.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [python, "-m", "prosperity4bt", trader, day, "--data", "./data", "--out", str(log)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        raise SystemExit(f"backtest failed for {trader} on {day}:\n  " + "\n  ".join(tail))

    out = {}
    for metric in METRICS:
        found = re.search(rf"{metric}:\s*(-?[\d,\.]+)", result.stdout)
        out[metric] = float(found.group(1).replace(",", "")) if found else float("nan")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rounds", nargs="+", type=int, choices=sorted(ROUNDS), default=sorted(ROUNDS))
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()

    python = sys.executable
    started = time.time()
    per_round: dict[int, list[float]] = {}

    for round_num in args.rounds:
        trader, days = ROUNDS[round_num]
        print(f"\nRound {round_num}  ({trader})")
        pnls = []
        for day in days:
            log = Path("runs") / f"run_{day}.log"
            begin = time.time()
            metrics = run_one(python, trader, day, log)
            pnls.append(metrics["final_pnl"])
            print(f"  {day:<6} PnL {metrics['final_pnl']:>12,.0f}   "
                  f"Sharpe {metrics['annualized_sharpe']:>8.2f}   "
                  f"maxDD {metrics['max_drawdown_abs']:>10,.0f}   "
                  f"({time.time() - begin:.0f}s)")
            if not args.no_plots:
                subprocess.run([python, "plot_run.py", str(log),
                                "--out", f"plots/{day}.html"], check=True)
        per_round[round_num] = pnls

    print("\n" + "=" * 78)
    print(f"{'Round':>5}  {'mean of the days you can see':>28}  {'official, unseen day':>20}  {'change':>8}")
    print("-" * 78)
    for round_num, pnls in per_round.items():
        mean = sum(pnls) / len(pnls)
        official = OFFICIAL[round_num]
        change = 100 * (official - mean) / abs(mean) if mean else float("nan")
        print(f"{round_num:>5}  {mean:>28,.0f}  {official:>20,}  {change:>7.0f}%")
    print("=" * 78)
    print("The middle column is in sample: those days were visible while the strategy was")
    print("being written. See results/official_submissions.md for why that gap is the")
    print("interesting number and what it is not.")
    print(f"\nDone in {time.time() - started:.0f}s.")
    if not args.no_plots:
        print("Charts in plots/. Open any of them in a browser.")


if __name__ == "__main__":
    main()
