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

---

## 🧰 Fitur

- Pengolahan data curah hujan GSMaP (NetCDF)  
- Visualisasi peta distribusi hujan  
- Subset wilayah berdasarkan extent atau shapefile  
- Ekspor data ke format CSV  

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

### 2. Configure the input

Edit the input configuration file:

```text
config/input.txt
```

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
- `all` — Run both extraction and visualization

