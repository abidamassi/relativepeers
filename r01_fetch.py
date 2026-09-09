"""
=============================================================================
SECTION R1 - PENGAMBILAN DATA DAN KONVERSI MATA UANG
=============================================================================
TUJUAN  : Menarik harga, laporan keuangan tahunan dan kuartalan, serta
          metadata dari yfinance, lalu menyiapkan kurs harian bila laporan
          keuangan dilaporkan dalam mata uang berbeda dari harga saham.

MASALAH YANG DITANGANI:
          Sejumlah emiten IDX (BUMI, ADRO, ITMG, MEDC, ENRG) melaporkan
          laporan keuangan dalam USD sementara harganya dalam IDR. Tanpa
          konversi, seluruh multiple berbasis EV dan P/BV akan salah
          ribuan kali lipat.

          Konversi memakai kurs HARIAN, bukan kurs spot terakhir, karena
          seri multiple dihitung per hari perdagangan. Memakai satu kurs
          untuk seluruh periode akan memindahkan pergerakan kurs ke dalam
          pergerakan multiple.

PERBAIKAN DARI SKRIP ASAL:
          Fungsi pencarian baris lama memakai pencocokan longgar tanpa
          penyaring. Ketika baris "Total Revenue" tidak ada, kunci
          "Revenue" bisa cocok ke baris "Cost Of Revenue" dan seluruh
          perhitungan EV/Sales menjadi salah secara diam-diam. Versi ini
          menolak label yang mengandung kata pada daftar blokir, dan
          memilih label terpendek bila ada beberapa kandidat.

OUTPUT  : dict berisi harga, laporan keuangan, kurs, metadata, dan flag.
=============================================================================
"""

import numpy as np
import pandas as pd
import yfinance as yf

from rel_config import REL_CONFIG, KEYS, LABEL_BLOCKLIST


# -----------------------------------------------------------------------
# R1.1 PENCATATAN FLAG
# -----------------------------------------------------------------------
class FlagLog:
    """Menampung peringatan data selama satu run, tiga level."""

    def __init__(self):
        self.items = []

    def missing(self, field, note=""):
        self.items.append(("MISSING", field, note or "Not available in yfinance"))

    def zero(self, field, note=""):
        self.items.append(("ZERO", field, note))

    def warn(self, field, note=""):
        self.items.append(("WARN", field, note))

    @property
    def has_issue(self):
        return len(self.items) > 0

    def render(self):
        if not self.items:
            return "No data issues detected."
        order = {"MISSING": 0, "ZERO": 1, "WARN": 2}
        return "\n".join(
            f"  [{lv:<7}] {fd:<24} {nt}"
            for lv, fd, nt in sorted(self.items, key=lambda x: order.get(x[0], 9)))


# -----------------------------------------------------------------------
# R1.2 HELPER
# -----------------------------------------------------------------------
def norm_ticker(code):
    """'buva' atau 'BUVA ' menjadi 'BUVA.JK'."""
    t = str(code).strip().upper().replace(" ", "")
    if not t:
        raise ValueError("Empty ticker")
    return t if "." in t else f"{t}.JK"


def num(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else np.nan
    except Exception:
        return np.nan


def find_row(df, keys):
    """
    Cari baris laporan keuangan berdasarkan daftar kandidat label.

    Dua tahap:
      1. Pencocokan persis, mengikuti urutan prioritas kandidat.
      2. Pencocokan longgar, HANYA pada label yang tidak mengandung kata
         pada daftar blokir, dan memilih label terpendek karena label
         terpendek biasanya yang paling spesifik.
    """
    if df is None or getattr(df, "empty", True):
        return None
    label_map = {str(i).strip().lower(): i for i in df.index}

    for k in keys:
        if k.lower() in label_map:
            return df.loc[label_map[k.lower()]]

    for k in keys:
        kl = k.lower()
        cands = [(len(lk), orig) for lk, orig in label_map.items()
                 if kl in lk and not any(b in lk for b in LABEL_BLOCKLIST)]
        if cands:
            return df.loc[min(cands)[1]]
    return None


def series_from(df, keys):
    """Ubah satu baris laporan keuangan menjadi Series terurut waktu."""
    r = find_row(df, keys)
    if r is None:
        return pd.Series(dtype=float)
    s = pd.Series({pd.Timestamp(c): num(r.get(c)) for c in df.columns}).dropna()
    return s.sort_index()


def series_sum(df, key_groups):
    """Jumlahkan beberapa baris, dipakai untuk utang jangka pendek + panjang."""
    parts = [series_from(df, g) for g in key_groups]
    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.Series(dtype=float)
    out = parts[0]
    for p in parts[1:]:
        out = out.add(p.reindex(out.index).fillna(0), fill_value=0)
    return out.sort_index()


# -----------------------------------------------------------------------
# R1.3 PENGAMBILAN UTAMA
# -----------------------------------------------------------------------
def pull(code):
    """Ambil seluruh data satu emiten. Tidak melempar exception ke pemanggil."""
    ticker = norm_ticker(code)
    flags = FlagLog()
    d = {"ticker": ticker, "code": ticker.replace(".JK", ""),
         "flags": flags, "src": {}, "ok": False, "error": None}

    try:
        t = yf.Ticker(ticker)
    except Exception as exc:
        d["error"] = f"{type(exc).__name__}: {exc}"
        flags.missing("Ticker", d["error"])
        return d

    # ---- metadata ----
    try:
        info = t.get_info() or {}
    except Exception:
        info = {}
    d["info"] = info
    d["name"] = info.get("longName") or info.get("shortName") or d["code"]
    d["sector"] = info.get("sector") or "n/a"
    d["industry"] = info.get("industry") or "n/a"
    d["fin_ccy"] = (info.get("financialCurrency") or "IDR").upper()
    d["px_ccy"] = (info.get("currency") or "IDR").upper()

    # ---- harga ----
    try:
        px = t.history(period=REL_CONFIG["price_period"], auto_adjust=False)["Close"].dropna()
        px.index = pd.to_datetime(px.index).tz_localize(None)
    except Exception:
        px = pd.Series(dtype=float)

    if len(px) == 0:
        d["error"] = "Price history not available"
        flags.missing("Price", d["error"])
        return d

    d["px"] = px
    d["price"] = float(px.iloc[-1])
    d["price_date"] = px.index[-1].date()

    # ---- laporan keuangan ----
    S = {}
    for key, attr in [("ais", "income_stmt"), ("qis", "quarterly_income_stmt"),
                      ("abs", "balance_sheet"), ("qbs", "quarterly_balance_sheet"),
                      ("acf", "cashflow"), ("qcf", "quarterly_cashflow")]:
        try:
            S[key] = getattr(t, attr)
        except Exception:
            S[key] = None
    d["S"] = S

    if all(S.get(k) is None or getattr(S.get(k), "empty", True)
           for k in ["ais", "qis"]):
        flags.missing("Income statement",
                      "Neither annual nor quarterly is available.")

    # ---- kurs ----
    d["fx"] = None
    if d["fin_ccy"] != d["px_ccy"]:
        pair = f"{d['fin_ccy']}{d['px_ccy']}=X"
        try:
            fx = yf.Ticker(pair).history(period=REL_CONFIG["price_period"])["Close"].dropna()
            fx.index = pd.to_datetime(fx.index).tz_localize(None)
        except Exception:
            fx = pd.Series(dtype=float)

        if fx.empty:
            flags.missing("Exchange rate",
                          f"Pair {pair} failed to fetch. Financial statements in "
                          f"{d['fin_ccy']} cannot be converted, so every EV-based "
                          f"and P/BV multiple is INVALID.")
        else:
            d["fx"] = fx
            flags.warn("Reporting currency",
                       f"Financial statements in {d['fin_ccy']}, converted to "
                       f"{d['px_ccy']} using daily exchange rates. Latest rate "
                       f"{fx.iloc[-1]:,.0f}.")

    d["ok"] = True
    return d


def fx_series(d, idx):
    """Kurs harian sejajar dengan index harga. Bernilai 1.0 bila tidak perlu konversi."""
    if d.get("fx") is None:
        return pd.Series(1.0, index=idx)
    fx = d["fx"]
    aligned = fx.reindex(idx.union(fx.index)).sort_index().ffill().bfill().reindex(idx)
    return aligned.ffill().fillna(1.0)
