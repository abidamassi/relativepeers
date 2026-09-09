"""
=============================================================================
THEME - DESIGN TOKENS AND CUSTOM STYLING
=============================================================================
PURPOSE : Single source of truth for colours, typography, and CSS. Every
          visual decision in the app derives from the tokens defined here,
          so the palette can be changed in one place.

TOKENS  : Navy and ice blue base, Poppins typeface, pill section labels,
          consultant-report layout discipline.

OUTPUT  : COLORS dict, PLOTLY_LAYOUT dict, and inject_css().
=============================================================================
"""

import streamlit as st

# ---------------------------------------------------------------------
# COLOUR TOKENS
# ---------------------------------------------------------------------
COLORS = {
    "navy":        "#0B1F3A",   # primary, headers and verdict band
    "navy_mid":    "#14304F",   # secondary surfaces
    "navy_soft":   "#2C4A6B",   # borders and muted text on light ground
    "ice":         "#A9C9E8",   # accent, chart primary
    "ice_pale":    "#E4EEF7",   # card background
    "ice_faint":   "#F4F8FC",   # page alternate ground
    "white":       "#FFFFFF",
    "ink":         "#1A2733",   # body text
    "ink_muted":   "#63748A",   # captions and secondary labels
    "rule":        "#D6E2EE",   # hairline dividers
    "buy":         "#1E8F5F",
    "sell":        "#C0392B",
    "hold":        "#B08D57",
    "warn":        "#D98B2B",
    "miss":        "#8A94A6",
    "orange":      "#FF7A1A",   # accent, run-analysis action
    "orange_dark": "#E36A0C",
}

RATING_COLOR = {
    "BUY": COLORS["buy"],
    "SELL": COLORS["sell"],
    "HOLD": COLORS["hold"],
    "N/A": COLORS["ink_muted"],
}

FLAG_COLOR = {
    "MISSING": COLORS["miss"],
    "ZERO":    COLORS["warn"],
    "WARN":    COLORS["warn"],
}

# ---------------------------------------------------------------------
# PLOTLY BASE LAYOUT
# ---------------------------------------------------------------------
PLOTLY_LAYOUT = dict(
    font=dict(family="Poppins, sans-serif", size=12, color=COLORS["ink"]),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=48, b=10),
    hoverlabel=dict(font=dict(family="Poppins, sans-serif", size=12)),
    title=dict(font=dict(size=14, color=COLORS["navy"]), x=0, xanchor="left"),
    xaxis=dict(gridcolor=COLORS["rule"], zerolinecolor=COLORS["rule"],
               linecolor=COLORS["rule"], tickfont=dict(size=11)),
    yaxis=dict(gridcolor=COLORS["rule"], zerolinecolor=COLORS["rule"],
               linecolor=COLORS["rule"], tickfont=dict(size=11)),
    legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1,
                font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
)


def inject_css():
    """Load Poppins and apply the full stylesheet."""
    st.markdown(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">

<style>
:root {{
  --navy:{COLORS['navy']}; --navy-mid:{COLORS['navy_mid']}; --navy-soft:{COLORS['navy_soft']};
  --ice:{COLORS['ice']}; --ice-pale:{COLORS['ice_pale']}; --ice-faint:{COLORS['ice_faint']};
  --ink:{COLORS['ink']}; --ink-muted:{COLORS['ink_muted']}; --rule:{COLORS['rule']};
  --orange:{COLORS['orange']}; --orange-dark:{COLORS['orange_dark']};
  --radius:16px; --radius-sm:10px;
}}

html, body, [class*="css"], .stApp, button, input, textarea, select {{
  font-family:'Poppins',sans-serif !important;
}}
.stApp {{ background:{COLORS['white']}; color:var(--ink); }}
.block-container {{ padding-top:2.0rem; padding-bottom:3rem; max-width:1180px; }}
#MainMenu, footer {{ visibility:hidden; }}
/* Header dibuat transparan dan dipipihkan, BUKAN visibility:hidden. Header
   menampung tombol panah buka/tutup sidebar (data-testid collapsedControl).
   Menyembunyikan header total membuat tombol itu ikut hilang, sehingga
   sidebar yang sudah di-collapse tidak bisa dibuka lagi. */
header[data-testid="stHeader"] {{
  background:rgba(0,0,0,0) !important;
  height:2.6rem !important;
}}
header[data-testid="stHeader"] * {{ visibility:visible !important; }}
button[data-testid="stBaseButton-headerNoPadding"],
div[data-testid="stDecoration"] {{ visibility:visible !important; }}

/* ---------- SIDEBAR ---------- */
section[data-testid="stSidebar"] {{ background:var(--navy); }}
section[data-testid="stSidebar"] * {{ color:{COLORS['white']} !important; }}
section[data-testid="stSidebar"] .stSlider label,
section[data-testid="stSidebar"] .stTextInput label {{
  font-size:.72rem !important; font-weight:600 !important;
  letter-spacing:.09em; text-transform:uppercase; color:var(--ice) !important;
}}
section[data-testid="stSidebar"] input {{
  background:var(--navy-mid) !important; border:1px solid var(--navy-soft) !important;
  color:{COLORS['white']} !important; font-weight:700 !important; letter-spacing:.1em;
  text-transform:uppercase; border-radius:8px !important;
}}
/* Run-analysis sits directly under the ticker box: both stretch to the same
   sidebar width, and a small top margin separates the two instead of the
   button touching the input. */
section[data-testid="stSidebar"] .stTextInput,
section[data-testid="stSidebar"] .stButton {{ width:100%; }}
section[data-testid="stSidebar"] .stButton {{ margin-top:.55rem; }}
section[data-testid="stSidebar"] .stButton button {{
  background:var(--orange); color:{COLORS['white']} !important; border:0; width:100%;
  font-weight:700; letter-spacing:.09em; text-transform:uppercase;
  font-size:.8rem; padding:.72rem 0; border-radius:8px;
  box-shadow:0 4px 14px rgba(255,122,26,.32);
  transition:background .15s ease, box-shadow .15s ease;
}}
section[data-testid="stSidebar"] .stButton button:hover {{
  background:var(--orange-dark); box-shadow:0 6px 18px rgba(255,122,26,.4);
}}
section[data-testid="stSidebar"] hr {{ border-color:var(--navy-soft); margin:1.1rem 0; }}

/* ---------- TYPOGRAPHY ---------- */
.eyebrow {{
  font-size:.68rem; font-weight:600; letter-spacing:.16em; text-transform:uppercase;
  color:var(--ink-muted); margin:0 0 .25rem 0;
}}
.masthead {{
  border-bottom:2px solid var(--navy); padding-bottom:.7rem; margin-bottom:1.4rem;
}}
.masthead h1 {{
  font-size:1.85rem; font-weight:600; color:var(--navy); margin:0; letter-spacing:-.015em;
}}
.masthead .sub {{ font-size:.9rem; color:var(--ink-muted); margin-top:.15rem; }}

/* Pill section label: the structural device carrying section number + name */
.pill {{
  display:inline-flex; align-items:center; gap:.55rem;
  background:var(--navy); color:{COLORS['white']};
  padding:.34rem .95rem; border-radius:100px;
  font-size:.74rem; font-weight:600; letter-spacing:.1em; text-transform:uppercase;
  margin:2.1rem 0 .65rem 0;
}}
.pill .num {{
  background:var(--ice); color:var(--navy); border-radius:100px;
  padding:.02rem .46rem; font-size:.66rem; font-weight:700; letter-spacing:.04em;
}}
.pill-note {{ font-size:.8rem; color:var(--ink-muted); margin:0 0 .9rem 0; }}

/* ---------- METRIC STRIP ---------- */
.mstrip {{
  display:flex; flex-wrap:wrap; gap:0; border:1px solid var(--rule);
  border-radius:var(--radius-sm); overflow:hidden;
  box-shadow:0 1px 3px rgba(11,31,58,.05);
}}
.mcell {{ flex:1 1 0; min-width:132px; padding:.78rem .9rem; border-right:1px solid var(--rule); background:var(--ice-faint); }}
.mcell:last-child {{ border-right:0; }}
.mcell .k {{ font-size:.64rem; font-weight:600; letter-spacing:.1em; text-transform:uppercase; color:var(--ink-muted); }}
.mcell .v {{ font-size:1.02rem; font-weight:600; color:var(--navy); margin-top:.18rem; }}

/* ---------- VERDICT BAND (signature element) ---------- */
.verdict {{
  background:linear-gradient(155deg, var(--navy) 0%, var(--navy-mid) 100%);
  border-radius:var(--radius); padding:1.5rem 1.7rem; margin:.5rem 0 .3rem 0;
  box-shadow:0 8px 24px rgba(11,31,58,.18);
}}
/* Equal-width columns so the four fields sit flush left, flush right, and
   evenly spaced in between, rather than bunching by content width.
   align-items:start pins every "lab" caption to the same top line — with
   align-items:end the taller Headline Multiple value (2.1rem) pushed its
   caption higher than the other three columns. */
.verdict .row {{ display:grid; grid-template-columns:repeat(4, 1fr); align-items:start; gap:1.6rem 1.6rem; }}
.verdict .rating {{ font-size:2.5rem; font-weight:700; line-height:1; letter-spacing:-.02em; overflow-wrap:break-word; }}
.verdict .lab {{ font-size:.64rem; font-weight:600; letter-spacing:.14em; text-transform:uppercase; color:var(--ice); margin-bottom:.3rem; }}
.verdict .big {{ font-size:1.5rem; font-weight:600; color:{COLORS['white']}; line-height:1; overflow-wrap:break-word; }}
.verdict .small {{ font-size:.78rem; color:var(--ice); margin-top:.35rem; }}
@media (max-width:820px) {{ .verdict .row {{ grid-template-columns:repeat(2, 1fr); gap:1.4rem 1.6rem; }} }}
@media (max-width:480px) {{
  .verdict {{ padding:1.25rem 1.1rem; }}
  .verdict .row {{ grid-template-columns:1fr; gap:1.1rem; }}
  .verdict .rating {{ font-size:1.9rem; }}
  .verdict .big {{ font-size:1.25rem; }}
}}

/* Scale showing where market price sits inside the bear-bull range */
.scale {{ margin-top:1.25rem; }}
.scale .track {{ position:relative; height:6px; background:var(--navy-soft); border-radius:100px; }}
.scale .fill {{ position:absolute; height:6px; background:var(--ice); border-radius:100px; }}
.scale .mark {{ position:absolute; top:-6px; width:2px; height:18px; background:{COLORS['white']}; }}
.scale .ends {{ display:flex; justify-content:space-between; font-size:.66rem; color:var(--ice); margin-top:.42rem; letter-spacing:.05em; }}

/* ---------- FLAG PANEL ---------- */
.flagbox {{ border:1px solid var(--rule); border-left:4px solid {COLORS['warn']}; border-radius:var(--radius-sm); background:var(--ice-faint); padding:.9rem 1.1rem; }}
.flagrow {{ display:flex; gap:.7rem; padding:.32rem 0; border-bottom:1px solid var(--rule); font-size:.82rem; }}
.flagrow:last-child {{ border-bottom:0; }}
.flagtag {{ flex:0 0 66px; font-size:.6rem; font-weight:700; letter-spacing:.08em; text-align:center; padding:.16rem 0; border-radius:100px; height:fit-content; color:{COLORS['white']}; }}
.flagfield {{ flex:0 0 168px; font-weight:600; color:var(--navy); }}
.flagnote {{ flex:1 1 auto; color:var(--ink-muted); }}

/* ---------- CALLOUTS ---------- */
.callout {{ border-left:3px solid var(--ice); background:var(--ice-pale); padding:.75rem 1.05rem; border-radius:0 var(--radius-sm) var(--radius-sm) 0; font-size:.84rem; margin:.5rem 0; }}
.callout.callout-gap {{ margin-top:1.3rem; }}
.callout b {{ color:var(--navy); }}
.gate-ok {{ color:{COLORS['buy']}; font-weight:600; }}
.gate-no {{ color:{COLORS['sell']}; font-weight:600; }}

/* ---------- TABLES ---------- */
[data-testid="stDataFrame"] {{ border:1px solid var(--rule); border-radius:var(--radius-sm); overflow:hidden; }}

/* Custom HTML table: rounded frame, navy header with white text, zebra rows.
   overflow-x:auto (rather than hidden) so a table wider than the viewport
   scrolls horizontally on a phone instead of breaking the page layout; the
   rounded corners still clip because overflow-y stays hidden. */
.tablewrap {{
  border:1px solid var(--rule); border-radius:var(--radius-sm);
  overflow-x:auto; overflow-y:hidden; -webkit-overflow-scrolling:touch;
  box-shadow:0 1px 4px rgba(11,31,58,.06); margin:.2rem 0 .4rem 0;
}}
.tablewrap table {{ width:100%; min-width:640px; border-collapse:collapse; font-size:.85rem; }}
.tablewrap thead th {{
  background:var(--navy); color:{COLORS['white']}; text-align:left;
  padding:.68rem .95rem; font-size:.68rem; font-weight:600;
  letter-spacing:.08em; text-transform:uppercase; white-space:nowrap;
}}
.tablewrap tbody td {{ padding:.62rem .95rem; border-bottom:1px solid var(--rule); color:var(--ink); }}
.tablewrap tbody tr:last-child td {{ border-bottom:0; }}
.tablewrap tbody tr:nth-child(even) {{ background:var(--ice-faint); }}
.tablewrap tbody tr:hover td {{ background:var(--ice-pale); }}
.tablewrap td.rowlab {{ font-weight:600; color:var(--navy); white-space:nowrap; }}
.tablewrap tr.hl td {{ background:var(--ice-pale) !important; font-weight:700; }}

/* ---------- LIMITATIONS + DISCLAIMER ---------- */
.limits {{ border:1px solid var(--rule); border-radius:var(--radius-sm); padding:1.05rem 1.25rem; background:var(--ice-faint); font-size:.83rem; }}
.limits li {{ margin-bottom:.3rem; color:var(--ink-muted); }}

/* Numbered list: each bullet carries its own index in a small navy badge. */
.numlist {{ list-style:none; margin:0; padding:0; border:1px solid var(--rule); border-radius:var(--radius-sm); background:var(--ice-faint); overflow:hidden; }}
.numlist li {{ display:flex; gap:.75rem; align-items:flex-start; padding:.65rem 1.1rem; border-bottom:1px solid var(--rule); }}
.numlist li:last-child {{ border-bottom:0; }}
.numlist .n {{
  flex:0 0 20px; height:20px; border-radius:50%; background:var(--navy); color:{COLORS['white']};
  font-size:.64rem; font-weight:700; display:flex; align-items:center; justify-content:center;
  margin-top:.15rem;
}}
.numlist .t {{ flex:1 1 auto; color:var(--ink-muted); font-size:.83rem; line-height:1.55; }}

.disclaimer {{ background:var(--navy); color:var(--ice); border-radius:var(--radius); padding:1.2rem 1.45rem; margin-top:2.4rem; font-size:.78rem; line-height:1.6; }}
.disclaimer .sig {{ color:{COLORS['white']}; font-weight:600; letter-spacing:.1em; text-transform:uppercase; font-size:.74rem; margin-bottom:.5rem; }}

/* ---------- EMPTY STATE ---------- */
.empty {{ border:1px dashed var(--rule); border-radius:var(--radius); padding:3.2rem 2rem; text-align:center; background:var(--ice-faint); }}
.empty h3 {{ color:var(--navy); font-weight:600; font-size:1.1rem; margin:0 0 .4rem 0; }}
.empty p {{ color:var(--ink-muted); font-size:.87rem; margin:0; }}

/* ---------- MOBILE ---------- */
@media (max-width:640px) {{
  .block-container {{ padding-left:1rem; padding-right:1rem; }}
  .masthead h1 {{ font-size:1.4rem; overflow-wrap:break-word; }}
  .masthead .sub {{ font-size:.82rem; }}
  .mcell {{ min-width:44%; }}
  /* Flag rows stack instead of forcing three fixed-width columns into a
     narrow screen, which would either overflow or crush the note text. */
  .flagrow {{ flex-direction:column; gap:.3rem; padding:.55rem 0; }}
  .flagtag {{ flex:0 0 auto; width:fit-content; padding:.16rem .55rem; }}
  .flagfield {{ flex:0 0 auto; }}
  .tablewrap table {{ min-width:560px; font-size:.8rem; }}
  .pill {{ font-size:.68rem; padding:.3rem .8rem; }}
}}

@media (prefers-reduced-motion: reduce) {{ * {{ animation:none !important; transition:none !important; }} }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------
# SMALL RENDER HELPERS
# ---------------------------------------------------------------------
def pill(number, label, note=""):
    """Section label: numbered pill. The number encodes the pipeline order."""
    st.markdown(
        f'<div class="pill"><span class="num">{number}</span>{label}</div>',
        unsafe_allow_html=True)
    if note:
        st.markdown(f'<p class="pill-note">{note}</p>', unsafe_allow_html=True)


def metric_strip(pairs):
    """Horizontal strip of key/value cells."""
    cells = "".join(
        f'<div class="mcell"><div class="k">{k}</div><div class="v">{v}</div></div>'
        for k, v in pairs)
    st.markdown(f'<div class="mstrip">{cells}</div>', unsafe_allow_html=True)


def callout(html, gap_above=False):
    """gap_above adds a bit of extra top margin, for a callout that follows
    a visually dense block (e.g. the verdict band) rather than another
    callout."""
    cls = "callout callout-gap" if gap_above else "callout"
    st.markdown(f'<div class="{cls}">{html}</div>', unsafe_allow_html=True)


def render_table(df, index_label="", highlight_index=None):
    """Render a DataFrame as a rounded HTML table with a navy header.

    Replaces st.dataframe for report tables: st.dataframe draws its grid on
    canvas in modern Streamlit, so the header row cannot be recoloured with
    CSS. `highlight_index` tints one row (e.g. the headline multiple).
    """
    cols = list(df.columns)
    head = "".join(f"<th>{c}</th>" for c in cols)
    body = []
    for idx, row in df.iterrows():
        cells = "".join(f"<td>{row[c]}</td>" for c in cols)
        cls = " class=\"hl\"" if (highlight_index is not None and idx == highlight_index) else ""
        body.append(f'<tr{cls}><td class="rowlab">{idx}</td>{cells}</tr>')
    st.markdown(
        f'<div class="tablewrap"><table><thead><tr><th>{index_label}</th>'
        f'{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>',
        unsafe_allow_html=True)


def numbered_list(items):
    """Bulleted content where every item carries its own number badge."""
    rows = "".join(
        f'<li><span class="n">{i + 1}</span><span class="t">{it}</span></li>'
        for i, it in enumerate(items))
    st.markdown(f'<ul class="numlist">{rows}</ul>', unsafe_allow_html=True)
