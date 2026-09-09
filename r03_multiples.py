"""
=============================================================================
SECTION R3 - SERI MULTIPLE HARIAN DAN IMPLIED PRICE
=============================================================================
TUJUAN  : Menyusun seri multiple harian sepanjang riwayat harga, lalu
          menghitung harga yang tersirat bila multiple kembali ke rata-rata
          atau mediannya sendiri.

RUMUS   :
  R3.1 PENYELARASAN
       Pos laporan keuangan dilaporkan per kuartal atau per tahun, sedangkan
       harga bergerak harian. Pos laporan diteruskan maju (forward fill)
       sampai laporan berikutnya terbit.

       Konsekuensi yang harus disadari: multiple akan melompat pada tanggal
       rilis laporan, bukan bergerak mulus. Lompatan itu nyata, bukan
       kesalahan hitung, tetapi membuat volatilitas multiple sebagian
       berasal dari jadwal pelaporan, bukan murni dari pergerakan harga.

  R3.2 KONVERSI MATA UANG
       Seluruh pos laporan keuangan dikalikan kurs HARIAN sebelum dipakai,
       sehingga sebanding dengan harga saham.

  R3.3 AGREGAT
       Market Cap       = Harga x Jumlah saham
       Net Debt         = Total Debt - Kas
       Enterprise Value = Market Cap + Net Debt + Minority Interest
       EPS              = Laba bersih TTM / Jumlah saham
       BVPS             = Ekuitas / Jumlah saham

  R3.4 MULTIPLE
       P/E        = Harga / EPS                (hanya bila EPS > 0)
       P/BV       = Harga / BVPS               (hanya bila BVPS > 0)
       EV/EBITDA  = EV / EBITDA                (hanya bila EBITDA > 0)
       EV/Sales   = EV / Revenue               (hanya bila Revenue > 0)

       Nilai dengan penyebut tidak positif dibuang, bukan dipaksa menjadi
       angka negatif yang tidak punya arti ekonomi.

  R3.5 IMPLIED PRICE
       Multiple ekuitas (P/E, P/BV):
           Harga tersirat = multiple benchmark x driver saat ini

       Multiple enterprise (EV/EBITDA, EV/Sales):
           EV tersirat     = multiple benchmark x driver saat ini
           Ekuitas tersirat = EV tersirat - Net Debt - Minority Interest
           Harga tersirat   = Ekuitas tersirat / Jumlah saham

       Perhatikan bahwa driver DIANGGAP TETAP. Yang berubah hanya
       multiple-nya. Ini asumsi paling penting sekaligus paling lemah dari
       seluruh metode ini.

OUTPUT  : DataFrame harian berisi seluruh agregat dan multiple, serta
          fungsi implied price.
=============================================================================
"""

import numpy as np
import pandas as pd

from rel_config import REL_CONFIG, DRIVER_OF, IS_EV
from r01_fetch import fx_series


# -----------------------------------------------------------------------
# R3.1 - R3.4 SERI MULTIPLE
# -----------------------------------------------------------------------
def build_series(d, s):
    """Bangun DataFrame harian berisi agregat dan keempat multiple."""
    px = d["px"]
    if len(px) == 0:
        return pd.DataFrame()
    idx = px.index

    def ff(x):
        if x is None or x.empty:
            return pd.Series(np.nan, index=idx)
        return x.reindex(idx.union(x.index)).sort_index().ffill().reindex(idx)

    fx = fx_series(d, idx)

    h = pd.DataFrame({"Price": px})
    h["Shares"] = ff(s["sh"])
    h["Equity"] = ff(s["eq"]) * fx
    h["Debt"] = ff(s["debt"]) * fx
    h["Cash"] = ff(s["cash"]) * fx
    h["MI"] = (ff(s["mi"]) * fx).fillna(0)
    h["EBITDA"] = ff(s["ebitda"]) * fx
    h["Rev"] = ff(s["rev"]) * fx
    h["NI"] = ff(s["ni"]) * fx

    h["NetDebt"] = h["Debt"].fillna(0) - h["Cash"].fillna(0)
    h["MktCap"] = h["Price"] * h["Shares"]
    h["EV"] = h["MktCap"] + h["NetDebt"] + h["MI"]
    h["EPS"] = h["NI"] / h["Shares"]
    h["BVPS"] = h["Equity"] / h["Shares"]

    h["P/E"] = np.where(h["EPS"] > 0, h["Price"] / h["EPS"], np.nan)
    h["P/BV"] = np.where(h["BVPS"] > 0, h["Price"] / h["BVPS"], np.nan)
    h["EV/EBITDA"] = np.where(h["EBITDA"] > 0, h["EV"] / h["EBITDA"], np.nan)
    h["EV/Sales"] = np.where(h["Rev"] > 0, h["EV"] / h["Rev"], np.nan)
    return h


def window_slice(h):
    """Potong ke jendela sejarah yang dipakai."""
    days = int(365.25 * REL_CONFIG["window_years"])
    return h.loc[h.index >= h.index[-1] - pd.Timedelta(days=days)]


def check_share_stability(h1, flags):
    """
    Periksa apakah jumlah saham berubah di dalam jendela.

    Perubahan jumlah saham (rights issue, private placement, buyback)
    membuat multiple sebelum dan sesudahnya tidak sebanding, sehingga
    rata-rata sepanjang jendela mencampur dua struktur modal berbeda.
    """
    sh = pd.to_numeric(h1.get("Shares", pd.Series(dtype=float)), errors="coerce").dropna()
    if len(sh) < 2:
        return np.nan
    change = float(sh.iloc[-1] / sh.iloc[0] - 1) if sh.iloc[0] > 0 else np.nan
    if np.isfinite(change) and abs(change) > REL_CONFIG["warn_share_change"]:
        flags.warn("Share count",
                   f"Changed {change*100:+.1f}% within the window. A corporate "
                   f"action likely occurred. Multiples before and after are not "
                   f"fully comparable, so the window average mixes two different "
                   f"capital structures.")
    return change


# -----------------------------------------------------------------------
# R3.5 IMPLIED PRICE
# -----------------------------------------------------------------------
def implied_price(mult, m, cur):
    """Harga tersirat bila multiple kembali ke `mult`, driver dianggap tetap."""
    drv = cur.get(DRIVER_OF[m], np.nan)
    if pd.isna(mult) or pd.isna(drv) or drv <= 0:
        return np.nan

    if not IS_EV[m]:
        return mult * drv

    sh = cur.get("Shares", np.nan)
    if pd.isna(sh) or sh <= 0:
        return np.nan
    net_debt = 0 if pd.isna(cur.get("NetDebt")) else cur["NetDebt"]
    mi = 0 if pd.isna(cur.get("MI")) else cur["MI"]
    equity_value = mult * drv - net_debt - mi
    return equity_value / sh if equity_value > 0 else np.nan


def hmean(s):
    """Rata-rata harmonik, hanya untuk nilai positif."""
    s = pd.to_numeric(s, errors="coerce")
    s = s[np.isfinite(s) & (s > 0)]
    return float(len(s) / np.sum(1.0 / s)) if len(s) else np.nan


def benchmark(series):
    """Rata-rata dan median satu seri multiple."""
    s = pd.to_numeric(series, errors="coerce")
    s = s[np.isfinite(s) & (s > 0)]
    if len(s) == 0:
        return np.nan, np.nan, 0
    avg = hmean(s) if REL_CONFIG["use_harmonic"] else float(s.mean())
    return avg, float(s.median()), int(len(s))
