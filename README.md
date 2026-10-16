# 🌧️ GSMaP Explorer

A desktop-based GSMaP rainfall data processing and visualization tool focused on Indonesia.

---

## 🌍 Description

**GSMaP Explorer** is a desktop-based application designed to process and analyze GSMaP rainfall data in NetCDF (`.nc`) format.

Users can download GSMaP datasets from the HESLab-UPER data portal:

🔗 https://heslab-uper.com/data/hujan-satelit

After downloading the data, users can process it locally on their computer. The application supports rainfall visualization, spatial subsetting, and data export to CSV.

The current implementation is focused on rainfall data over Indonesia.

---

## 🇮🇩 Deskripsi

**GSMaP Explorer** adalah aplikasi berbasis desktop yang digunakan untuk pengolahan dan analisis data curah hujan GSMaP dalam format NetCDF (`.nc`).

Data GSMaP dapat diunduh melalui portal data HESLab-UPER:

🔗 https://heslab-uper.com/data/hujan-satelit

Setelah data diunduh, data dapat diolah secara lokal di komputer pengguna, termasuk visualisasi peta hujan, subset wilayah, dan ekspor data ke CSV.

Aplikasi ini difokuskan pada wilayah Indonesia.

---

## ✨ Features

- Processing GSMaP NetCDF rainfall data  
- Rainfall map visualization  
- Spatial subsetting based on extent or shapefile  
- Export rainfall data to CSV  
- Areal rainfall per sub-watershed using Thiessen polygons  
- Design rainfall: return periods with Chi-square and Smirnov-Kolmogorov tests  
- Rainfall intensity: Mononobe and IDF curves from hourly data  
- Hourly rainfall characteristics: diurnal cycle and rain events  

---

## 🧰 Fitur

- Pengolahan data curah hujan GSMaP (NetCDF)  
- Visualisasi peta distribusi hujan  
- Subset wilayah berdasarkan extent atau shapefile  
- Ekspor data ke format CSV  
- Hujan wilayah per sub-DAS dengan poligon Thiessen  
- Hujan rancangan: kala ulang dengan uji Chi-kuadrat dan Smirnov-Kolmogorov  
- Intensitas hujan: Mononobe dan kurva IDF dari data jam-an  
- Karakteristik hujan jam-jaman: siklus diurnal dan kejadian hujan  

---

## ⚙️ Installation

Install the required dependencies using one of the following options:

**Option 1: pip**

```bash
pip install -r requirements.txt
```

**Option 2: conda**

```bash
conda env update -n base -f environment.yml
```

---

## ✅ Usage

### 1. Prepare the data

Download GSMaP NetCDF (`.nc`) data from:

🔗 https://heslab-uper.com/data/hujan-satelit

Place the monthly `.nc` files in `data/raw/` (or set `path_nc` to their folder).
Data files are not included in this repository.

### 2. Configure the input

Edit the input configuration file:

```text
config/input.txt
```

Main keys:

- `path_nc` — folder containing the `.nc` files
- `path_out` — output folder
- `path_shp` — watershed/sub-watershed shapefile, or `None` to use the bounding box (`min_lon`, `max_lon`, `min_lat`, `max_lat`)
- `das_field` — shapefile attribute that identifies each sub-watershed (used by `thiessen`)
- `start_date`, `end_date` — period (`YYYY-MM-DD`)
- `wilayah_waktu` — local time zone of the output (`WIB`, `WITA`, `WIT`)

The analysis keys (fixed day, frequency analysis, intensity, rain events)
are explained by the comments in `config/input.txt`. They are checked before
any data is read; a wrong key stops the program with its name.

**Time convention.** GSMaP time is UTC and marks the start of each hour.
Output times are local and mark the end of the hour (rain that has fallen):
UTC + 8 h for WIB (7 h time zone + 1 h), + 9 h for WITA, + 10 h for WIT.
Daily totals run from `day_start_hour` to the same hour next day (07.00–07.00
by default), dated by the day the window starts.

### 3. Run the program

**Option 1: Windows**

```bat
run.bat
```

**Option 2: Command Line**

```bash
python run.py --mode extract
```

Available modes:

- `extract` — Export rainfall data to CSV
- `visualize` — Generate rainfall maps
- `thiessen` — Export CSV, then compute areal rainfall per sub-watershed
- `analysis` — Export CSV (and Thiessen when a shapefile is given), then design rainfall, intensity and hourly characteristics
- `series` — Rainfall series at points, in a box, or in the bounds of a shapefile (asks on screen)
- `all` — Run extraction, visualization, Thiessen (when a shapefile is given) and analysis

Running `run.py` (or `run.bat`) without `--mode` shows a menu. Another
config file can be given with `--config`, e.g.

```bash
python run.py --mode series --config my_job/input.txt
```

### Series mode

Asks on screen, with the config values as defaults (press Enter to keep one):

1. **Product** — every `NC` folder under `gsmap_archive_root` (e.g. `STD/V8/GA`,
   `NRT/V8/NGA`, `NOW`); with `gsmap_archive_root = None`, the files in `path_nc`.
   Monthly files may be named `*_YYYY_MM.nc` (portal) or `*_YYYYMM.nc`
   (archive, also in year subfolders).
2. **Region** — `points` (CSV `path_points` with columns `name`, `lat`, `lon`,
   e.g. `config/points.csv`), `box` (`min_lon`, `max_lon`, `min_lat`, `max_lat`)
   or `shape` (the total bounds of `path_shp`).
3. **Period** — first and last rain day (local, `day_start_hour` to the same hour next day).
4. **Outputs** — hourly, daily, monthly, yearly (one or more).
5. **Time zone** — WIB, WITA, WIT. Labels mark the end of the recorded hour,
   so the offset is the zone + 1 h: UTC + 8 h (WIB), + 9 h (WITA), + 10 h (WIT).

`--no-menu` takes the config values without asking (for scheduled runs).
No interpolation: each column is one 0.1-degree cell; points in the same
cell get identical series, boxes and shapes take every cell they overlap.
Results in `<path_out>/series_output/<product>_<region>_<start>_<end>_<zone>/`:

| File | Content |
|---|---|
| `cells.csv` | each column: its cell centre (and the point, and the points sharing that cell) |
| `rain_hourly.csv` | hourly rainfall (mm), local end-of-hour labels, missing hours empty |
| `rain_daily.csv` | daily totals (mm); empty when an hour of the day is missing |
| `rain_monthly.csv` | monthly totals of the rain days (mm); empty when a day is missing or the month is not wholly in the period |
| `rain_yearly.csv` | yearly totals, same rule |
| `choices.txt` | the choices of the run and a summary |

### Thiessen mode

Requires `path_shp` (a polygon shapefile) and `das_field`. Thiessen polygons
are built from the GSMaP grid points, clipped to each sub-watershed, and
weighted by geodesic area. Results in `<path_out>/csv_output/`:

| File | Content |
|---|---|
| `koordinat.csv` | grid-point names and coordinates |
| `hujan_grid.csv` | hourly rainfall per grid point (mm) |
| `hujan_area_hourly.csv` | hourly areal rainfall per sub-watershed (mm) |
| `hujan_area_daily.csv` | daily totals (fixed day, `day_start_hour`) |
| `hujan_area_monthly.csv` | monthly totals of those days |
| `hujan_max_daily_yearly.csv` | annual maximum daily rainfall |

### Analysis mode

Runs on the sub-watershed series (`hujan_area_hourly.csv`) when `path_shp` is
a shapefile, or on every grid point (`hujan_grid.csv`) when `path_shp = None`.
Hours missing from the `.nc` files are kept as missing, never as zero. Results
in `<path_out>/analysis_output/`:

| File | Content |
|---|---|
| `annual_maxima.csv` | annual maximum per series and duration (`daily`, sliding `1h`, `2h`, ...), with the valid fraction of the year |
| `distribution_fits.csv` | every distribution: parameters, Chi-square and Smirnov-Kolmogorov results, selected |
| `return_levels_all.csv` | rainfall per return period for every distribution (mm) |
| `design_rainfall.csv` | rainfall per return period of the selected distribution (mm), or a note why there is none |
| `intensity.csv` | intensity per duration and return period (mm/h): reference, each formula, selected |
| `idf_parameters.csv` | IDF formula parameters (Talbot, Sherman, Ishiguro) and the selected one |
| `diurnal_cycle.csv` | per local hour (and month): mean rain, wet-hour fraction, mean rain of wet hours |
| `rain_events.csv` | every rain event: start, end, duration, depth, peak, complete |
| `rain_event_summary.csv` | event statistics per year and over all years (complete events only) |

The selected distribution passes both Chi-square and Smirnov-Kolmogorov and
has the smallest Delta max; when none passes both, no design value is given.
A series needs at least `min_years` complete years. The `idf` method needs
hourly durations (`idf_durations_hours`); intensities are not extrapolated
outside them. Durations are analysed separately, so for large return periods
a longer duration can occasionally give less rain than a shorter one.

