"""
=============================================================================
REL MAIN - ORKESTRATOR
=============================================================================
TUJUAN  : Menjalankan seluruh section secara berurutan. File ini tidak
          berisi rumus, hanya mengatur urutan pemanggilan dan menyiapkan
          tabel keluaran.

URUTAN ALUR:
    R1  Pengambilan data, harga, laporan keuangan, kurs
    R2  Seri driver TTM dengan fallback berlapis
    R3  Seri multiple harian, potong ke jendela, uji stabilitas saham
    R4  Scorecard, pemilihan headline multiple
    R5  Implied price dan verdict

CARA PAKAI:
    from rel_main import analyze_relative
    r = analyze_relative("BUVA")
=============================================================================
"""

import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from rel_config import REL_CONFIG, MULTIPLES, DRIVER_OF, DISCLAIMER
from r01_fetch import pull, num
from r02_drivers import build_drivers
from r03_multiples import (build_series, window_slice, check_share_stability,
                           implied_price, benchmark)
from r04_scorecard import run_scorecard, scorecard_table, sector_bucket

SNAPSHOT_FIELDS = ["EPS", "BVPS", "EBITDA", "Rev", "Shares", "NetDebt", "MI",
                   "EV", "MktCap", "Price", "NI", "Equity", "Debt", "Cash"]


# -----------------------------------------------------------------------
# LAYER FETCH (dipisah supaya bisa di-cache UI)
# -----------------------------------------------------------------------
def fetch_relative_bundle(code):
    """Jalankan hanya tahap yang butuh jaringan: R1 dan R2."""
    d = pull(code)
    if not d["ok"]:
        return {"d": d, "drivers": None, "ok": False}
    drivers = build_drivers(d)
    return {"d": d, "drivers": drivers, "ok": True}


# -----------------------------------------------------------------------
# PIPELINE UTAMA
# -----------------------------------------------------------------------
def analyze_relative(code, bundle=None):
    """Jalankan seluruh pipeline relative valuation untuk satu emiten."""
    out = {"code": str(code).upper().strip(), "ok": False, "error": None}

    if bundle is None:
        bundle = fetch_relative_bundle(code)

    d = bundle["d"]
    out["d"] = d
    if not bundle["ok"]:
        out["error"] = d.get("error") or "Insufficient data"
        return out

    s = bundle["drivers"]

    # ---------------- R3 ----------------
    h = build_series(d, s)
    if h.empty:
        out["error"] = "Multiple series could not be built"
        d["flags"].missing("Multiple series", out["error"])
        return out

    h1 = window_slice(h)
    out["h"] = h
    out["h1"] = h1
    out["share_change"] = check_share_stability(h1, d["flags"])

    last = h.iloc[-1]
    cur = {k: num(last.get(k)) for k in SNAPSHOT_FIELDS}
    for m in MULTIPLES:
        cur[m] = num(last.get(m))
    out["cur"] = cur

    # ---------------- R4 ----------------
    ev, head = run_scorecard(h1, cur, d)
    out["scorecard"] = ev
    out["headline"] = head

    # ---------------- R5 ----------------
    out["multiples"] = build_multiple_rows(h1, cur, d)
    out["verdict"] = build_verdict(h1, cur, ev, head, out["multiples"])

    out["ok"] = True
    return out


# -----------------------------------------------------------------------
# R5.1 TABEL MULTIPLE
# -----------------------------------------------------------------------
def build_multiple_rows(h1, cur, d):
    """Statistik dan implied price untuk keempat multiple."""
    rows = {}
    for m in MULTIPLES:
        s = pd.to_numeric(h1[m], errors="coerce")
        s = s[np.isfinite(s) & (s > 0)]
        cur_m = cur.get(m, np.nan)
        avg, med, n = benchmark(s)
        ia = implied_price(avg, m, cur)
        im = implied_price(med, m, cur)
        price = cur["Price"]

        pct = (float((s < cur_m).mean() * 100)
               if (len(s) and np.isfinite(cur_m)) else np.nan)

        rows[m] = {
            "current": cur_m,
            "avg": avg,
            "median": med,
            "percentile": pct,
            "implied_avg": ia,
            "implied_med": im,
            "upside_avg": (ia / price - 1) if (np.isfinite(ia) and price > 0) else np.nan,
            "upside_med": (im / price - 1) if (np.isfinite(im) and price > 0) else np.nan,
            "obs": n,
            "p10": float(s.quantile(0.10)) if len(s) else np.nan,
            "p90": float(s.quantile(0.90)) if len(s) else np.nan,
        }
    return rows


# -----------------------------------------------------------------------
# R5.2 VERDICT
# -----------------------------------------------------------------------
def build_verdict(h1, cur, ev, head, rows):
    """Rangkum headline multiple menjadi rentang harga dan arah driver."""
    if head is None:
        return {"valid": False,
                "reason": "No multiple passed the eligibility scorecard."}

    r = rows[head]
    price = cur["Price"]
    ia, im = r["implied_avg"], r["implied_med"]

    if np.isfinite(ia) and np.isfinite(im):
        lo, hi = min(ia, im), max(ia, im)
    elif np.isfinite(ia):
        lo = hi = ia
    elif np.isfinite(im):
        lo = hi = im
    else:
        return {"valid": False,
                "reason": f"{head} was selected but the implied price could not be calculated."}

    up_lo = lo / price - 1 if price > 0 else np.nan
    up_hi = hi / price - 1 if price > 0 else np.nan

    # arah driver sepanjang jendela
    dv = pd.to_numeric(h1[DRIVER_OF[head]], errors="coerce").dropna()
    drv_chg = (float(dv.iloc[-1] / dv.iloc[0] - 1)
               if (len(dv) > 1 and dv.iloc[0] > 0) else np.nan)

    # tanda peringatan bila hasilnya ekstrem
    review = bool(np.isfinite(up_hi) and
                  (up_hi > REL_CONFIG["review_upside"]
                   or up_lo < REL_CONFIG["review_downside"]))

    return {
        "valid": True,
        "headline": head,
        "score": ev[head]["score"],
        "cv": ev[head]["cv"],
        "price": price,
        "implied_low": lo,
        "implied_high": hi,
        "upside_low": up_lo,
        "upside_high": up_hi,
        "percentile": r["percentile"],
        "driver": DRIVER_OF[head],
        "driver_change": drv_chg,
        "review_required": review,
        "obs": r["obs"],
    }


# -----------------------------------------------------------------------
# TABEL SNAPSHOT
# -----------------------------------------------------------------------
def snapshot_table(cur, d):
    """Tabel fundamental dengan kolom sumber setiap angka."""
    src = d["src"]
    ccy_note = " (converted)" if d.get("fx") is not None else ""

    def tn(v):
        return f"{v/1e12:,.2f}" if (v is not None and np.isfinite(v)) else "N/M"

    def plain(v, dec=2):
        return f"{v:,.{dec}f}" if (v is not None and np.isfinite(v)) else "N/M"

    roe = (cur["NI"] / cur["Equity"] * 100
           if (np.isfinite(cur.get("Equity", np.nan)) and cur["Equity"]) else np.nan)
    nd_ebitda = (cur["NetDebt"] / cur["EBITDA"]
                 if (np.isfinite(cur.get("EBITDA", np.nan)) and cur["EBITDA"] > 0)
                 else np.nan)

    items = [
        ("Last price (IDR)", plain(cur["Price"], 0), "market"),
        ("Shares outstanding (mn)",
         plain(cur["Shares"] / 1e6, 0) if np.isfinite(cur["Shares"]) else "N/M",
         src.get("sh", "-")),
        ("Market cap (IDR tn)", tn(cur["MktCap"]), "calculated"),
        ("Total debt (IDR tn)" + ccy_note, tn(cur["Debt"]), src.get("debt", "-")),
        ("Cash (IDR tn)" + ccy_note, tn(cur["Cash"]), src.get("cash", "-")),
        ("Net debt (IDR tn)", tn(cur["NetDebt"]), "calculated"),
        ("Minority interest (IDR tn)", tn(cur["MI"]), src.get("mi", "-")),
        ("Enterprise value (IDR tn)", tn(cur["EV"]), "calculated"),
        ("Revenue TTM (IDR tn)" + ccy_note, tn(cur["Rev"]), src.get("rev", "-")),
        ("EBITDA TTM (IDR tn)" + ccy_note, tn(cur["EBITDA"]), src.get("ebitda", "-")),
        ("Net income TTM (IDR tn)" + ccy_note, tn(cur["NI"]), src.get("ni", "-")),
        ("Equity (IDR tn)" + ccy_note, tn(cur["Equity"]), src.get("eq", "-")),
        ("EPS TTM (IDR)", plain(cur["EPS"]), "calculated"),
        ("BVPS (IDR)", plain(cur["BVPS"]), "calculated"),
        ("ROE TTM (%)", plain(roe, 1), "calculated"),
        ("Net debt / EBITDA (x)", plain(nd_ebitda), "calculated"),
    ]
    return pd.DataFrame([{"Value": v, "Source": s} for _, v, s in items],
                        index=[k for k, _, _ in items])


def multiple_table(rows, cur):
    """Tabel keempat multiple beserta implied price dan upside."""
    def x(v):
        return f"{v:,.2f}x" if (v is not None and np.isfinite(v)) else "N/M"

    def rp(v):
        return f"{v:,.0f}" if (v is not None and np.isfinite(v)) else "N/M"

    def pc(v, sign=False):
        if v is None or not np.isfinite(v):
            return "N/M"
        return f"{v*100:+.1f}%" if sign else f"{v*100:.0f}%"

    out = {}
    for m, r in rows.items():
        out[m] = {
            "Price now": rp(cur["Price"]),
            "Current": x(r["current"]),
            "1Y average": x(r["avg"]),
            "1Y median": x(r["median"]),
            "Implied @avg": rp(r["implied_avg"]),
            "Upside @avg": pc(r["upside_avg"], sign=True),
            "Implied @median": rp(r["implied_med"]),
            "Upside @median": pc(r["upside_med"], sign=True),
        }
    return pd.DataFrame(out).T


def quality_table(d):
    """Log kualitas data."""
    rows = [
        ("Reporting currency",
         f"{d['fin_ccy']} converted to {d['px_ccy']} at daily rates"
         if d.get("fx") is not None else f"{d['fin_ccy']} (no conversion needed)"),
        ("EBITDA source", d["src"].get("ebitda", "-")),
        ("Debt source", d["src"].get("debt", "-")),
        ("Revenue source", d["src"].get("rev", "-")),
        ("Equity source", d["src"].get("eq", "-")),
        ("Share count source", d["src"].get("sh", "-")),
        ("Price date", str(d.get("price_date", "-"))),
    ]
    return pd.DataFrame([{"Detail": v} for _, v in rows], index=[k for k, _ in rows])


if __name__ == "__main__":
    import sys
    code = sys.argv[1] if len(sys.argv) > 1 else "BUVA"
    r = analyze_relative(code)
    if not r["ok"]:
        print("GAGAL:", r["error"])
    else:
        print(snapshot_table(r["cur"], r["d"]).to_string())
        print()
        print(multiple_table(r["multiples"], r["cur"]).to_string())
        print()
        print(scorecard_table(r["scorecard"]).to_string())
        print()
        print("HEADLINE:", r["headline"])
        print(r["d"]["flags"].render())
        print()
        print(DISCLAIMER)
