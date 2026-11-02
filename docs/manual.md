# Petunjuk Pemakaian GSMaP Explorer

Program untuk mengambil dan memetakan hujan satelit GSMaP di Indonesia.

Petunjuk ini untuk gsmap-explorer dengan tiga menu: **Extract**,
**Visualisasi**, dan **Thiessen**.

[TOC]

## 1. Tentang program

GSMaP Explorer membaca berkas hujan GSMaP bulanan (`.nc`) dan menghasilkan:

- hujan tiap sel grid di sebuah **kotak** wilayah, di wilayah dari satu atau
  beberapa **shapefile**, atau di **titik**;
- tabel hujan **jam-jaman, harian, bulanan, tahunan**, dan **hujan harian
  maksimum per tahun**;
- **peta hujan** jam-jaman, harian, bulanan, dan tahunan dengan kelas BMKG;
- **hujan wilayah** dengan poligon Thiessen.

Program berjalan di komputer Anda sendiri. Halamannya dibuka di peramban,
tetapi tidak dikirim ke internet.

Data GSMaP dapat diunduh dari portal data HESLab-UPER:
<https://heslab-uper.com/data/hujan-satelit>

## 2. Yang dibutuhkan

| Kebutuhan | Keterangan |
|---|---|
| Windows | `install.bat` dan `run.bat` adalah skrip Windows |
| Miniforge (conda) | <https://github.com/conda-forge/miniforge> |
| Internet | saat pemasangan (beberapa menit) dan saat peta pertama dibuat (lapisan peta Natural Earth diunduh sekali) |
| Data GSMaP | berkas `.nc` bulanan, satu folder per produk |

## 3. Pemasangan

1. Pasang **Miniforge** dari alamat di atas, dengan pilihan bawaan.
2. Ekstrak folder program ke tempat yang tetap, misalnya
   `D:\Program\gsmap-explorer`.
3. Klik dua kali **`install.bat`**.

Satu klik itu mengerjakan semuanya:

1. mencari Miniforge, baik yang dipasang untuk satu pengguna maupun untuk
   semua pengguna (`%USERPROFILE%\miniforge3`, `%LOCALAPPDATA%\miniforge3`,
   `%ProgramData%\miniforge3`), atau conda di PATH;
2. membuat lingkungan Python di folder `env\` di dalam folder program, dari
   daftar pustaka di `environment.yml`. Semua pustaka (numpy, pandas,
   matplotlib, netCDF4, cartopy, geopandas, shapely, pyproj, rasterio)
   diunduh dan dipasang otomatis dari conda-forge; Anda tidak perlu
   memasangnya satu per satu;
3. memeriksa semua pustaka bisa dipakai (`libraries: ok`);
4. mengunduh lapisan peta Natural Earth (laut, darat, garis pantai, batas
   negara dan provinsi, kota), sehingga peta pertama tidak perlu internet.

Pemasangan berakhir dengan baris:

```
libraries: ok
Natural Earth map layers:
  ok   ocean
  ...
Installed. Next: copy config\input.local.example.txt to config\input.local.txt,
fill in gsmap_folder, then double-click run.bat.
Petunjuk lengkap: docs\manual.pdf
```

Bila lapisan peta gagal diunduh (misalnya tanpa internet), pemasangan tetap
selesai dengan catatan; lapisan itu diunduh saat peta pertama dibuat.

Langkah "copy" pada pesan itu boleh dilewati: halaman program menulis
pilihan Anda ke `config\input.local.txt` (bagian 6).

**Bila folder program dipindah**, jalankan `install.bat` lagi. Lingkungan
conda di dalam folder tidak bisa dipindah.

**Bila conda tidak ditemukan** (Miniforge dipasang di folder lain), buka
*Miniforge Prompt* lalu jalankan `install.bat` dari sana.

**Tanpa conda** (Python milik sendiri):

```
pip install -r requirements.txt
python run.py
```

## 4. Menyiapkan data

Taruh berkas `.nc` bulanan **satu produk** di satu folder, langsung atau di
subfolder tahun:

```
D:\GSMaP\STD_V8_GA\2015\gsmap_std_v8_ga_201501.nc
D:\GSMaP\STD_V8_GA\2015\gsmap_std_v8_ga_201502.nc
D:\GSMaP\STD_V8_GA\2016\...
```

- Nama berkas berakhir `_YYYYMM.nc` atau `_YYYY_MM.nc`.
- Dua berkas untuk bulan yang sama ditolak. Jangan mencampur produk (misalnya
  NRT dan Standard) di satu folder.
- Berkas data tidak disertakan dalam program.

## 5. Menjalankan program

1. Klik dua kali **`run.bat`**.
2. Jendela hitam muncul, lalu halaman gsmap-explorer terbuka di peramban
   bawaan. **Biarkan jendela hitam terbuka** selama program dipakai; menutupnya
   menghentikan program.
3. Isi halaman dari atas ke bawah (bagian 6).
4. Bila selesai, klik **Tutup program**.

Halaman hanya bisa dibuka dari komputer ini (alamat `http://127.0.0.1:…`).

## 6. Mengisi halaman

Halaman diisi dari atas ke bawah. Pesan merah di bawah sebuah bagian
menyebut apa yang masih kurang. Tombol **Jalankan** baru aktif setelah semua
bagian benar dan ringkasan siap.

### 6.1 Jendela Telusuri

Semua tombol **Telusuri** membuka jendela yang sama:

- klik nama folder untuk masuk ke dalamnya;
- **↑** naik satu folder;
- **Drive** pindah drive (C:, D:, …);
- untuk memilih **folder**: masuk ke folder itu, lalu klik **Pilih folder
  ini**;
- untuk memilih **berkas** (`.shp`, `.csv`): klik nama berkasnya.

### 6.2 Folder data GSMaP

Pilih folder data dari bagian 4. Di bawahnya muncul produk dan bulan yang
tersedia, misalnya:

```
✓ STD_V8_GA, data tersedia 1998-01 .. 2026-09 (345 bulan)
```

### 6.3 Menu

| Menu | Gunanya | Hasil di folder hasil |
|---|---|---|
| **Extract** | hujan tiap sel grid di kotak, di wilayah shapefile, atau di titik | `extract_output\box`, `extract_output\<nama shapefile>`, `extract_output\points` |
| **Visualisasi** | peta hujan jam-jaman, harian, bulanan, tahunan (kelas BMKG) | `visualization_output\<jenis peta>` |
| **Thiessen** | hujan wilayah tiap poligon shapefile (bobot luas Thiessen) | `thiessen_output\<nama shapefile>` |

### 6.4 Wilayah

Thiessen selalu memakai shapefile. Extract dan Visualisasi memilih salah satu
dari tiga cara berikut.

**Kotak.** Isi bujur min/maks dan lintang min/maks dalam derajat desimal
(bujur timur positif, lintang selatan negatif), misalnya bujur 110.2 sampai
110.6 dan lintang -8.1 sampai -7.6. Program menambah 0.2° di tiap sisi.

**Shapefile.** Klik **+ Tambah shapefile** dan pilih berkas `.shp`.

- Berkas `.shx`, `.dbf`, dan `.prj` dengan nama yang sama harus ada di
  sebelahnya. `.prj` berisi sistem koordinat; tanpa itu shapefile ditolak.
- Kartu shapefile menampilkan sistem koordinat, jumlah poligon, dan jumlah
  wilayah.
- Pilih **Kolom pengenal wilayah**: kolom yang menamai tiap wilayah. Poligon
  dengan nilai sama digabung menjadi satu wilayah. Tiap kolom ditampilkan
  dengan jumlah nilai uniknya dan contohnya.
- Boleh lebih dari satu shapefile (misalnya DAS dan kabupaten). Masing-masing
  mendapat folder hasil sendiri, dinamai dari nama berkasnya.
- **Hapus** melepas shapefile dari daftar; berkasnya tidak terhapus.

**Titik.** Pilih berkas `.csv` dengan kolom `name,lat,lon`, misalnya
`config\points.csv` yang disertakan:

```
name,lat,lon
Jakarta,-6.175,106.827
Bandung,-6.917,107.619
```

Tiap titik mengambil sel grid yang memuatnya.

### 6.5 Periode

Tanggal awal dan akhir adalah **hari hujan** setempat: satu hari hujan
berjalan dari jam awal hari (bawaan 07.00) sampai jam yang sama esok harinya,
dan diberi tanggal **hari berakhirnya**. Contoh: hujan tanggal Kamis = Rabu
07.00 sampai Kamis 07.00. Kedua tanggal ikut penuh. Keterangan di bawah kolom
tanggal menyebut jam dan zona waktu yang berlaku.

### 6.6 Folder hasil

Pilih folder tempat hasil ditulis; subfolder menurut menu (tabel 6.3) dibuat
sendiri. Bawaannya `data\output` di folder program. Menjalankan ulang dengan
wilayah yang sama **menimpa** berkas di subfolder itu.

### 6.7 Lanjutan (boleh dilewati)

Klik **Lanjutan** untuk membuka:

- **Zona waktu**: WIB, WITA, WIT, atau UTC.
- **Jam awal hari hujan** (0–23, bawaan 7).
- **Tabel hujan yang ditulis** (Extract, Thiessen): jam-jaman, harian,
  bulanan, tahunan, maks. harian. Berkas jam-jaman paling besar; matikan bila
  tidak perlu.
- **Jenis peta** (Visualisasi): jam-jaman, harian, bulanan, tahunan. Peta
  jam-jaman membuat satu gambar per jam, jadi pakai untuk periode pendek.
- **Urutan kolom wilayah** (Thiessen): *sesuai shapefile (tidak diurutkan)*
  sebagai bawaan, *terkecil ke terbesar*, atau *terbesar ke terkecil*
  (bagian 7.3).

### 6.8 Ringkasan dan Jalankan

Ringkasan dihitung ulang setiap isian berubah: wilayah yang dibaca (dengan
margin), periode dalam waktu setempat dan UTC, ukuran (sel × jam), dan folder
hasil. Periksa, lalu klik **Jalankan**.

Bila ukurannya sangat besar (lebih dari 200 juta nilai), halaman
memperingatkan: perkecil wilayah atau periode.

### 6.9 Proses dan hasil

Selama berjalan isian dikunci dan log tampil di halaman (juga di jendela
hitam). Di akhir muncul `✓ Selesai dalam … detik` atau `✗ Gagal …` dengan
sebabnya, lalu daftar folder hasil beserta jumlah berkas baru. **Buka
folder** membukanya di Explorer. Hanya satu proses pada satu waktu.

### 6.10 Selesai

Klik **Tutup program**, atau tutup jendela hitam. Pilihan terakhir tersimpan
di `config\input.local.txt`, jadi `run.bat` berikutnya membuka halaman dengan
isian yang sama.

## 7. Hasil

### 7.1 Lima tabel hujan (Extract dan Thiessen)

Tiap kolom tabel adalah satu sel grid, titik, atau wilayah.

| Berkas | Isi |
|---|---|
| `rain_hourly.csv` | mm per jam, label akhir jam waktu setempat; jam yang hilang kosong |
| `rain_daily.csv` | jumlah hujan hari tetap (mm); kosong bila ada jam yang hilang di hari itu |
| `rain_monthly.csv` | jumlah hari dalam tiap bulan; kosong kecuali semua hari ada dan bulan itu utuh di dalam periode |
| `rain_yearly.csv` | jumlah hari dalam tiap tahun (mulai bulan awal tahun), dengan aturan yang sama |
| `rain_max_daily.csv` | hujan harian terbesar tiap tahun, bila sedikitnya 90 % harinya ada |
| `rain_max_daily_date.csv` | tanggal hujan maksimum itu |
| `rain_max_daily_valid.csv` | bagian hari dalam tahun itu yang datanya ada |

Tidak ada interpolasi. Tiap kolom grid adalah satu sel 0,1° (sekitar
11 × 11 km), dinamai dengan titik pusatnya `<lintang>_<bujur>`, misalnya
`-7.85_110.45`, sama di setiap run.

### 7.2 Extract

Folder `<folder hasil>\extract_output\<box | points | nama shapefile>\`
berisi lima tabel hujan, ditambah:

| Berkas | Isi |
|---|---|
| `cells.csv` | pusat tiap sel; untuk titik juga titiknya dan titik lain di sel yang sama; untuk shapefile juga wilayah yang disentuhnya |
| `map.png` | sel yang ditulis, di atas hujan rata-rata periode |
| `choices.txt` | pilihan yang dipakai dan ringkasannya, untuk dicatat di laporan |

- **Kotak**: semua sel di kotak + margin.
- **Shapefile**: semua sel yang beririsan dengan poligon tiap shapefile.
- **Titik**: sel yang memuat tiap titik, satu kolom per titik dengan nama dari
  berkas titik.

### 7.3 Thiessen

Folder `<folder hasil>\thiessen_output\<nama shapefile>\` berisi lima tabel
hujan dengan satu kolom per wilayah (nilai kolom pengenal), ditambah
`weights.csv` (wilayah, sel, luas geodesik, bobot), `map.png`, dan
`choices.txt`.

**Urutan kolom wilayah** dipilih di *Lanjutan* (kunci
`thiessen_column_order`) dan berlaku juga untuk baris `weights.csv`:

| Pilihan | Urutan | Contoh pengenal `SubDAS_10, SubDAS_2, SubDAS_1` |
|---|---|---|
| sesuai shapefile (bawaan) | urutan tabel atribut shapefile, tidak diurutkan | SubDAS_10, SubDAS_2, SubDAS_1 |
| terkecil ke terbesar | naik | SubDAS_1, SubDAS_2, SubDAS_10 |
| terbesar ke terkecil | turun | SubDAS_10, SubDAS_2, SubDAS_1 |

Pengenal berupa angka diurutkan sebagai angka. Pengenal berupa teks juga
membaca angka di dalamnya sebagai angka, sehingga `SubDAS_2` berada sebelum
`SubDAS_10`.

Cara hitungnya: poligon Thiessen dibentuk dari titik grid di sekitar
shapefile (batas + margin), dipotong menurut tiap wilayah, dan diberi bobot
luas geodesik. Tiap poligon mengambil hujan titik grid di dalamnya. Hujan
wilayah kosong bila salah satu sel yang berbobot di wilayah itu tidak ada
datanya. Wilayah yang berada di sel yang sama mendapat hujan yang sama, dan
program memberitahukannya.

### 7.4 Peta (Visualisasi)

Peta menggambar wilayah terpilih (+ margin) beserta poligon shapefile, di
`<folder hasil>\visualization_output\<jenis>\`:

| Peta | Contoh berkas | Judul |
|---|---|---|
| jam-jaman | `hourly\rain_hourly_20260114_0200.png` | 14 Jan 2026, 02.00 WIB (akhir jam) |
| harian | `daily\rain_daily_20260114.png` | Rabu, 14 Jan 2026 (13 Jan 07.00 - 14 Jan 07.00 WIB) |
| bulanan | `monthly\rain_monthly_202601.png` | Januari 2026; hanya bulan utuh tanpa hari hilang |
| tahunan | `yearly\rain_yearly_2026.png` | 2026; hanya tahun utuh tanpa hari hilang |

- Bulan atau tahun yang tidak utuh di dalam periode dilewati, dengan
  catatan di log.
- Peta jam-jaman: satu peta per jam (sekitar 0,6 detik per peta), jadi
  periode panjang menghasilkan ribuan berkas.
- **Kelas warna**: jam-jaman dan harian menurut kategori intensitas hujan
  BMKG (ditambah kelas sangat ringan 0,1–1 mm/jam dan 0,5–5 mm/hari);
  bulanan menurut 9 kelas BMKG dengan kelompok rendah, menengah, tinggi,
  sangat tinggi. Sumber tiap kelas ada di komentar `config\input.txt`.
- Sel di bawah batas kelas pertama transparan, sehingga daratan atau relief
  terlihat. Sel dengan data tidak lengkap diarsir.
- Lapisan peta: relief (opsional), darat dan laut, hujan, garis pantai, batas
  negara dan provinsi, kota terbesar (Natural Earth 10m), dan wilayah
  shapefile dengan labelnya.

## 8. Konvensi waktu

- Waktu di berkas GSMaP adalah **UTC** dan menandai **awal** jam.
- Waktu di hasil menandai **akhir** jam (hujan yang sudah turun): zona waktu
  + 1 jam, yaitu UTC + 8 jam untuk WIB, UTC + 9 jam untuk WITA, UTC + 10 jam
  untuk WIT, dan UTC + 1 jam untuk UTC.
- Hujan harian dijumlah dari jam awal hari sampai jam yang sama esok harinya
  (bawaan 07.00–07.00, jam baca pos hujan manual) dan diberi tanggal hari
  berakhirnya.

## 9. Pengaturan lewat berkas config

Biasanya Anda tidak perlu menyunting berkas apa pun: halaman menulis pilihan
Anda ke `config\input.local.txt`.

- `config\input.txt` memuat nilai bawaan semua pilihan. Tiap kunci dijelaskan
  oleh komentarnya dan diperiksa sebelum data dibaca; kunci yang hilang atau
  salah menghentikan program dengan menyebut namanya.
- `config\input.local.txt` (khusus komputer ini) menimpa kunci yang sama di
  `input.txt`. Program mencetak kunci mana yang berasal dari berkas ini.

Kunci yang **tidak ada di halaman** dan hanya bisa diubah di berkas config:

| Kunci | Arti | Bawaan |
|---|---|---|
| `region_margin_deg` | margin di tiap sisi wilayah, derajat (0–5) | 0.2 |
| `year_start_month` | bulan awal tahun untuk tabel tahunan dan maksimum (1 = tahun kalender, 11 = tahun air Nov–Okt) | 1 |
| `min_valid_fraction` | bagian hari yang harus ada agar maksimum tahunan dihitung (0 < f ≤ 1) | 0.9 |
| `daily_date_label` | tanggal hujan harian: `end` = hari jendela berakhir, `start` = hari jendela dimulai | end |
| `map_levels_*`, `map_names_*` | batas dan nama kelas warna peta | kelas BMKG |
| `map_label_max` | label wilayah dan nomor sel hanya bila jumlahnya ≤ nilai ini (0 = tanpa label) | 100 |
| `map_cities` | jumlah kota terbesar yang diberi nama (0 = tanpa kota) | 8 |
| `basemap_relief_file` | relief bayangan di bawah peta (lihat di bawah) | kosong |

**Relief bayangan.** Isi `basemap_relief_file` di `config\input.local.txt`
dengan sebuah folder, misalnya `data/basemap`. Bila `SR_HR.tif` belum ada di
sana, program mengunduh relief Natural Earth 10m sekali (`SR_HR.zip`, 42 MB;
233 MB setelah diekstrak) lalu memakainya seterusnya. Bila diisi path berkas
`.tif`, berkas itu dipakai apa adanya (grayscale, EPSG:4326). Relief bersifat
opsional: bila tidak ada, gagal diunduh, atau tidak terbaca, program mencatat
di layar dan membuat peta tanpa relief.

## 10. Menjalankan tanpa peramban

Untuk run tanpa halaman, dari folder program:

```
run.bat --mode extract --no-menu
```

`run.bat` meneruskan argumen ke program dan menyiapkan pustaka peta
(GDAL) lebih dulu; jendela menunggu satu tombol di akhir.

- Mode: `extract`, `visualize`, `thiessen`. Berkas config dibaca apa adanya.
- Tanpa `--no-menu`, program mencetak ringkasan lalu bertanya
  `Lanjut? [Y/n]`.
- `--text-menu` menampilkan menu di jendela hitam, bukan di halaman.
- Berkas config lain: `--config pekerjaan_saya/input.txt`.

## 11. Bila ada masalah

| Gejala | Yang dilakukan |
|---|---|
| Halaman tidak terbuka | salin alamat `http://127.0.0.1:…/` dari jendela hitam ke peramban |
| Jendela hitam langsung tertutup / galat pustaka | jalankan `install.bat` lagi (juga setelah folder program dipindah) |
| `conda not found` saat pemasangan | pasang Miniforge, atau jalankan `install.bat` dari *Miniforge Prompt* |
| Tombol Jalankan tidak aktif | masih ada pesan merah di salah satu bagian |
| Shapefile ditolak | `.prj` tidak ada, atau berkas `.shx`/`.dbf` tidak di sebelahnya |
| Dua berkas untuk bulan yang sama | folder data berisi lebih dari satu produk atau berkas ganda; pisahkan |
| Halaman tidak merespons setelah jendela hitam ditutup | program sudah berhenti; klik dua kali `run.bat` lagi |
| Peta tanpa garis pantai atau batas | lapisan Natural Earth belum terunduh; sambungkan internet lalu jalankan `install.bat` lagi |

## 12. Sitasi dan lisensi

Bila Anda memakai program ini dalam karya tulis, kutip:

> Januriyadi, N. F. GSMaP Explorer [Perangkat lunak]. Program Studi Teknik
> Sipil, Universitas Pertamina. <https://doi.org/10.5281/zenodo.21310278>

Lisensi MIT (lihat berkas `LICENSE`). Kode sumber:
<https://github.com/heslab-uper/gsmap-explorer>
