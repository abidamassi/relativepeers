"""
=============================================================================
REL CONFIG - PUSAT PARAMETER RELATIVE HISTORICAL
=============================================================================
TUJUAN  : Menyimpan seluruh parameter, bobot scorecard, dan kamus label
          laporan keuangan di satu tempat.

METODE  : Relative valuation terhadap SEJARAH MULTIPLE EMITEN ITU SENDIRI,
          bukan terhadap peer. Asumsi dasarnya multiple cenderung kembali
          ke rata-ratanya sendiri (mean reversion), dan driver fundamental
          dianggap tidak berubah saat menghitung implied price.

OUTPUT  : REL_CONFIG, SCORE_WEIGHTS, KEYS, MULTIPLES.
=============================================================================
"""

REL_CONFIG = {
    # Jendela sejarah multiple. Dikunci 1 tahun, tidak ada opsi di sidebar.
    "window_years":   1.0,

    # Rata-rata aritmetik, bukan harmonik. Untuk own-history, penyebut
    # multiple (EPS, BVPS, EBITDA) relatif konstan dalam satu jendela,
    # sehingga bias agregasi yang biasanya mengganggu rata-rata aritmetik
    # pada perbandingan lintas emiten tidak muncul di sini.
    "use_harmonic":   False,

    # Minimum observasi harian agar satu multiple dianggap layak dipakai.
    # Satu tahun perdagangan kira-kira 245 hari, jadi 120 berarti separuh.
    "min_obs":        120,

    # Panjang riwayat harga yang ditarik.
    "price_period":   "6y",

    # Ambang peringatan untuk uji kewajaran.
    "warn_cv":            0.60,   # volatilitas multiple
    "warn_share_change":  0.05,   # perubahan jumlah saham dalam jendela
    "review_upside":      1.00,   # upside di atas ini ditandai Review Required
    "review_downside":   -0.50,
}

# -----------------------------------------------------------------------
# BOBOT SCORECARD
# -----------------------------------------------------------------------
# Base score menurut relevansi multiple terhadap sektor, ditambah komponen
# yang menilai apakah datanya layak dipakai.
SCORE_WEIGHTS = {
    "stability_max":  25,   # semakin stabil multiple, semakin bermakna rata-ratanya
    "driver_positive": 15,  # driver harus positif di seluruh jendela
    "observation_max": 10,  # kecukupan jumlah observasi
    "obs_full":       200,  # jumlah observasi untuk mendapat poin penuh
}

BASE_SCORE = {
    "financial": {"P/BV": 45, "P/E": 35, "EV/EBITDA": 0,  "EV/Sales": 0},
    "property":  {"P/BV": 40, "P/E": 25, "EV/EBITDA": 25, "EV/Sales": 10},
    "default":   {"P/BV": 22, "P/E": 28, "EV/EBITDA": 40, "EV/Sales": 15},
}

FINANCIAL_KEYWORDS = ["bank", "insurance", "asuransi", "capital markets",
                      "financial", "credit services", "asset management"]
PROPERTY_KEYWORDS = ["real estate", "property"]

# -----------------------------------------------------------------------
# MULTIPLE
# -----------------------------------------------------------------------
MULTIPLES = ["P/E", "P/BV", "EV/EBITDA", "EV/Sales"]
DRIVER_OF = {"P/E": "EPS", "P/BV": "BVPS", "EV/EBITDA": "EBITDA", "EV/Sales": "Rev"}
IS_EV = {"P/E": False, "P/BV": False, "EV/EBITDA": True, "EV/Sales": True}

# -----------------------------------------------------------------------
# KAMUS LABEL YFINANCE
# -----------------------------------------------------------------------
# Setiap entri adalah daftar grup. Grup dengan lebih dari satu daftar akan
# DIJUMLAHKAN, dipakai untuk utang jangka pendek ditambah jangka panjang.
KEYS = {
    "rev":    [["Total Revenue", "Operating Revenue", "Revenue"]],
    "ni":     [["Net Income Common Stockholders", "Net Income",
                "Net Income Continuous Operations"]],
    "ebitda": [["EBITDA", "Normalized EBITDA"]],
    "opinc":  [["Operating Income", "EBIT"]],
    "da":     [["Depreciation And Amortization",
                "Depreciation Amortization Depletion", "Depreciation"]],
    "eq":     [["Stockholders Equity", "Total Stockholder Equity",
                "Common Stock Equity"]],
    "debt":   [["Total Debt"]],
    "debt_c": [["Current Debt And Capital Lease Obligation", "Current Debt",
                "Short Term Debt"],
               ["Long Term Debt And Capital Lease Obligation", "Long Term Debt"]],
    "cash":   [["Cash Cash Equivalents And Short Term Investments",
                "Cash And Cash Equivalents", "Cash Financial"]],
    "mi":     [["Minority Interest"]],
    "sh":     [["Ordinary Shares Number", "Share Issued"]],
}

# Kata yang TIDAK boleh ikut tertangkap saat pencocokan longgar.
# Tanpa ini, kunci "Revenue" bisa cocok ke baris "Cost Of Revenue" dan
# seluruh perhitungan EV/Sales menjadi salah tanpa peringatan apa pun.
LABEL_BLOCKLIST = ["cost of", "expense", "per share", "average", "diluted",
                   "basic", "growth", "margin", "tax", "interest"]

DISCLAIMER = (
    "This output is produced by an automated model based on public yfinance "
    "data. The method used is relative valuation against the issuer's own "
    "multiple history, not against peers, so the result depends entirely on "
    "the assumption that the multiple will revert to its own average. "
    "Figures have not been reconciled against official financial statements "
    "and this is not investment advice."
)
