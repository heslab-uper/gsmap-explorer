# 🌧️ GSMaP Explorer

A desktop tool to extract and map GSMaP rainfall over Indonesia.

---

## 🌍 Description

**GSMaP Explorer** reads monthly GSMaP NetCDF (`.nc`) rainfall files and gives
the rain of a box, of the regions of one or more shapefiles, or at points, as
hourly, daily, monthly and yearly tables and the annual maximum daily rain,
plus rainfall maps and areal rainfall by Thiessen polygons.

Users can download GSMaP datasets from the HESLab-UPER data portal:

🔗 https://heslab-uper.com/data/hujan-satelit

---

## 🇮🇩 Deskripsi

**GSMaP Explorer** membaca berkas hujan GSMaP bulanan (`.nc`) dan menghasilkan
hujan sebuah kotak wilayah, wilayah dari satu atau beberapa shapefile, atau
titik, dalam tabel jam-jaman, harian, bulanan, tahunan dan hujan harian
maksimum per tahun, ditambah peta hujan dan hujan wilayah dengan poligon
Thiessen.

Data GSMaP dapat diunduh melalui portal data HESLab-UPER:

🔗 https://heslab-uper.com/data/hujan-satelit

---

## ✨ Features / Fitur

| Menu | English | Indonesia |
|---|---|---|
| 1. Extract | rain of every grid cell of a box, of the regions of each shapefile, or at points | hujan tiap sel grid di kotak, di wilayah tiap shapefile, atau di titik |
| 2. Visualisasi | hourly, daily, monthly and yearly rain maps with BMKG classes | peta hujan jam-jaman, harian, bulanan, tahunan dengan kelas BMKG |
| 3. Thiessen | areal rain of the regions of each shapefile | hujan wilayah tiap shapefile |

Extract and Thiessen write the same five outputs: hourly, daily, monthly,
yearly rain and the annual maximum daily rain (with its date).

---

## ⚙️ Installation

1. Install **Miniforge** (conda): https://github.com/conda-forge/miniforge
2. Double-click **`install.bat`**. It creates the Python environment in the
   folder `env\` of the program from `environment.yml` (conda-forge, internet
   needed, a few minutes). It ends with `libraries: ok`. Run it again after
   moving the program folder (a conda environment in a folder cannot be moved).

Without conda: `pip install -r requirements.txt` in your own Python, then
`python run.py`.

The map layers (coastline, borders, provinces, places) come from Natural Earth
through cartopy and are downloaded once, at the first map (internet needed).

---

## 🚀 Cara cepat / Quick start

1. Unduh berkas GSMaP `.nc` bulanan ke satu folder per produk (boleh dengan
   subfolder tahun).
2. Klik dua kali **`run.bat`**. Halaman gsmap-explorer terbuka di peramban
   (hanya di komputer ini, tanpa internet); jendela hitam di belakangnya
   biarkan terbuka.
3. Di halaman: **Telusuri** folder data, pilih menu (Extract, Visualisasi,
   Thiessen), wilayah (kotak, shapefile, titik), periode, dan folder hasil.
   Ringkasan muncul sendiri; klik **Jalankan**, ikuti prosesnya, lalu
   **Buka folder** hasil.
4. Pilihan disimpan ke `config\input.local.txt` (tidak masuk git), jadi
   halaman berikutnya terbuka dengan isian terakhir. **Tutup program** bila
   selesai.

English: double-click `run.bat`; a page opens in the browser (local only).
Browse to the data folder, choose the menu, region, period and output folder,
check the summary, click **Jalankan** (run) and open the result folder. The
choices are kept in `config\input.local.txt` (not in git).

---

## 🖱️ Panduan pemakaian / How to use the page

Halaman diisi dari atas ke bawah. Pesan merah di bawah sebuah bagian
menyebut apa yang masih kurang; tombol **Jalankan** baru aktif setelah semua
bagian benar dan ringkasan siap.

**Jendela Telusuri.** Semua tombol *Telusuri* membuka jendela yang sama.
Klik nama folder untuk masuk, **↑** untuk naik satu folder, **Drive** untuk
pindah drive (C:, D:, ...). Untuk memilih *folder*, masuk ke folder itu lalu
klik **Pilih folder ini**; untuk memilih *berkas* (`.shp`, `.csv`), klik
nama berkasnya.

### 1. Folder data GSMaP

Pilih folder yang berisi berkas `.nc` bulanan satu produk, langsung atau di
subfolder tahun (`2015\`, `2016\`, ...). Di bawahnya muncul produk dan bulan
yang tersedia, misalnya `✓ STD_V8_GA, data tersedia 1998-01 .. 2026-09
(345 bulan)`. Dua berkas untuk bulan yang sama ditolak.

### 2. Menu

| Menu | Gunanya | Hasil di folder hasil |
|---|---|---|
| **Extract** | hujan tiap sel grid di kotak, di wilayah shapefile, atau di titik | `extract_output\box`, `extract_output\<nama shapefile>`, `extract_output\points` |
| **Visualisasi** | peta hujan jam-jaman, harian, bulanan, tahunan (kelas BMKG) | `visualization_output\<jenis peta>` |
| **Thiessen** | hujan wilayah tiap poligon shapefile (bobot luas Thiessen) | `thiessen_output\<nama shapefile>` |

### 3. Wilayah

Thiessen selalu memakai shapefile; Extract dan Visualisasi memilih salah satu:

- **Kotak**: isi bujur min/maks dan lintang min/maks dalam derajat desimal
  (bujur timur positif, lintang selatan negatif), misalnya bujur 110.2 ..
  110.6, lintang -8.1 .. -7.6. Program menambah 0.2° di tiap sisi.
- **Shapefile**: klik **+ Tambah shapefile** dan pilih berkas `.shp`.
  Berkas `.shx`, `.dbf` dan `.prj` dengan nama sama harus ada di sebelahnya
  (`.prj` = sistem koordinat; tanpa itu shapefile ditolak). Kartu shapefile
  menampilkan sistem koordinat, jumlah poligon dan wilayah. Pilih **Kolom
  pengenal wilayah**: kolom yang menamai tiap wilayah (poligon dengan nilai
  sama digabung jadi satu wilayah); tiap kolom ditampilkan dengan jumlah
  nilai uniknya dan contohnya. Boleh lebih dari satu shapefile (misalnya DAS
  dan kabupaten); masing-masing mendapat folder hasil sendiri, dinamai dari
  nama berkasnya. **Hapus** melepas shapefile dari daftar (berkasnya tidak
  terhapus).
- **Titik**: pilih berkas `.csv` dengan kolom `name,lat,lon`, contohnya
  `config\points.csv`:

  ```
  name,lat,lon
  Jakarta,-6.175,106.827
  Bandung,-6.917,107.619
  ```

### 4. Periode

Tanggal awal dan akhir adalah *hari hujan* setempat: satu hari hujan
berjalan dari jam awal hari (07.00) sampai 07.00 esok harinya, dan diberi
tanggal hari berakhirnya. Kedua tanggal ikut penuh. Keterangan di bawah
kolom tanggal menyebut jam dan zona waktu yang berlaku.

### 5. Folder hasil

Pilih folder tempat hasil ditulis; subfolder menurut menu (tabel di atas)
dibuat sendiri. Bawaannya `data\output` di folder program, yang tidak masuk
git. Menjalankan ulang dengan wilayah yang sama menimpa berkas di subfolder
itu.

### 6. Lanjutan (boleh dilewati)

Klik **Lanjutan** untuk membuka:

- **Zona waktu**: WIB, WITA, WIT atau UTC (label jam = akhir jam hujan).
- **Jam awal hari hujan** (0-23, bawaan 7).
- **Tabel hujan yang ditulis** (Extract, Thiessen): jam-jaman, harian,
  bulanan, tahunan, maks. harian. Berkas jam-jaman paling besar; matikan
  bila tidak perlu.
- **Jenis peta** (Visualisasi): jam-jaman, harian, bulanan, tahunan. Peta
  jam-jaman membuat satu gambar per jam, jadi pakai untuk periode pendek.

### 7. Ringkasan dan Jalankan

Ringkasan dihitung sendiri setiap isian berubah: wilayah yang dibaca
(dengan margin), periode dalam waktu setempat dan UTC, ukuran (sel × jam),
dan folder hasil. Periksa, lalu klik **Jalankan**. Bila ukurannya sangat
besar (lebih dari 200 juta nilai), halaman memperingatkan: perkecil wilayah
atau periode.

### 8. Proses dan hasil

Selama berjalan isian dikunci dan log tampil di halaman (juga di jendela
hitam). Di akhir muncul `✓ Selesai dalam … detik` atau `✗ Gagal …` dengan
sebabnya, lalu daftar folder hasil beserta jumlah berkas baru; **Buka
folder** membukanya di Explorer. Hanya satu proses pada satu waktu.

Isi folder hasil Extract dan Thiessen: tabel hujan (`rain_hourly.csv`,
`rain_daily.csv`, `rain_monthly.csv`, `rain_yearly.csv`, `rain_max_daily*.csv`;
lihat *The five rain outputs*), `map.png` (sel yang dipakai), `cells.csv`
(Extract) atau `weights.csv` (Thiessen), dan `choices.txt` (pilihan yang
dipakai, untuk dicatat di laporan).

### 9. Selesai

Klik **Tutup program**, atau tutup jendela hitam. Pilihan terakhir tersimpan
di `config\input.local.txt`, jadi `run.bat` berikutnya membuka halaman
dengan isian yang sama.

**Bila ada masalah**

| Gejala | Yang dilakukan |
|---|---|
| Halaman tidak terbuka | salin alamat `http://127.0.0.1:…/` dari jendela hitam ke peramban |
| Jendela hitam langsung tertutup / galat pustaka | jalankan `install.bat` lagi (juga setelah folder program dipindah) |
| *Jalankan aktif setelah ringkasan siap* | masih ada pesan merah di salah satu bagian |
| Shapefile ditolak | `.prj` tidak ada, atau berkas `.shx`/`.dbf` tidak di sebelahnya |
| Halaman tidak merespons setelah jendela hitam ditutup | program sudah berhenti; klik dua kali `run.bat` lagi |

English: fill the page top to bottom (data folder, menu, region, period,
output folder, optional *Lanjutan*); red messages say what is missing.
*Telusuri* opens a file browser: enter a folder and click **Pilih folder
ini**, or click a file to choose it. Check the summary, click **Jalankan**,
follow the log and use **Buka folder** to open the results.

---

## ✅ Usage

### 1. Prepare the data

Put the monthly `.nc` files of one product in one folder, directly or in year
subfolders (`<folder>/2015/gsmap_std_v8_ga_201501.nc`), and set `gsmap_folder`
to it. Files may be named `*_YYYYMM.nc` or `*_YYYY_MM.nc`; two files for the
same month stop the program. Data files are not included in this repository.

### 2. Configure

The page of `run.bat` writes your choices to `config/input.local.txt`; you
normally do not edit any file. That file is not in git, each key there
replaces the same key of `config/input.txt`, and the program prints which keys
came from it. The page changes only the keys it shows (`gsmap_folder`,
`extract_region`, `min_lon` .. `max_lat`, `points_file`, `shape_<name>`,
`start_date`, `end_date`, `output_folder`, `time_zone`, `day_start_hour`,
`rain_outputs`, `map_outputs`) and keeps the other lines and comments of the
file; a `shape_<name>` line removed on the page is removed from the file.

`config/input.txt` holds the defaults of every choice; each key is explained
by its comment and checked before any data is read (a missing or wrong key
stops the program with its name). Keys the page does not show (margin, year
start, map classes and labels, relief) are set there, or in `config/input.local.txt` to keep them out of
git.

Main keys (paths are absolute, or relative to the folder of `run.py`):

| Key | Meaning |
|---|---|
| `gsmap_folder` | folder of one GSMaP product (local config) |
| `shape_<name> = <path> \| <id field>` | one line per shapefile (local config): watersheds or administrative areas with a CRS; `<id field>` names each region, polygons with the same value form one region; `<name>` (a-z, 0-9, _) names the output folder |
| `output_folder` | `data/output`; inside the program folder only under `data/`, so results never reach git |
| `extract_region` | `box` (`min_lon` .. `max_lat`), `shape` (each `shape_<name>`) or `points` (`points_file`, CSV `name,lat,lon`) |
| `region_margin_deg` | degrees added on every side of the box, shapefiles or points (0.2) |
| `start_date`, `end_date` | first and last local rain day (`YYYY-MM-DD`) |
| `time_zone` | `WIB`, `WITA`, `WIT` or `UTC` |
| `rain_outputs` | `hourly, daily, monthly, yearly, max_daily` (one or more) |
| `year_start_month`, `min_valid_fraction` | first month of a year (1 = calendar, 11 = water year); share of days a year needs for its maximum (0.9) |
| `map_*`, `basemap_relief_file` | maps (see *Maps*) |

**Time convention.** GSMaP time is UTC and marks the start of each hour.
Output times mark the end of the hour (rain that has fallen): the time zone
+ 1 h, i.e. UTC + 8 h for WIB, + 9 h for WITA, + 10 h for WIT, + 1 h for UTC.
Daily totals run from `day_start_hour` to the same hour next day (07.00–07.00
in the config), dated by `daily_date_label`: `end` in the config, the day the
window ends (Thursday = Wednesday 07.00 to Thursday 07.00). `start_date` ..
`end_date` are such rain days, so the first and last day are whole.

### 3. Run

Double-click `run.bat` (it uses the Python of `env\`). It starts a small
server on `127.0.0.1` (this computer only, a random port, refused without the
key the page carries) and opens the page in the default browser. The page
checks each field, asks the program for the summary (region read, period,
cells x hours, output folder) and enables **Jalankan** when it is ready. The
log of the run is shown on the page and in the console window; one run at a
time. Close with **Tutup program** or by closing the console window.

Without the browser (scheduled runs, servers):

```bash
python run.py --mode extract --no-menu
```

Modes: `extract`, `visualize`, `thiessen`; they read the config files as they
are. Without `--no-menu` the program prints the summary and asks
`Lanjut? [Y/n]`. `--text-menu` gives the menu in the console instead of the
page. Another config file: `--config my_job/input.txt`.

### The five rain outputs

Extract and Thiessen write, for each column (grid cell, point or region):

| File | Content |
|---|---|
| `rain_hourly.csv` | mm per hour, local end-of-hour labels; missing hours empty |
| `rain_daily.csv` | fixed-day totals (mm); empty when an hour of the day is missing |
| `rain_monthly.csv` | sum of the days of each month; empty unless every day is present and the month is wholly in the period |
| `rain_yearly.csv` | sum of the days of each year (from `year_start_month`), same rule |
| `rain_max_daily.csv` | largest daily rain of each year, when at least `min_valid_fraction` of its days are present |
| `rain_max_daily_date.csv` | the date of that maximum |
| `rain_max_daily_valid.csv` | share of the days of the year that are present |

No interpolation: each grid column is one 0.1-degree cell (about 11 x 11 km),
named by its centre `<lat>_<lon>`, e.g. `-7.85_110.45`, the same in every run.

### Extract

`<output_folder>/extract_output/<box | points | name>/`: the rain outputs, plus

| File | Content |
|---|---|
| `cells.csv` | each column: cell centre; for points also the point and the points sharing its cell; for shapes the regions it touches |
| `map.png` | the cells written over the mean rain of the period |
| `choices.txt` | the settings of the run and a summary |

`box`: every cell of the box + margin. `shape`: every cell sharing an area with
the polygons of each shapefile (one folder per `shape_<name>`). `points`: the
cell holding each point (one column per point, named as in `points_file`).

### Thiessen

`<output_folder>/thiessen_output/<name>/` for each `shape_<name>`: the rain
outputs with one column per region (value of the id field), plus `weights.csv`
(region, cell, geodesic area, weight), `map.png` and `choices.txt`.

Thiessen polygons are built from the grid points around the shapefile (bounds
+ margin), clipped to each region, and weighted by geodesic area; each polygon
takes the rain of the grid point lying in it. An areal value is empty when a
cell with a weight in that region is missing. Regions inside the same cell(s)
get identical rain, and the program says so.

### Maps

`visualize` draws the region of `extract_region` (+ margin), with the polygons
of every `shape_<name>`, as the maps of `map_outputs` in
`<output_folder>/visualization_output/<kind>/`:

| Map | File | Title line |
|---|---|---|
| `hourly` | `hourly/rain_hourly_20260114_0200.png` | 14 Jan 2026, 02.00 WIB (end of the hour) |
| `daily` | `daily/rain_daily_20260114.png` | Rabu, 14 Jan 2026 (13 Jan 07.00 - 14 Jan 07.00 WIB) |
| `monthly` | `monthly/rain_monthly_202601.png` | Januari 2026; only whole months without a missing day |
| `yearly` | `yearly/rain_yearly_2026.png` | 2026; only whole years without a missing day |

Monthly and yearly maps follow the rain outputs exactly; a month or year not
whole in the period is skipped with a note. `hourly` gives one map per hour (a
long period gives thousands of files, about 0.6 s each).

Classes (`map_levels_*`, `map_names_*`): hourly and daily after the BMKG rain
intensity categories (very light 0.1-1 mm/h and 0.5-5 mm/day added), monthly
after the 9 BMKG monthly classes with the groups rendah, menengah, tinggi,
sangat tinggi; the sources are in the config comments. Below the first class
bound a cell is transparent, so the land or relief shows; a cell with
incomplete data is hatched. Layers: shaded relief (optional), land and sea,
rain, coastline, country and province borders, the largest places (Natural
Earth 10m) and the shapefile regions with their labels (when at most
`map_label_max`; regions close together share one label).

**Shaded relief.** Set `basemap_relief_file` in `config/input.local.txt` to a
folder, e.g. `data/basemap` (not in git): when `SR_HR.tif` is not there yet, the
program downloads the Natural Earth 10m shaded relief once (`SR_HR.zip`, 42 MB;
233 MB unpacked) from
https://naturalearth.s3.us-west-2.amazonaws.com/10m_raster/SR_HR.zip and uses
it from then on. A `.tif` path instead uses that file as it is (grayscale,
EPSG:4326). The relief is optional: when it is missing, cannot be downloaded
(e.g. offline) or cannot be read, the program prints a note and draws the maps
without it; a failed download is tried again at the next run.
