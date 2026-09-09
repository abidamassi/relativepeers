"""
=============================================================================
RELATIVE HISTORICAL - STREAMLIT APPLICATION
=============================================================================
PURPOSE : Web front end for relative valuation against a company's own
          multiple history. The sidebar holds only a ticker box and a run
          button, every other parameter is fixed in rel_config.py.

CACHING : Network work is cached per ticker for an hour.

RUN     : streamlit run rel_app.py
=============================================================================
"""

import copy
import warnings

import numpy as np
import pandas as pd
import streamlit as st

warnings.filterwarnings("ignore")

from rel_config import REL_CONFIG, MULTIPLES, DRIVER_OF, DISCLAIMER
from theme import (COLORS, FLAG_COLOR, inject_css, pill, metric_strip, callout,
                   render_table, numbered_list)
from rel_charts import chart_panels, chart_implied
from rel_main import fetch_relative_bundle, analyze_relative, multiple_table

AUTHOR = "Abida Massi Armand"

st.set_page_config(page_title="Relative Historical",
                   page_icon="chart_with_upwards_trend",
                   layout="wide",
                   initial_sidebar_state="expanded")
inject_css()


# =====================================================================
# VERSION-SAFE RENDER HELPERS
# =====================================================================
def show_chart(fig):
    if fig is None:
        return None
    cfg = {"displayModeBar": False}
    try:
        return st.plotly_chart(fig, width="stretch", config=cfg)
    except TypeError:
        return st.plotly_chart(fig, use_container_width=True, config=cfg)


# =====================================================================
# CACHED DATA LAYER
# =====================================================================
@st.cache_data(show_spinner=False, ttl=3600)
def load_bundle(code):
    return fetch_relative_bundle(code)


# =====================================================================
# FORMATTERS
# =====================================================================
def f_idr(v, dp=0):
    return f"IDR {v:,.{dp}f}" if v is not None and np.isfinite(v) else "n/a"


def f_tn(v):
    return f"IDR {v/1e12:,.2f} tn" if v is not None and np.isfinite(v) else "n/a"


def f_pct(v, dp=1, sign=False):
    if v is None or not np.isfinite(v):
        return "n/a"
    return f"{v*100:+.{dp}f}%" if sign else f"{v*100:.{dp}f}%"


def f_x(v, dp=2):
    return f"{v:.{dp}f}x" if v is not None and np.isfinite(v) else "n/a"


# =====================================================================
# SIDEBAR
# =====================================================================
with st.sidebar:
    st.markdown(
        f'<div style="padding:.2rem 0 1rem 0;">'
        f'<div style="font-size:1.05rem;font-weight:600;color:#fff;letter-spacing:-.01em;">'
        f'Relative Historical</div>'
        f'<div style="font-size:.7rem;color:{COLORS["ice"]};letter-spacing:.1em;'
        f'text-transform:uppercase;margin-top:.15rem;">Own-history multiples, IDX</div>'
        f'</div>', unsafe_allow_html=True)

    st.markdown("---")

    def _uppercase_ticker():
        st.session_state.ticker_in = st.session_state.ticker_in.upper()

    ticker_in = st.text_input("Ticker", value="AMMN", max_chars=4, key="ticker_in",
                              on_change=_uppercase_ticker,
                              help="Enter the IDX code only, max 4 characters. "
                                   "The .JK suffix is added automatically.")
    try:
        run = st.button("Run analysis", width="stretch")
    except TypeError:
        run = st.button("Run analysis", use_container_width=True)


# =====================================================================
# STATE
# =====================================================================
if "rel_result" not in st.session_state:
    st.session_state.rel_result = None

if run and ticker_in.strip():
    with st.spinner("Downloading prices and financial statements"):
        bundle = copy.deepcopy(load_bundle(ticker_in.strip()))
        st.session_state.rel_result = analyze_relative(ticker_in.strip(), bundle=bundle)

r = st.session_state.rel_result


def render_disclaimer():
    st.markdown(
        f'<div class="disclaimer">'
        f'<div class="sig">Disclaimer On &nbsp;|&nbsp; {AUTHOR}</div>'
        f'{DISCLAIMER}</div>', unsafe_allow_html=True)


def render_flags(flags):
    if flags.has_issue:
        rows = "".join(
            f'<div class="flagrow">'
            f'<div class="flagtag" style="background:{FLAG_COLOR.get(lv, COLORS["miss"])}">{lv}</div>'
            f'<div class="flagfield">{fd}</div><div class="flagnote">{nt}</div></div>'
            for lv, fd, nt in flags.items)
        st.markdown(f'<div class="flagbox">{rows}</div>', unsafe_allow_html=True)
    else:
        callout("No data quality issues detected.")


# =====================================================================
# EMPTY STATE
# =====================================================================
if r is None:
    st.markdown('<div class="masthead"><p class="eyebrow">Equity research tooling</p>'
                '<h1>Relative Historical</h1>'
                '<div class="sub">Trailing multiples measured against a company\'s '
                'own one-year history, not against peers.</div></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="empty"><h3>No company loaded</h3>'
                '<p>Enter an IDX ticker in the sidebar and select Run analysis.</p>'
                '</div>', unsafe_allow_html=True)
    render_disclaimer()
    st.stop()


d = r["d"]

# =====================================================================
# MASTHEAD
# =====================================================================
st.markdown(
    f'<div class="masthead"><p class="eyebrow">Relative historical valuation</p>'
    f'<h1>{d.get("ticker","")} &nbsp;&middot;&nbsp; {d.get("name","Unnamed")}</h1>'
    f'<div class="sub">{d.get("sector","n/a")} &nbsp;|&nbsp; '
    f'{d.get("industry","n/a")}</div></div>', unsafe_allow_html=True)

if not r["ok"]:
    st.markdown(f'<div class="callout"><b class="gate-no">CANNOT PROCEED.</b> '
                f'{r.get("error", "Insufficient data")}</div>',
                unsafe_allow_html=True)
    pill("01", "Data quality warnings")
    render_flags(d["flags"])
    render_disclaimer()
    st.stop()


cur = r["cur"]
rows = r["multiples"]
head = r["headline"]
verdict = r["verdict"]

metric_strip([
    ("Last price", f_idr(cur["Price"])),
    ("Market cap", f_tn(cur["MktCap"])),
    ("Enterprise value", f_tn(cur["EV"])),
    ("Price date", str(d.get("price_date", "n/a"))),
    ("Window", f"{REL_CONFIG['window_years']:.0f} year"),
])

if d.get("fx") is not None:
    callout(f"<b>Currency conversion applied.</b> Statements are reported in "
            f"{d['fin_ccy']} while the share price is quoted in {d['px_ccy']}. "
            f"Every statement line has been converted at the <b>daily</b> exchange "
            f"rate before multiples were computed, not at a single spot rate, so "
            f"currency moves do not leak into the multiple series.",
            gap_above=True)


# =====================================================================
# VERDICT
# =====================================================================
pill("01", "Headline verdict")

if not verdict["valid"]:
    callout(f"<b>No headline multiple.</b> {verdict['reason']} Check Data quality "
            f"warnings below — a multiple is usually excluded for failing sector "
            f"relevance, a non-positive driver, or too few observations.")
else:
    up_lo, up_hi = verdict["upside_low"], verdict["upside_high"]
    vcolor = (COLORS["ink_muted"] if verdict["review_required"]
              else COLORS["buy"] if (np.isfinite(up_hi) and up_hi > 0)
              else COLORS["sell"])
    label = "Review required" if verdict["review_required"] else verdict["headline"]

    lo, hi = verdict["implied_low"], verdict["implied_high"]
    price = verdict["price"]
    span = max(hi - lo, 1e-9)
    pos = float(np.clip((price - lo) / span, 0, 1)) * 100

    st.markdown(f"""
<div class="verdict">
  <div class="row">
    <div>
      <div class="lab">Headline multiple</div>
      <div class="rating" style="color:{vcolor};font-size:2.1rem">{label}</div>
    </div>
    <div>
      <div class="lab">Implied price range</div>
      <div class="big">{f_idr(lo)} &ndash; {f_idr(hi)}</div>
      <div class="small">At the 1Y average and median</div>
    </div>
    <div>
      <div class="lab">Price now</div>
      <div class="big">{f_idr(price)}</div>
      <div class="small">Percentile {verdict['percentile']:.0f} of the 1Y range</div>
    </div>
    <div>
      <div class="lab">Implied upside</div>
      <div class="big" style="color:{vcolor}">{f_pct(up_lo, 1, True)} to {f_pct(up_hi, 1, True)}</div>
      <div class="small">{verdict['driver']} moved {f_pct(verdict['driver_change'], 1, True)} over the window</div>
    </div>
  </div>
  <div class="scale">
    <div class="lab">Where the current price sits inside the implied range</div>
    <div class="track">
      <div class="fill" style="left:0%;width:{pos:.1f}%"></div>
      <div class="mark" style="left:{pos:.1f}%"></div>
    </div>
    <div class="ends"><span>{f_idr(lo)}</span><span>{f_idr(hi)}</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

    if verdict["review_required"]:
        callout("<b>Review required.</b> The implied move is large enough that it "
                "more often signals a data or structural issue than a genuine "
                "mispricing. Check Data quality warnings below, and cross-check "
                "with a peer comparison, SOTP, or a cash flow based method before "
                "drawing a conclusion.")

    callout(f"<b>How to read this.</b> The implied price is what the share would be "
            f"worth if {verdict['headline']} returned to its own one-year benchmark "
            f"<b>while the driver stays where it is today</b>. Where a multiple looks "
            f"cheap but the underlying driver is falling, the discount may be a "
            f"correct derating rather than an opportunity. Over the window "
            f"{verdict['driver']} moved {f_pct(verdict['driver_change'], 1, True)}.",
            gap_above=True)


# =====================================================================
# DATA QUALITY
# =====================================================================
pill("02", "Data quality warnings",
     "Read these before relying on any figure below.")
render_flags(d["flags"])


# =====================================================================
# R3 - MULTIPLES
# =====================================================================
avg_kind = "harmonic" if REL_CONFIG["use_harmonic"] else "arithmetic"
pill("03", "Multiples against own history",
     f"One-year window, {avg_kind} average of the company's own multiple history.")
render_table(multiple_table(rows, cur), index_label="Multiple", highlight_index=head)
show_chart(chart_implied(rows, cur["Price"], head))


# =====================================================================
# R3 - PANELS
# =====================================================================
pill("04", "Multiple history",
     "Shaded band is the P10 to P90 range within the window. The marker is the "
     "latest reading.")
show_chart(chart_panels(r["h1"], rows, head))


# =====================================================================
# LIMITATIONS
# =====================================================================
pill("05", "Model limitations")
numbered_list([
    "This compares a company against its own past, not against peers. If the "
    "whole sector rerated, the benchmark moves with it and the signal "
    "disappears.",
    "The implied price assumes the driver stays exactly where it is. In "
    "practice a multiple usually falls because the market expects the driver "
    "to fall, so a cheap looking multiple can be a correct derating rather "
    "than an opportunity.",
    "A one-year window is short. It cannot distinguish a cyclical trough from "
    "a structural rerating, and it will not contain a full earnings cycle for "
    "a commodity or property issuer.",
    "Statement items are held flat between reporting dates, so multiples step "
    "on release days. Part of the measured volatility comes from the "
    "reporting calendar rather than from price action.",
    "Share count is forward filled. Where a rights issue or buyback occurred "
    "inside the window, multiples before and after are not strictly "
    "comparable.",
    "Mean reversion is an assumption, not a law. A multiple can stay above or "
    "below its own average for years.",
    "Data comes from yfinance and has not been reconciled against audited "
    "financial statements or IDX filings.",
])

render_disclaimer()
