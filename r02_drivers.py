"""
=============================================================================
SECTION R2 - SERI DRIVER TTM DENGAN FALLBACK BERLAPIS
=============================================================================
TUJUAN  : Menyusun seri waktu untuk setiap driver multiple, dengan beberapa
          lapis cadangan supaya emiten yang pelaporannya tidak lengkap tetap
          bisa dinilai, tetapi sumber setiap angka tercatat sehingga
          pembaca tahu mana yang dari laporan dan mana yang hasil rekonstruksi.

RUMUS   :
  R2.1 TRAILING TWELVE MONTHS
       Pos laba rugi   : TTM_t = jumlah 4 kuartal terakhir
       Pos neraca      : dipakai apa adanya (stok, bukan aliran)

       Nilai tahunan dan TTM kuartalan digabung, lalu bila ada tanggal yang
       sama, versi kuartalan yang dipakai karena lebih mutakhir.

  R2.2 LAPIS FALLBACK
       Lapis 1  baris langsung dari laporan kuartalan atau tahunan
       Lapis 2  rekonstruksi dari komponen
                  EBITDA = Operating Income + D&A
                  Debt   = Current Debt + Long Term Debt
       Lapis 3  info dict yfinance (totalRevenue, ebitda, totalDebt,
                  totalCash, netIncomeToCommon, sharesOutstanding)
       Lapis 4  turunan
                  Equity = bookValue x shares

       Setiap lapis yang terpakai dicatat di d["src"], dan ditampilkan
       sebagai kolom Source pada tabel snapshot.

CATATAN : Lapis 3 hanya memberi SATU titik data pada tanggal terakhir,
          bukan seri waktu. Multiple yang bergantung padanya akan berupa
          garis datar sepanjang jendela, sehingga statistik sejarahnya
          tidak bermakna. Ini diberi flag.

OUTPUT  : dict berisi Series per driver, dan d["src"] berisi asal usulnya.
=============================================================================
"""

import numpy as np
import pandas as pd

from rel_config import KEYS
from r01_fetch import series_from, series_sum

BALANCE_KEYS = ("eq", "debt", "cash", "mi", "sh")


# -----------------------------------------------------------------------
# R2.1 SERI TTM
# -----------------------------------------------------------------------
def ttm_series(d, key):
    """Bangun seri untuk satu driver, dalam mata uang laporan keuangan."""
    S = d["S"]
    is_bs = key in BALANCE_KEYS

    if key == "da":
        ann_df, q_df = S["acf"], S["qcf"]
    elif is_bs:
        ann_df, q_df = S["abs"], S["qbs"]
    else:
        ann_df, q_df = S["ais"], S["qis"]

    groups = KEYS[key]
    ann = series_sum(ann_df, groups) if len(groups) > 1 else series_from(ann_df, groups[0])
    qtr = series_sum(q_df, groups) if len(groups) > 1 else series_from(q_df, groups[0])

    if is_bs:
        comb = pd.concat([ann, qtr])
    else:
        ttm = qtr.rolling(4).sum().dropna() if len(qtr) >= 4 else pd.Series(dtype=float)
        comb = pd.concat([ann, ttm])

    comb = comb[~comb.index.duplicated(keep="last")].sort_index()
    return comb


# -----------------------------------------------------------------------
# R2.2 FALLBACK BERLAPIS
# -----------------------------------------------------------------------
def build_drivers(d):
    """Susun seluruh driver beserta catatan sumbernya."""
    flags = d["flags"]
    src = d["src"]
    keys = ["rev", "ni", "ebitda", "opinc", "da", "eq", "debt", "cash", "mi", "sh"]
    s = {k: ttm_series(d, k) for k in keys}

    # ---- EBITDA: baris langsung, atau Operating Income + D&A ----
    if s["ebitda"].empty and not s["opinc"].empty:
        da = s["da"].reindex(s["opinc"].index).ffill().fillna(0)
        s["ebitda"] = s["opinc"].add(da, fill_value=0)
        src["ebitda"] = "OpInc + D&A"
        if s["da"].empty:
            flags.warn("D&A",
                       "Not found in the cash flow statement. EBITDA is "
                       "reconstructed from Operating Income alone, so it is "
                       "understated and EV/EBITDA will look more expensive than "
                       "it really is.")
    else:
        src["ebitda"] = "EBITDA row" if not s["ebitda"].empty else "missing"

    # ---- Debt: baris Total Debt, atau jumlah komponen ----
    if s["debt"].empty:
        s["debt"] = ttm_series(d, "debt_c")
        src["debt"] = "ST + LT debt" if not s["debt"].empty else "missing"
    else:
        src["debt"] = "Total Debt row"

    for k in ["rev", "ni", "eq", "cash", "mi", "sh"]:
        src[k] = "statement" if not s[k].empty else "missing"

    # ---- Lapis 3: info dict ----
    info = d.get("info", {}) or {}
    last_dt = d["px"].index[-1]
    info_used = []

    for k, ik in [("rev", "totalRevenue"), ("ebitda", "ebitda"),
                  ("debt", "totalDebt"), ("cash", "totalCash")]:
        if s[k].empty and info.get(ik) is not None:
            s[k] = pd.Series({pd.Timestamp(last_dt): float(info[ik])})
            src[k] = "info dict"
            info_used.append(k)

    if s["ni"].empty and info.get("netIncomeToCommon") is not None:
        s["ni"] = pd.Series({pd.Timestamp(last_dt): float(info["netIncomeToCommon"])})
        src["ni"] = "info dict"
        info_used.append("ni")

    if s["sh"].empty:
        v = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
        if v:
            s["sh"] = pd.Series({pd.Timestamp(last_dt): float(v)})
            src["sh"] = "info dict"
            info_used.append("sh")

    # ---- Lapis 4: turunan ----
    if s["eq"].empty and info.get("bookValue") and not s["sh"].empty:
        s["eq"] = pd.Series({pd.Timestamp(last_dt):
                             float(info["bookValue"]) * float(s["sh"].iloc[-1])})
        src["eq"] = "info bookValue x shares"
        info_used.append("eq")

    if info_used:
        flags.warn("Info dict source",
                   f"Item(s) {sorted(info_used)} were taken from the yfinance info "
                   f"dict rather than a financial statement. This is only a single "
                   f"data point on the last date, so any multiple depending on it "
                   f"will be flat across the window and its history is not "
                   f"meaningful.")

    for k in ["rev", "ni", "eq", "sh"]:
        if s[k].empty:
            flags.missing(k, "Not available at any fallback layer.")

    return s
