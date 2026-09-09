"""
=============================================================================
SECTION R4 - SCORECARD PEMILIHAN HEADLINE MULTIPLE
=============================================================================
TUJUAN  : Memilih satu multiple yang paling layak dijadikan patokan, secara
          eksplisit dan bisa diperdebatkan, bukan berdasarkan preferensi
          yang tidak tertulis.

RUMUS   : Skor total = Base + Stability + Driver positif + Observasi

  R4.1 BASE (menurut sektor)
       Financials  P/BV 45, P/E 35, EV 0
                   Multiple berbasis Enterprise Value tidak bermakna untuk
                   bank dan asuransi, karena utang bagi mereka adalah bahan
                   baku, bukan pendanaan. Enterprise Value tidak terdefinisi
                   dengan baik. Skornya nol, bukan sekadar rendah.

       Property    P/BV 40, EV/EBITDA 25, P/E 25, EV/Sales 10
                   Nilai perusahaan properti melekat pada aset, sehingga
                   P/BV paling relevan.

       Lainnya     EV/EBITDA 40, P/E 28, P/BV 22, EV/Sales 15
                   EV/EBITDA paling tahan terhadap perbedaan struktur modal
                   dan kebijakan penyusutan.

  R4.2 STABILITY (maksimum 25)
       CV    = standar deviasi multiple / rata-ratanya
       Skor  = 25 x (1 - min(CV, 1))

       Semakin stabil sebuah multiple secara historis, semakin bermakna
       rata-ratanya sebagai patokan. Multiple yang berayun liar tidak punya
       nilai tengah yang layak dijadikan target.

  R4.3 DRIVER POSITIF (15 atau 0)
       Bernilai penuh hanya bila driver positif di SELURUH jendela. Satu
       kuartal dengan laba negatif membuat P/E terputus dan rata-ratanya
       hanya mewakili sebagian periode.

  R4.4 OBSERVASI (maksimum 10)
       Skor = 10 x jumlah observasi / 200, dibatasi 10.

  R4.5 SYARAT GUGUR
       Sebuah multiple mendapat skor nol bila salah satu berlaku:
         - Multiple berbasis EV pada emiten finansial
         - Driver saat ini tidak positif
         - Jumlah observasi di bawah ambang minimum

OUTPUT  : dict evaluasi per multiple, dan nama headline yang terpilih.
=============================================================================
"""

import numpy as np
import pandas as pd

from rel_config import (REL_CONFIG, SCORE_WEIGHTS, BASE_SCORE, MULTIPLES,
                        DRIVER_OF, IS_EV, FINANCIAL_KEYWORDS, PROPERTY_KEYWORDS)


def sector_bucket(d):
    """Kelompokkan emiten untuk menentukan base score."""
    text = f"{d.get('sector','')} {d.get('industry','')}".lower()
    if any(k in text for k in FINANCIAL_KEYWORDS):
        return "financial"
    if any(k in text for k in PROPERTY_KEYWORDS):
        return "property"
    return "default"


def evaluate(m, h1, cur, d):
    """Nilai kelayakan satu multiple."""
    bucket = sector_bucket(d)
    e = {"multiple": m, "bucket": bucket, "base": BASE_SCORE[bucket][m],
         "stability": 0.0, "driver_pos": 0, "observation": 0.0,
         "score": 0.0, "n": 0, "cv": np.nan, "status": ""}

    # ---- syarat gugur 1: EV pada emiten finansial ----
    if IS_EV[m] and bucket == "financial":
        e["status"] = "Enterprise Value is not meaningful for a financial issuer"
        return e

    s = pd.to_numeric(h1.get(m, pd.Series(dtype=float)), errors="coerce")
    s = s[np.isfinite(s) & (s > 0)]
    e["n"] = int(len(s))

    # ---- syarat gugur 2: driver tidak positif ----
    drv_now = cur.get(DRIVER_OF[m], np.nan)
    if pd.isna(drv_now) or drv_now <= 0:
        e["status"] = f"{DRIVER_OF[m]} is negative or not available"
        return e

    # ---- syarat gugur 3: observasi kurang ----
    if len(s) < REL_CONFIG["min_obs"]:
        e["status"] = f"only {len(s)} observations, minimum {REL_CONFIG['min_obs']}"
        return e

    # ---- R4.2 stability ----
    mean = float(s.mean())
    cv = float(s.std(ddof=1) / mean) if mean else np.nan
    e["cv"] = cv
    e["stability"] = float(max(0.0, SCORE_WEIGHTS["stability_max"] *
                               (1 - min(cv if np.isfinite(cv) else 1.0, 1.0))))

    # ---- R4.3 driver positif sepanjang jendela ----
    drv_series = pd.to_numeric(h1[DRIVER_OF[m]], errors="coerce").dropna()
    e["driver_pos"] = (SCORE_WEIGHTS["driver_positive"]
                       if (len(drv_series) and (drv_series > 0).all()) else 0)

    # ---- R4.4 observasi ----
    e["observation"] = float(min(SCORE_WEIGHTS["observation_max"],
                                 SCORE_WEIGHTS["observation_max"] * len(s)
                                 / SCORE_WEIGHTS["obs_full"]))

    e["score"] = e["base"] + e["stability"] + e["driver_pos"] + e["observation"]
    e["status"] = "eligible"
    return e


def run_scorecard(h1, cur, d):
    """Jalankan evaluasi untuk keempat multiple dan pilih headline."""
    ev = {m: evaluate(m, h1, cur, d) for m in MULTIPLES}
    eligible = {m: e for m, e in ev.items() if e["score"] > 0}
    head = max(eligible, key=lambda m: eligible[m]["score"]) if eligible else None

    if head is not None:
        cv = ev[head]["cv"]
        if np.isfinite(cv) and cv > REL_CONFIG["warn_cv"]:
            d["flags"].warn(
                "Headline volatility",
                f"{head} has a coefficient of variation of {cv:.2f} over the "
                f"window. This multiple swings quite a bit, so its average is a "
                f"less solid anchor for mean reversion.")
    else:
        d["flags"].warn("Headline multiple",
                        "No multiple met the eligibility requirements (sector "
                        "relevance, driver sign, or observation count).")

    return ev, head


def scorecard_table(ev):
    """Tabel scorecard untuk ditampilkan."""
    rows = {}
    for m, e in ev.items():
        rows[m] = {
            "Base (sector)": f"{e['base']:.0f}",
            "Stability (25)": f"{e['stability']:.1f}",
            "Driver positive (15)": f"{e['driver_pos']:.0f}",
            "Observations (10)": f"{e['observation']:.1f}",
            "TOTAL": f"{e['score']:.1f}",
            "CV": f"{e['cv']:.2f}" if np.isfinite(e["cv"]) else "n/a",
            "Status": e["status"],
        }
    return pd.DataFrame(rows).T
