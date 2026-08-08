"""Tick charts for a backtest run.

Reads a .log produced by prosperity4bt and writes one self-contained HTML file with
PnL, positions and prices over the ticks of the run.

    python plot_run.py                       # newest .log in the working directory
    python plot_run.py run_5-2.log           # a specific run
    python plot_run.py run_5-2.log --open    # and open it in the browser

Why this exists rather than quick_plot.py: that script builds one subplot per product
with no downsampling, which on a round 5 run is 50 stacked panels, a million points and a
20,000 pixel tall figure in a 21 MB page. Browsers do not enjoy that. Here everything
shares an axis, the ticks are thinned to a budget, and the result is written to a file
instead of being pushed straight at a browser tab.
"""

import argparse
import glob
import io
import json
import math
import os
import webbrowser
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from prosperity4bt.rounds import ALL_LIMITS

POINT_BUDGET = 60_000  # per chart, across all products


def newest_log() -> str:
    logs = glob.glob("*.log")
    if not logs:
        raise SystemExit("No .log file here. Run a backtest first, for example: make backtest")
    return max(logs, key=os.path.getctime)


def read_log(path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    content = Path(path).read_text(encoding="utf-8")

    if "Activities log:" not in content:
        raise SystemExit(f"{path} has no activities log in it.")

    activities = content.split("Activities log:")[-1].split("Trade History:")[0].strip()
    prices = pd.read_csv(io.StringIO(activities), sep=";", on_bad_lines="skip", engine="python")
    prices.columns = prices.columns.str.strip()
    prices = prices[prices["product"] != "product"]
    for column in ("timestamp", "mid_price", "profit_and_loss"):
        prices[column] = pd.to_numeric(prices[column], errors="coerce")
    prices = prices.dropna(subset=["timestamp", "product"])

    trades = pd.DataFrame(columns=["timestamp", "symbol", "quantity", "buyer", "seller"])
    if "Trade History:" in content:
        raw = content.split("Trade History:")[-1].strip()
        try:
            parsed = json.loads(raw)
            if parsed:
                trades = pd.DataFrame(parsed)
        except json.JSONDecodeError as error:
            # Older runs were written with a trailing comma per trade object and cannot be
            # parsed. Charts still work, minus the position panel.
            print(f"  note: trade history is not valid JSON ({error.msg}), skipping positions")

    return prices, trades


def own_positions(trades: pd.DataFrame) -> pd.DataFrame:
    """Running position per product, from our own fills."""
    if trades.empty:
        return pd.DataFrame()

    signed = trades.copy()
    signed["signed"] = 0
    signed.loc[signed["buyer"] == "SUBMISSION", "signed"] = signed["quantity"]
    signed.loc[signed["seller"] == "SUBMISSION", "signed"] = -signed["quantity"]
    signed = signed[signed["signed"] != 0]
    if signed.empty:
        return pd.DataFrame()

    per_tick = signed.groupby(["timestamp", "symbol"])["signed"].sum().unstack(fill_value=0)
    return per_tick.cumsum()


def thin(frame: pd.DataFrame, products: int) -> pd.DataFrame:
    """Keep every nth tick so a chart stays inside the point budget."""
    ticks = frame.index.nunique() if frame.index.name == "timestamp" else frame["timestamp"].nunique()
    step = max(1, math.ceil(ticks * max(products, 1) / POINT_BUDGET))
    if step == 1:
        return frame
    if frame.index.name == "timestamp":
        return frame.iloc[::step]
    return frame[frame["timestamp"].isin(sorted(frame["timestamp"].unique())[::step])]


def build(prices: pd.DataFrame, trades: pd.DataFrame, title: str) -> go.Figure:
    products = sorted(prices["product"].unique())
    positions = own_positions(trades)

    rows = 3 if not positions.empty else 2
    titles = ["Total PnL", "PnL by product"] + (["Position by product"] if rows == 3 else [])
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, subplot_titles=titles,
                        vertical_spacing=0.06)

    total = prices.groupby("timestamp")["profit_and_loss"].sum().to_frame("pnl")
    total.index.name = "timestamp"
    total = thin(total, 1)
    fig.add_trace(go.Scatter(x=total.index, y=total["pnl"], name="Total",
                             line=dict(color="#2563eb", width=2)), row=1, col=1)

    thinned = thin(prices, len(products))
    for product in products:
        one = thinned[thinned["product"] == product]
        fig.add_trace(go.Scatter(x=one["timestamp"], y=one["profit_and_loss"], name=product,
                                 legendgroup=product, showlegend=False,
                                 hovertemplate=f"{product}<br>%{{y:,.0f}}<extra></extra>"),
                      row=2, col=1)

    if rows == 3:
        thinned_positions = thin(positions, len(positions.columns))
        for product in thinned_positions.columns:
            fig.add_trace(go.Scatter(x=thinned_positions.index, y=thinned_positions[product],
                                     name=product, legendgroup=product, showlegend=False,
                                     hovertemplate=f"{product}<br>%{{y:.0f}}<extra></extra>"),
                          row=3, col=1)
        limits = {ALL_LIMITS.get(p) for p in thinned_positions.columns}
        limits.discard(None)
        for limit in limits:
            for sign in (1, -1):
                fig.add_hline(y=sign * limit, line_dash="dot", line_color="red", opacity=0.35,
                              row=3, col=1)

    fig.update_layout(height=340 * rows, title_text=title, hovermode="x unified",
                      showlegend=False, margin=dict(t=80, l=60, r=30, b=50))
    fig.update_xaxes(title_text="tick", row=rows, col=1)
    fig.update_yaxes(title_text="seashells", row=1, col=1)
    fig.update_yaxes(title_text="seashells", row=2, col=1)
    if rows == 3:
        fig.update_yaxes(title_text="units", row=3, col=1)
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Tick charts for a prosperity4bt run.")
    parser.add_argument("log", nargs="?", help="log file (default: newest in this directory)")
    parser.add_argument("--out", help="output HTML (default: plots/<log name>.html)")
    parser.add_argument("--open", action="store_true", help="open the result in a browser")
    args = parser.parse_args()

    log = args.log or newest_log()
    prices, trades = read_log(log)

    products = prices["product"].nunique()
    ticks = prices["timestamp"].nunique()
    final = prices[prices["timestamp"] == prices["timestamp"].max()]["profit_and_loss"].sum()
    print(f"{log}: {products} products, {ticks:,} ticks, final PnL {final:,.0f}")

    out = Path(args.out or Path("plots") / (Path(log).stem + ".html"))
    out.parent.mkdir(parents=True, exist_ok=True)
    figure = build(prices, trades, f"{Path(log).stem}  |  {products} products  |  PnL {final:,.0f}")
    figure.write_html(out, include_plotlyjs="inline")
    print(f"  wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")

    if args.open:
        webbrowser.open(out.resolve().as_uri())


if __name__ == "__main__":
    main()
