"""
=============================================================================
REL CHARTS - PLOTLY VISUALS
=============================================================================
PURPOSE : Charts for the relative historical tool. Colours and fonts come
          from theme.py, the same tokens the other valuation tools use.

CHARTS  : 1. Panels   four multiples over the window, each with its P10-P90
                      band, median line, average line, and current marker
          2. Implied  implied price by multiple against the current price

OUTPUT  : Plotly Figure objects.
=============================================================================
"""

import copy

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from theme import COLORS, PLOTLY_LAYOUT
from rel_config import MULTIPLES


def _base(title=None, height=340):
    layout = copy.deepcopy(PLOTLY_LAYOUT)
    if title:
        layout["title"]["text"] = title
    layout["height"] = height
    return layout


# ---------------------------------------------------------------------
# 1. FOUR PANEL MULTIPLE HISTORY
# ---------------------------------------------------------------------
def chart_panels(h1, rows, headline=None):
    """Each multiple over the window, with its own benchmark lines."""
    fig = make_subplots(rows=2, cols=2, subplot_titles=MULTIPLES,
                        vertical_spacing=0.18, horizontal_spacing=0.09)

    for i, m in enumerate(MULTIPLES):
        rr, cc = i // 2 + 1, i % 2 + 1
        s = pd.to_numeric(h1[m], errors="coerce")
        valid = s[np.isfinite(s) & (s > 0)]

        if len(valid) < 10:
            # Plotly menamai sumbu subplot pertama "x" tanpa angka, bukan "x1".
            # Memakai "x1 domain" akan ditolak dan seluruh chart gagal dirender.
            ax_suffix = "" if i == 0 else str(i + 1)
            fig.add_annotation(text="insufficient data",
                               xref=f"x{ax_suffix} domain",
                               yref=f"y{ax_suffix} domain",
                               x=0.5, y=0.5, showarrow=False,
                               font=dict(size=11, color=COLORS["ink_muted"]),
                               row=rr, col=cc)
            continue

        r = rows[m]
        p10, p90 = r["p10"], r["p90"]
        med, avg = r["median"], r["avg"]

        # P10 to P90 band
        if np.isfinite(p10) and np.isfinite(p90):
            fig.add_trace(go.Scatter(
                x=list(s.index) + list(s.index[::-1]),
                y=[p90] * len(s) + [p10] * len(s),
                fill="toself", fillcolor="rgba(169,201,232,0.30)",
                line=dict(width=0), hoverinfo="skip", showlegend=False),
                row=rr, col=cc)

        # Soft fill under the line itself, for visual weight
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, mode="lines", fill="tozeroy",
            fillcolor="rgba(11,31,58,0.06)",
            line=dict(color=COLORS["navy"], width=2),
            name=m, showlegend=False,
            hovertemplate="%{x|%d %b %Y}<br>" + m + ": %{y:,.2f}x<extra></extra>"),
            row=rr, col=cc)

        # Median and average lines: median label pinned to the left edge,
        # average label pinned to the right edge, so the two never collide
        # even when the two benchmarks sit close together in value.
        for val, colr, dash, lbl, anchor_x, xanchor, yshift in [
                (med, COLORS["buy"], "dash", "Median", s.index[0], "left", 9),
                (avg, COLORS["sell"], "dot", "Average", s.index[-1], "right", -11)]:
            if np.isfinite(val):
                fig.add_hline(y=val, line=dict(color=colr, width=1.4, dash=dash),
                              row=rr, col=cc)
                fig.add_annotation(x=anchor_x, y=val, text=f"{lbl} {val:,.2f}x",
                                   showarrow=False, xanchor=xanchor, yanchor="middle",
                                   yshift=yshift, bgcolor="rgba(255,255,255,0.85)",
                                   font=dict(size=10, color=colr, family="Poppins"),
                                   row=rr, col=cc)

        cur_v = float(valid.iloc[-1])
        fig.add_trace(go.Scatter(
            x=[valid.index[-1]], y=[cur_v], mode="markers+text",
            marker=dict(size=10, color=COLORS["navy"], line=dict(color="#fff", width=1.5)),
            text=[f"{cur_v:,.2f}x"], textposition="top left",
            textfont=dict(size=10, color=COLORS["navy"], family="Poppins"),
            showlegend=False, hoverinfo="skip"), row=rr, col=cc)

    layout = _base(None, 600)
    layout.pop("title", None)
    layout["showlegend"] = False
    fig.update_layout(**layout)
    fig.update_xaxes(gridcolor=COLORS["rule"], linecolor=COLORS["rule"],
                     tickfont=dict(size=9))
    fig.update_yaxes(gridcolor=COLORS["rule"], linecolor=COLORS["rule"],
                     tickfont=dict(size=9))

    # Subplot titles as highlighted chips, so P/E, P/BV etc. read as labels
    # rather than plain caption text.
    for ann in fig.layout.annotations[:len(MULTIPLES)]:
        is_head = ann.text == headline
        ann.text = f"  {ann.text}  "
        ann.font = dict(size=12.5, color=COLORS["white"] if is_head else COLORS["navy"],
                        family="Poppins")
        ann.bgcolor = COLORS["navy"] if is_head else COLORS["ice_pale"]
        ann.bordercolor = COLORS["navy"] if is_head else COLORS["rule"]
        ann.borderwidth = 1
        ann.borderpad = 5
        ann.xanchor = "left"
        ann.yshift = 6
    return fig


# ---------------------------------------------------------------------
# 2. IMPLIED PRICE BY MULTIPLE
# ---------------------------------------------------------------------
def chart_implied(rows, price, headline=None):
    """Implied price at average and median, per multiple, against price now."""
    names, at_avg, at_med = [], [], []
    for m in MULTIPLES:
        r = rows[m]
        if not (np.isfinite(r["implied_avg"]) or np.isfinite(r["implied_med"])):
            continue
        names.append(m + (" *" if m == headline else ""))
        at_avg.append(r["implied_avg"] if np.isfinite(r["implied_avg"]) else None)
        at_med.append(r["implied_med"] if np.isfinite(r["implied_med"]) else None)

    if not names:
        return None

    fig = go.Figure()
    fig.add_bar(x=names, y=at_avg, name="At 1Y average",
                marker_color=COLORS["navy"],
                text=[f"{v:,.0f}" if v else "" for v in at_avg],
                textposition="outside", textfont=dict(size=10),
                hovertemplate="%{x} at average: IDR %{y:,.0f}<extra></extra>")
    fig.add_bar(x=names, y=at_med, name="At 1Y median",
                marker_color=COLORS["ice"],
                marker_line=dict(color=COLORS["navy_soft"], width=1),
                text=[f"{v:,.0f}" if v else "" for v in at_med],
                textposition="outside", textfont=dict(size=10),
                hovertemplate="%{x} at median: IDR %{y:,.0f}<extra></extra>")

    if price and np.isfinite(price) and price > 0:
        fig.add_hline(y=price, line=dict(color=COLORS["sell"], width=2, dash="dash"),
                      annotation_text=f"Price now IDR {price:,.0f}",
                      annotation_position="top left",
                      annotation_font=dict(size=11, color=COLORS["sell"]))

    vals = [v for v in at_avg + at_med if v] + [price or 0]
    layout = _base("Implied price if the multiple reverts (IDR per share)", 360)
    layout["barmode"] = "group"
    layout["yaxis"]["range"] = [0, max(vals) * 1.25]
    layout["yaxis"]["title"] = dict(text="IDR per share", font=dict(size=11))
    fig.update_layout(**layout)
    return fig
