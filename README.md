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

---

## 🧰 Fitur

- Pengolahan data curah hujan GSMaP (NetCDF)  
- Visualisasi peta distribusi hujan  
- Subset wilayah berdasarkan extent atau shapefile  
- Ekspor data ke format CSV  
- Hujan wilayah per sub-DAS dengan poligon Thiessen  

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
- `all` — Run extraction, visualization, and Thiessen analysis

Running `run.py` (or `run.bat`) without `--mode` shows a menu.

### Thiessen mode

Requires `path_shp` (a polygon shapefile) and `das_field`. Thiessen polygons
are built from the GSMaP grid points, clipped to each sub-watershed, and
weighted by geodesic area. Results in `<path_out>/csv_output/`:

| File | Content |
|---|---|
| `koordinat.csv` | grid-point names and coordinates |
| `hujan_grid.csv` | hourly rainfall per grid point (mm) |
| `hujan_area_hourly.csv` | hourly areal rainfall per sub-watershed (mm) |
| `hujan_area_daily.csv` | daily totals |
| `hujan_area_monthly.csv` | monthly totals |
| `hujan_max_daily_yearly.csv` | annual maximum daily rainfall |

