"""
=============================================================================
TEST RELATIVE - VALIDASI DENGAN DATA SINTETIS
=============================================================================
TUJUAN  : Menguji Section R1 sampai R5 tanpa memanggil yfinance. Data harga
          dan laporan keuangan dibuat manual dengan angka yang hasilnya bisa
          dihitung tangan.

          Jalankan dengan: python test_relative.py
=============================================================================
"""

import numpy as np
import pandas as pd

from rel_config import REL_CONFIG, MULTIPLES, DRIVER_OF, LABEL_BLOCKLIST
from r01_fetch import FlagLog, norm_ticker, find_row, series_from
from r02_drivers import build_drivers
from r03_multiples import (build_series, window_slice, check_share_stability,
                           implied_price, benchmark)
from r04_scorecard import evaluate, run_scorecard, sector_bucket
from rel_main import analyze_relative, build_multiple_rows, build_verdict

SHARES = 10_000_000_000.0


# -----------------------------------------------------------------------
# EMITEN SINTETIS
# -----------------------------------------------------------------------
def make_fake(price_level=1000.0, fin_ccy="IDR", n_days=800):
    """Harga datar, laporan keuangan konstan, sehingga multiple mudah dihitung."""
    idx = pd.bdate_range(end=pd.Timestamp("2026-08-31"), periods=n_days)
    px = pd.Series(price_level, index=idx, dtype=float)

    q_dates = pd.to_datetime(["2024-12-31", "2025-03-31", "2025-06-30",
                              "2025-09-30", "2025-12-31", "2026-03-31",
                              "2026-06-30"])
    a_dates = pd.to_datetime(["2023-12-31", "2024-12-31", "2025-12-31"])

    # Kuartalan: revenue 1000bn, NI 100bn, OpInc 150bn, D&A 50bn per kuartal
    qis = pd.DataFrame(index=["Total Revenue", "Operating Income", "Net Income"],
                       columns=q_dates, dtype=float)
    qis.loc["Total Revenue"] = 1_000e9
    qis.loc["Operating Income"] = 150e9
    qis.loc["Net Income"] = 100e9

    ais = pd.DataFrame(index=["Total Revenue", "Operating Income", "Net Income"],
                       columns=a_dates, dtype=float)
    ais.loc["Total Revenue"] = 4_000e9
    ais.loc["Operating Income"] = 600e9
    ais.loc["Net Income"] = 400e9

    qbs = pd.DataFrame(index=["Stockholders Equity", "Total Debt",
                              "Cash And Cash Equivalents", "Minority Interest",
                              "Ordinary Shares Number"],
                       columns=q_dates, dtype=float)
    qbs.loc["Stockholders Equity"] = 5_000e9
    qbs.loc["Total Debt"] = 2_000e9
    qbs.loc["Cash And Cash Equivalents"] = 500e9
    qbs.loc["Minority Interest"] = 0.0
    qbs.loc["Ordinary Shares Number"] = SHARES

    abs_ = qbs.reindex(columns=a_dates).copy()
    for c in a_dates:
        abs_[c] = qbs.iloc[:, 0].values

    qcf = pd.DataFrame(index=["Depreciation And Amortization"],
                       columns=q_dates, dtype=float)
    qcf.loc["Depreciation And Amortization"] = 50e9
    acf = pd.DataFrame(index=["Depreciation And Amortization"],
                       columns=a_dates, dtype=float)
    acf.loc["Depreciation And Amortization"] = 200e9

    d = {
        "ticker": "TEST.JK", "code": "TEST", "name": "PT Uji Relatif Tbk",
        "sector": "Consumer Cyclical", "industry": "Specialty Retail",
        "fin_ccy": fin_ccy, "px_ccy": "IDR",
        "px": px, "price": price_level, "price_date": idx[-1].date(),
        "info": {}, "flags": FlagLog(), "src": {}, "ok": True, "error": None,
        "S": {"ais": ais, "qis": qis, "abs": abs_, "qbs": qbs,
              "acf": acf, "qcf": qcf},
        "fx": None,
    }
    if fin_ccy != "IDR":
        d["fx"] = pd.Series(16_000.0, index=idx)
    return d


def main():
    print("=" * 74)
    print("VALIDASI RELATIVE HISTORICAL - DATA SINTETIS")
    print("=" * 74)

    # ---- R1: normalisasi ticker ----
    print("\n[R1] Normalisasi ticker")
    got = [norm_ticker(x) for x in ["buva", " BUVA ", "BUVA.JK", "asii"]]
    print(f"  {got}")
    assert got == ["BUVA.JK", "BUVA.JK", "BUVA.JK", "ASII.JK"]

    # ---- R1: BUG FIX find_row ----
    print("\n[R1] Perbaikan bug pencocokan label")
    df_trap = pd.DataFrame(index=["Cost Of Revenue", "Operating Income"],
                           data={pd.Timestamp("2025-12-31"): [100.0, 50.0]})
    r = find_row(df_trap, ["Total Revenue", "Operating Revenue", "Revenue"])
    print(f"  Hanya ada 'Cost Of Revenue', dicari Revenue -> "
          f"{r.name if r is not None else None}")
    assert r is None, "Cost Of Revenue TIDAK boleh dianggap Revenue"

    df_ok = pd.DataFrame(index=["Cost Of Revenue", "Total Revenue"],
                         data={pd.Timestamp("2025-12-31"): [100.0, 400.0]})
    r2 = find_row(df_ok, ["Total Revenue", "Operating Revenue", "Revenue"])
    print(f"  Ada 'Total Revenue' -> {r2.name}")
    assert r2.name == "Total Revenue"

    # ---- R2: driver TTM ----
    d = make_fake()
    s = build_drivers(d)
    print("\n[R2] Driver TTM")
    print(f"  Revenue TTM   : {s['rev'].iloc[-1]/1e9:>10,.0f} bn  (harap 4,000)")
    print(f"  Net income TTM: {s['ni'].iloc[-1]/1e9:>10,.0f} bn  (harap 400)")
    print(f"  EBITDA TTM    : {s['ebitda'].iloc[-1]/1e9:>10,.0f} bn  "
          f"(harap 800 = OpInc 600 + D&A 200)")
    print(f"  Sumber EBITDA : {d['src']['ebitda']}")
    assert abs(s["rev"].iloc[-1] - 4_000e9) < 1e6
    assert abs(s["ni"].iloc[-1] - 400e9) < 1e6
    assert abs(s["ebitda"].iloc[-1] - 800e9) < 1e6, "EBITDA = OpInc + D&A"

    # ---- R3: seri multiple ----
    h = build_series(d, s)
    h1 = window_slice(h)
    last = h.iloc[-1]
    print("\n[R3] Multiple terakhir")
    eps_m = 400e9 / SHARES
    bvps_m = 5_000e9 / SHARES
    nd_m = 2_000e9 - 500e9
    ev_m = 1000.0 * SHARES + nd_m
    print(f"  EPS  : {last['EPS']:>8,.2f}  (manual {eps_m:,.2f})")
    print(f"  BVPS : {last['BVPS']:>8,.2f}  (manual {bvps_m:,.2f})")
    print(f"  P/E  : {last['P/E']:>8,.2f}  (manual {1000.0/eps_m:,.2f})")
    print(f"  P/BV : {last['P/BV']:>8,.2f}  (manual {1000.0/bvps_m:,.2f})")
    print(f"  EV   : {last['EV']/1e12:>8,.2f} tn  (manual {ev_m/1e12:,.2f} tn)")
    print(f"  EV/EBITDA: {last['EV/EBITDA']:>4,.2f}  (manual {ev_m/800e9:,.2f})")
    print(f"  EV/Sales : {last['EV/Sales']:>4,.2f}  (manual {ev_m/4_000e9:,.2f})")
    assert abs(last["EPS"] - eps_m) < 1e-9
    assert abs(last["P/E"] - 1000.0 / eps_m) < 1e-9
    assert abs(last["EV"] - ev_m) < 1e3
    assert abs(last["EV/EBITDA"] - ev_m / 800e9) < 1e-9

    # ---- R3: konversi FX ----
    print("\n[R3] Konversi mata uang")
    d_usd = make_fake(fin_ccy="USD")
    s_usd = build_drivers(d_usd)
    h_usd = build_series(d_usd, s_usd)
    pe_usd = float(h_usd["P/E"].iloc[-1])
    print(f"  Lapkeu USD, kurs 16,000 -> P/E {pe_usd:,.4f}")
    print(f"  P/E versi IDR {float(last['P/E']):,.4f} dibagi 16,000 = "
          f"{float(last['P/E'])/16000:,.4f}")
    assert abs(pe_usd - float(last["P/E"]) / 16000) < 1e-9, \
        "P/E USD harus = P/E IDR / kurs"

    # ---- R3: implied price ----
    print("\n[R3] Implied price")
    cur = {k: float(last.get(k)) for k in
           ["EPS", "BVPS", "EBITDA", "Rev", "Shares", "NetDebt", "MI", "EV",
            "MktCap", "Price", "NI", "Equity", "Debt", "Cash"]}
    for m in MULTIPLES:
        cur[m] = float(last.get(m))

    ip_pe = implied_price(30.0, "P/E", cur)
    print(f"  P/E 30x  -> IDR {ip_pe:,.2f}  (manual {30.0*eps_m:,.2f})")
    assert abs(ip_pe - 30.0 * eps_m) < 1e-9

    ip_ev = implied_price(15.0, "EV/EBITDA", cur)
    manual_ev = (15.0 * 800e9 - nd_m - 0) / SHARES
    print(f"  EV/EBITDA 15x -> IDR {ip_ev:,.2f}  (manual {manual_ev:,.2f})")
    assert abs(ip_ev - manual_ev) < 1e-9, "EV multiple harus dikurangi net debt"

    # ---- R4: scorecard ----
    print("\n[R4] Scorecard")
    ev_map, head = run_scorecard(h1, cur, d)
    for m in MULTIPLES:
        e = ev_map[m]
        print(f"  {m:<10} base {e['base']:>3.0f} | stab {e['stability']:>5.1f} | "
              f"drv {e['driver_pos']:>2.0f} | obs {e['observation']:>4.1f} | "
              f"total {e['score']:>5.1f} | {e['status']}")
    print(f"  HEADLINE: {head}")
    assert head == "EV/EBITDA", "sektor default harus memilih EV/EBITDA"
    # harga dan driver konstan -> CV nol -> stability penuh
    assert abs(ev_map["EV/EBITDA"]["stability"] - 25.0) < 1e-6

    # ---- R4: emiten finansial harus menolak EV ----
    print("\n[R4] Emiten finansial")
    d_fin = make_fake()
    d_fin["sector"] = "Financial Services"
    d_fin["industry"] = "Banks - Regional"
    s_fin = build_drivers(d_fin)
    h_fin = window_slice(build_series(d_fin, s_fin))
    ev_fin, head_fin = run_scorecard(h_fin, cur, d_fin)
    print(f"  bucket: {sector_bucket(d_fin)}")
    for m in ["EV/EBITDA", "EV/Sales"]:
        print(f"  {m:<10} score {ev_fin[m]['score']:.1f} | {ev_fin[m]['status']}")
    print(f"  HEADLINE: {head_fin}")
    assert ev_fin["EV/EBITDA"]["score"] == 0
    assert ev_fin["EV/Sales"]["score"] == 0
    assert head_fin == "P/BV", "bank harus memilih P/BV"

    # ---- R4: driver negatif menggugurkan ----
    print("\n[R4] Driver negatif")
    cur_loss = dict(cur)
    cur_loss["EPS"] = -50.0
    e_loss = evaluate("P/E", h1, cur_loss, d)
    print(f"  EPS negatif -> P/E score {e_loss['score']:.1f} | {e_loss['status']}")
    assert e_loss["score"] == 0

    # ---- R5: verdict ----
    print("\n[R5] Verdict")
    rows = build_multiple_rows(h1, cur, d)
    verdict = build_verdict(h1, cur, ev_map, head, rows)
    print(f"  headline    : {verdict['headline']}")
    print(f"  price now   : IDR {verdict['price']:,.0f}")
    print(f"  implied     : IDR {verdict['implied_low']:,.0f} - "
          f"IDR {verdict['implied_high']:,.0f}")
    print(f"  upside      : {verdict['upside_low']*100:+.1f}% s/d "
          f"{verdict['upside_high']*100:+.1f}%")
    print(f"  driver 1Y   : {verdict['driver_change']*100:+.1f}%")
    assert verdict["valid"]
    # multiple konstan -> implied price harus sama dengan harga sekarang
    assert abs(verdict["implied_low"] - verdict["price"]) < 1.0, \
        "multiple konstan berarti tidak ada upside"

    # ---- R3: perubahan jumlah saham ----
    print("\n[R3] Deteksi perubahan jumlah saham")
    d2 = make_fake()
    d2["S"]["qbs"].loc["Ordinary Shares Number", pd.Timestamp("2026-06-30")] = SHARES * 1.30
    s2 = build_drivers(d2)
    h2 = window_slice(build_series(d2, s2))
    chg = check_share_stability(h2, d2["flags"])
    print(f"  perubahan {chg*100:+.1f}%")
    w = [x for x in d2["flags"].render().split("\n") if "saham" in x.lower()]
    print(f"  {w[0][:110] if w else 'tidak ada flag'}")
    assert abs(chg - 0.30) < 1e-9 and len(w) > 0

    # ---- flag ----
    print("\n[Flag data]")
    print(d.flags.render() if hasattr(d, "flags") else d["flags"].render())

    print("\n" + "=" * 74)
    print("SELURUH ASSERTION RELATIVE LULUS")
    print("=" * 74)


if __name__ == "__main__":
    main()
