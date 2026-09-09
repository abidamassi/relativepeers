# Relative Historical

Relative valuation terhadap sejarah multiple emiten itu sendiri, bukan terhadap
peer. Untuk emiten IDX, empat multiple sekaligus: P/E, P/BV, EV/EBITDA, EV/Sales.

Folder ini berdiri sendiri, tidak butuh folder tool DCF maupun DDM.

## Ide dasarnya

Setiap hari perdagangan dihitung ulang keempat multiple emiten. Dari jendela satu
tahun terakhir diambil rata-rata dan mediannya, lalu dihitung berapa harga saham
seandainya multiple kembali ke angka itu, dengan driver fundamental dianggap tetap.

Satu multiple dipilih sebagai patokan lewat scorecard, bukan lewat preferensi.

## Cara pakai

```bash
python -m venv venv
venv\Scripts\activate.bat        # Windows CMD
pip install -r requirements.txt

python test_relative.py          # validasi rumus tanpa jaringan
streamlit run rel_app.py         # jalankan web app
```

Sidebar hanya berisi kotak ticker dan tombol Run analysis. Seluruh parameter
dikunci di `rel_config.py`.

## Peta modul

| File | Section | Isi |
|---|---|---|
| `rel_config.py` | - | Parameter, bobot scorecard, kamus label, daftar blokir |
| `r01_fetch.py` | R1 | Harga, laporan keuangan, kurs harian, pencarian label |
| `r02_drivers.py` | R2 | Seri TTM dengan fallback berlapis dan pelacakan sumber |
| `r03_multiples.py` | R3 | Seri multiple harian, implied price, uji stabilitas saham |
| `r04_scorecard.py` | R4 | Pemilihan headline multiple |
| `rel_main.py` | R5 | Orkestrator, tabel keluaran, verdict |
| `rel_charts.py` | UI | Panel 4 multiple dan bar implied price |
| `rel_app.py` | UI | Aplikasi Streamlit |
| `theme.py` | UI | Design token navy/ice blue, CSS, Poppins |
| `test_relative.py` | - | Validasi dengan data sintetis |

## Scorecard pemilihan headline

```
Skor = Base (sektor) + Stability (25) + Driver positif (15) + Observasi (10)
```

Base menurut sektor:

| Bucket | P/BV | P/E | EV/EBITDA | EV/Sales |
|---|---|---|---|---|
| Financial | 45 | 35 | 0 | 0 |
| Property | 40 | 25 | 25 | 10 |
| Lainnya | 22 | 28 | 40 | 15 |

Syarat gugur, skor menjadi nol:

- Multiple berbasis EV pada emiten finansial. Bagi bank, utang adalah bahan baku
  bukan pendanaan, sehingga Enterprise Value tidak terdefinisi dengan baik.
- Driver saat ini tidak positif. P/E dari laba negatif tidak punya arti.
- Observasi kurang dari 120 hari dalam jendela.

## Rumus

```
Net Debt         = Total Debt - Kas
Enterprise Value = Market Cap + Net Debt + Minority Interest

P/E       = Harga / EPS          (hanya bila EPS > 0)
P/BV      = Harga / BVPS         (hanya bila BVPS > 0)
EV/EBITDA = EV / EBITDA          (hanya bila EBITDA > 0)
EV/Sales  = EV / Revenue         (hanya bila Revenue > 0)

Implied price, multiple ekuitas     = multiple benchmark x driver
Implied price, multiple enterprise  = (multiple x driver - Net Debt - MI) / saham
```

## Perbedaan dari skrip asal

| Perbaikan | Sebab |
|---|---|
| Daftar blokir label | Pencocokan longgar lama bisa mengambil baris `Cost Of Revenue` sebagai Revenue ketika `Total Revenue` tidak ada, membuat EV/Sales salah tanpa peringatan. Sekarang label yang mengandung kata seperti "cost of" dan "expense" ditolak, dan bila ada beberapa kandidat dipilih yang labelnya terpendek. |
| Deteksi perubahan jumlah saham | Rights issue atau buyback di dalam jendela membuat multiple sebelum dan sesudahnya tidak sebanding. Sekarang ditandai. |
| Perbaikan `xref` subplot | Plotly menamai sumbu subplot pertama `x`, bukan `x1`. Versi lama akan gagal merender seluruh chart bila ada satu multiple yang datanya kurang. |
| Peringatan sumber info dict | Angka dari info dict hanya satu titik pada tanggal terakhir, sehingga multiple yang bergantung padanya menjadi garis datar dan statistik sejarahnya tidak bermakna. Sekarang diberi flag. |
| `ffill()` menggantikan `fillna(method="ffill")` | Sudah usang di pandas 2.x |

## Keterbatasan

- Membandingkan emiten dengan masa lalunya sendiri, bukan dengan peer. Kalau
  seluruh sektor mengalami rerating, patokannya ikut bergeser dan sinyalnya hilang.
- Implied price mengasumsikan driver tidak berubah. Padahal multiple biasanya turun
  justru karena pasar memperkirakan drivernya akan turun, sehingga multiple yang
  terlihat murah bisa jadi derating yang benar, bukan peluang.
- Jendela satu tahun pendek. Tidak bisa membedakan lembah siklus dari rerating
  struktural.
- Pos laporan keuangan ditahan datar antar tanggal rilis, sehingga multiple
  melompat pada hari rilis. Sebagian volatilitas berasal dari jadwal pelaporan.
- Mean reversion adalah asumsi, bukan hukum.

## Disclaimer

Disclaimer On - Abida Massi Armand. Untuk keperluan analisis internal, bukan
rekomendasi investasi.
