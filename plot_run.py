"""Tick charts for a backtest run.

Reads a .log produced by prosperity4bt and writes one self-contained HTML file with
total PnL, PnL per series and position per series over the ticks of the run.

    python plot_run.py                       # newest .log in the working directory
    python plot_run.py run_5-2.log           # a specific run
    python plot_run.py run_5-2.log --open    # and open it in the browser

Round 5 trades 50 products in 10 labelled clusters, which is more series than any chart
can carry at once. The page therefore opens on one line per cluster and takes a filter
above the chart to drill into a single cluster's five products. Rounds 3 and 4 group the
`VEV_*` chain the same way; rounds 1 and 2 have two products and no grouping to do.

Colours come from the validated categorical palette: eight hues in fixed order, assigned
by entity rather than by rank, so a series keeps its colour when the filter changes. Past
eight, identity is carried by hue plus dash rather than by a ninth generated hue. Three of
the light-mode hues sit below 3:1 against the surface, so the page also ships the table
view underneath the chart.

Why this exists rather than quick_plot.py: that script builds one subplot per product with
no downsampling, which on a round 5 run is 50 stacked panels, a million points and a 20,000
pixel tall figure in a 21 MB page. Browsers do not enjoy that. Here everything shares an
axis and the ticks are thinned to a budget.
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
from plotly.offline import get_plotlyjs
from plotly.subplots import make_subplots

from prosperity4bt.rounds import ALL_LIMITS, ROUND_5_GROUPS

POINT_BUDGET = 60_000  # per panel, across all series

# Validated categorical palette, eight hues in fixed order. Both modes are selected
# rather than flipped: the dark column is the same hues stepped for the dark surface.
# Checked with the data-viz validator on the adjacent pairlist (lines): worst CVD
# dE 9.1 light / 8.4 dark, worst normal-vision dE 19.6 / 19.3.
SERIES = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
              "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
    "dark": ["#3987e5", "#d95926", "#199e70", "#c98500",
             "#d55181", "#008300", "#9085e9", "#e66767"],
}

CHROME = {
    "light": {"surface": "#fcfcfb", "page": "#f9f9f7", "primary": "#0b0b0b",
              "secondary": "#52514e", "muted": "#898781", "grid": "#e1e0d9",
              "axis": "#c3c2b7", "border": "rgba(11,11,11,0.10)"},
    "dark": {"surface": "#1a1a19", "page": "#0d0d0d", "primary": "#ffffff",
             "secondary": "#c3c2b7", "muted": "#898781", "grid": "#2c2c2a",
             "axis": "#383835", "border": "rgba(255,255,255,0.10)"},
}


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


def product_groups(products: list[str]) -> dict[str, list[str]]:
    """Map each run's products onto the groups the round actually traded in.

    Round 5 shipped its 50 products as 10 labelled clusters and the strategy is written
    one per cluster, so that is the grouping worth charting. Rounds 3 and 4 have two
    underlyings plus an option chain. Rounds 1 and 2 have two products and each is its
    own group, which leaves the chart exactly as it was before this existed.
    """
    member_of = {f"{group}_{variant}": (index, group)
                 for index, (group, variants) in enumerate(ROUND_5_GROUPS.items(), start=1)
                 for variant in variants}

    if any(product in member_of for product in products):
        groups: dict[str, list[str]] = {}
        for product in products:
            index, group = member_of.get(product, (99, "OTHER"))
            groups.setdefault(f"TG{index:02d} {group}", []).append(product)
        return dict(sorted(groups.items()))

    chain = sorted(p for p in products if p.startswith("VEV_"))
    if chain:
        groups = {p: [p] for p in products if not p.startswith("VEV_")}
        groups["VEV option chain"] = chain
        return groups

    return {product: [product] for product in products}


def thinned_grid(ticks: list[int], series_count: int) -> list[int]:
    """Keep every nth tick so one panel stays inside the point budget."""
    step = max(1, math.ceil(len(ticks) * max(series_count, 1) / POINT_BUDGET))
    return ticks[::step]


def colour(index: int, mode: str) -> tuple[str, str | None]:
    """Hue and dash for a series, keyed by its position in a fixed entity order.

    Never cycles a ninth hue: past the eighth slot identity is hue plus dash, so two
    series that share a hue are still told apart without relying on colour alone.
    """
    palette = SERIES[mode]
    return palette[index % len(palette)], None if index < len(palette) else "dash"


def build(prices: pd.DataFrame, trades: pd.DataFrame) -> tuple[go.Figure, dict, list[dict]]:
    products = sorted(prices["product"].unique())
    groups = product_groups(products)
    positions = own_positions(trades)
    has_positions = not positions.empty

    ticks = sorted(prices["timestamp"].unique())
    grid = thinned_grid(ticks, len(products))

    pnl = (prices.pivot_table(index="timestamp", columns="product",
                              values="profit_and_loss", aggfunc="last")
           .reindex(ticks).ffill().fillna(0.0).reindex(grid))

    if has_positions:
        positions = positions.reindex(ticks).ffill().fillna(0.0).reindex(grid)
        for product in products:
            if product not in positions.columns:
                positions[product] = 0.0

    rows = 3 if has_positions else 2
    titles = ["Total PnL of the selection", "PnL by series"] + (
        ["Position by series"] if rows == 3 else [])
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, subplot_titles=titles,
                        vertical_spacing=0.07)

    # One view per filter option: the overview, then one per group. Every trace for every
    # view is built once and the filter only flips visibility, so switching never refetches
    # and never repaints a series that stayed on screen.
    views = [{"label": f"All {len(groups)} groups", "members": None}]
    views += [{"label": label, "members": members} for label, members in groups.items()]

    traces: list[dict] = []
    limits_per_view: list[list[int]] = []

    for view in views:
        if view["members"] is None:
            entities = [(label, members) for label, members in groups.items()]
        else:
            entities = [(product, [product]) for product in view["members"]]

        total = pnl[[p for _, members in entities for p in members]].sum(axis=1)
        traces.append({"row": 1, "view": view["label"], "name": "Total", "index": 0,
                       "x": grid, "y": total.tolist(), "legend": False})

        for index, (name, members) in enumerate(entities):
            traces.append({"row": 2, "view": view["label"], "name": name, "index": index,
                           "x": grid, "y": pnl[members].sum(axis=1).tolist(), "legend": True})
            if has_positions:
                traces.append({"row": 3, "view": view["label"], "name": name, "index": index,
                               "x": grid, "y": positions[members].sum(axis=1).tolist(),
                               "legend": False})

        # A limit line only means something where a series is one product. Summing five
        # products' positions into a cluster line has no limit of its own, so the overview
        # draws none unless its groups happen to be single products (rounds 1 and 2).
        singles = {members[0] for _, members in entities if len(members) == 1}
        limits_per_view.append(sorted({ALL_LIMITS[p] for p in singles if p in ALL_LIMITS}))

    first_view = views[0]["label"]
    for trace in traces:
        line_colour, dash = colour(trace["index"], "light")
        fig.add_trace(
            go.Scatter(
                x=trace["x"], y=trace["y"], name=trace["name"], mode="lines",
                line=dict(color=line_colour, width=2, dash=dash),
                visible=trace["view"] == first_view,
                showlegend=trace["legend"] and trace["view"] == first_view,
                legendgroup=trace["name"],
                hovertemplate=f"{trace['name']}<br>%{{y:,.0f}}<extra></extra>",
            ),
            row=trace["row"], col=1,
        )

    all_limits = sorted({limit for limits in limits_per_view for limit in limits})
    if has_positions:
        for limit in all_limits:
            for sign in (1, -1):
                fig.add_hline(y=sign * limit, line_dash="dot", line_width=1,
                              line_color=CHROME["light"]["axis"],
                              visible=limit in limits_per_view[0], row=3, col=1)

    fig.update_layout(height=330 * rows, hovermode="x unified", showlegend=True,
                      margin=dict(t=56, l=64, r=24, b=48),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                  xanchor="left", x=0))
    fig.update_xaxes(title_text="tick", row=rows, col=1)
    fig.update_yaxes(title_text="seashells", row=1, col=1)
    fig.update_yaxes(title_text="seashells", row=2, col=1)
    if has_positions:
        fig.update_yaxes(title_text="units", row=3, col=1)

    filters = {
        "views": [view["label"] for view in views],
        "visible": [[trace["view"] == view["label"] for trace in traces] for view in views],
        "legend": [[trace["legend"] and trace["view"] == view["label"] for trace in traces]
                   for view in views],
        "colours": {mode: [colour(trace["index"], mode)[0] for trace in traces]
                    for mode in ("light", "dark")},
        "shapes": [[limit in limits for limit in all_limits for _ in (1, -1)]
                   for limits in limits_per_view],
    }
    return fig, filters, table_rows(groups, pnl, positions if has_positions else None)


def table_rows(groups: dict[str, list[str]], pnl: pd.DataFrame,
               positions: pd.DataFrame | None) -> list[dict]:
    """The table-view twin of the chart.

    Three of the light-mode hues sit below 3:1 against the chart surface, which the
    palette documents as needing relief: either visible direct labels or a table. Fifty
    end-labels would be unreadable, so this is the table.
    """
    rows = []
    for index, (label, members) in enumerate(groups.items()):
        final = float(pnl[members].sum(axis=1).iloc[-1])
        peak = (float(positions[members].sum(axis=1).abs().max())
                if positions is not None else float("nan"))
        rows.append({"label": label, "products": len(members), "pnl": final, "peak": peak,
                     "colour": colour(index, "light")[0],
                     "dash": colour(index, "light")[1] is not None})
    return sorted(rows, key=lambda row: row["pnl"], reverse=True)


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root {{ color-scheme: light dark; }}
body {{ margin: 0; background: {light[page]}; color: {light[primary]};
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
.wrap {{ max-width: 1180px; margin: 0 auto; padding: 28px 20px 56px; }}
h1 {{ font-size: 19px; margin: 0 0 4px; font-weight: 600; }}
.sub {{ color: {light[secondary]}; font-size: 14px; margin: 0 0 20px; }}
.sub b {{ font-weight: 600; color: {light[primary]}; font-variant-numeric: tabular-nums; }}
.filters {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
  margin: 0 0 14px; }}
label {{ font-size: 13px; color: {light[secondary]}; }}
select {{ font: inherit; font-size: 14px; padding: 6px 10px; border-radius: 7px;
  border: 1px solid {light[axis]}; background: {light[surface]};
  color: {light[primary]}; }}
.card {{ background: {light[surface]}; border: 1px solid {light[border]};
  border-radius: 12px; padding: 8px 8px 4px; overflow-x: auto; }}
details {{ margin-top: 22px; }}
summary {{ cursor: pointer; font-size: 14px; color: {light[secondary]}; }}
table {{ border-collapse: collapse; margin-top: 12px; font-size: 14px;
  font-variant-numeric: tabular-nums; }}
th, td {{ text-align: right; padding: 7px 14px;
  border-bottom: 1px solid {light[grid]}; }}
th:first-child, td:first-child {{ text-align: left; }}
th {{ color: {light[secondary]}; font-weight: 600; }}
.swatch {{ display: inline-block; width: 10px; height: 10px; border-radius: 3px;
  margin-right: 8px; vertical-align: middle; }}
.swatch.dash {{ border-radius: 0; height: 4px; width: 14px; }}
.note {{ color: {light[muted]}; font-size: 13px; margin-top: 18px; }}
@media (prefers-color-scheme: dark) {{
  body {{ background: {dark[page]}; color: {dark[primary]}; }}
  .sub {{ color: {dark[secondary]}; }} .sub b {{ color: {dark[primary]}; }}
  label, summary, th {{ color: {dark[secondary]}; }}
  select {{ background: {dark[surface]}; color: {dark[primary]};
    border-color: {dark[axis]}; }}
  .card {{ background: {dark[surface]}; border-color: {dark[border]}; }}
  th, td {{ border-bottom-color: {dark[grid]}; }}
  .note {{ color: {dark[muted]}; }}
}}
</style></head><body>
<div class="wrap">
  <h1>__TITLE__</h1>
  <p class="sub">__SUBTITLE__</p>
  <div class="filters">
    <label for="view">Show</label>
    <select id="view">__OPTIONS__</select>
  </div>
  <div class="card"><div id="chart"></div></div>
  <details open>
    <summary>Table view — final PnL and peak absolute position per group</summary>
    __TABLE__
  </details>
  <p class="note">__NOTE__</p>
</div>
<script>__PLOTLYJS__</script>
<script>
const FIG = __FIG__, F = __FILTERS__;
const CHROME = __CHROME__;
const dark = () => window.matchMedia('(prefers-color-scheme: dark)').matches;

function theme() {{
  const c = dark() ? CHROME.dark : CHROME.light;
  Plotly.restyle('chart', {{'line.color': F.colours[dark() ? 'dark' : 'light']}});
  const shapes = {{}};
  (FIG.layout.shapes || []).forEach((_, k) => {{
    shapes['shapes[' + k + '].line.color'] = c.axis;
  }});
  Plotly.relayout('chart', Object.assign(shapes, {{
    'paper_bgcolor': c.surface, 'plot_bgcolor': c.surface,
    'font.color': c.secondary, 'xaxis.gridcolor': c.grid, 'xaxis2.gridcolor': c.grid,
    'xaxis3.gridcolor': c.grid, 'yaxis.gridcolor': c.grid, 'yaxis2.gridcolor': c.grid,
    'yaxis3.gridcolor': c.grid, 'xaxis.linecolor': c.axis, 'xaxis2.linecolor': c.axis,
    'xaxis3.linecolor': c.axis, 'yaxis.linecolor': c.axis, 'yaxis2.linecolor': c.axis,
    'yaxis3.linecolor': c.axis, 'xaxis.zerolinecolor': c.axis,
    'yaxis.zerolinecolor': c.axis, 'yaxis2.zerolinecolor': c.axis,
    'yaxis3.zerolinecolor': c.axis
  }}));
}}

Plotly.newPlot('chart', FIG.data, FIG.layout, {{responsive: true, displaylogo: false}})
  .then(() => {{
    theme();
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', theme);
    document.getElementById('view').addEventListener('change', (e) => {{
      const i = +e.target.value;
      Plotly.restyle('chart', {{visible: F.visible[i], showlegend: F.legend[i]}});
      if (F.shapes[i].length) {{
        const up = {{}};
        F.shapes[i].forEach((v, k) => {{ up['shapes[' + k + '].visible'] = v; }});
        Plotly.relayout('chart', up);
      }}
    }});
  }});
</script>
</body></html>
"""


def render(path: Path, fig: go.Figure, filters: dict, rows: list[dict],
           title: str, subtitle: str, note: str) -> None:
    options = "".join(
        f'<option value="{i}">{label}</option>' for i, label in enumerate(filters["views"]))

    head = ("<table><thead><tr><th>Group</th><th>Products</th>"
            "<th>Final PnL</th><th>Peak |position|</th></tr></thead><tbody>")
    body = "".join(
        f'<tr><td><span class="swatch{" dash" if row["dash"] else ""}" '
        f'style="background:{row["colour"]}"></span>{row["label"]}</td>'
        f'<td>{row["products"]}</td><td>{row["pnl"]:,.0f}</td>'
        f'<td>{"" if row["peak"] != row["peak"] else format(row["peak"], ",.0f")}</td></tr>'
        for row in rows)

    page = PAGE.format(light=CHROME["light"], dark=CHROME["dark"])
    figure = json.loads(fig.to_json())
    for key, value in (("__TITLE__", title), ("__SUBTITLE__", subtitle),
                       ("__OPTIONS__", options), ("__TABLE__", head + body + "</tbody></table>"),
                       ("__NOTE__", note), ("__FIG__", json.dumps(figure)),
                       ("__FILTERS__", json.dumps(filters)),
                       ("__CHROME__", json.dumps(CHROME)),
                       ("__PLOTLYJS__", get_plotlyjs())):
        page = page.replace(key, value)
    path.write_text(page, encoding="utf-8")


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

    fig, filters, rows = build(prices, trades)
    name = Path(log).stem
    render(
        out, fig, filters, rows,
        title=name,
        subtitle=(f"{products} products in {len(filters['views']) - 1} groups &middot; "
                  f"{ticks:,} ticks &middot; final PnL <b>{final:,.0f}</b>"),
        note=("This day was visible while the strategy was being written. Ticks are thinned "
              "to a point budget, so a line is a sample of the path, not every tick of it."),
    )
    print(f"  wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")

    if args.open:
        webbrowser.open(out.resolve().as_uri())


if __name__ == "__main__":
    main()
