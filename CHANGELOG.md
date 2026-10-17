# Changelog

## Unreleased

gsmap-explorer is reduced to three modes (owner 2026-10-17): **extract**,
**visualize** and **thiessen**, with five rain outputs (hourly, daily,
monthly, yearly, annual maximum daily). The config `config/input.txt` is
reorganised: a config of an earlier version has to be rewritten; its old keys
are not read, and each missing new key stops the program with its name.

### Removed

- Modes `analysis` (return periods, distribution tests, IDF/Mononobe, diurnal
  cycle, rain events), `series` (its points, box and shape regions are now in
  `extract`) and `all`. Their code stays in the git history and in `v1.0.0`.
- The question-and-answer menu of the series mode and its `series_last.txt`.
- `csv_output/hujan_grid.csv`, `koordinat.csv`, `hujan_area_*.csv`,
  `hujan_max_daily_yearly.csv`: replaced by the five rain outputs below.
- Keys `shapefile`, `shapefile_id_field` (now `shape_<name>`), `series_*`, every
  key of the analysis, `gsmap_product`, `path_temp`, `var_name`, `time_dim`,
  `lat_dim`, `lon_dim`.
- Packages `xarray`, `fiona`, `scipy`, `tqdm` (not used).

### Renamed keys

| Before | Now |
|---|---|
| `path_nc`, `gsmap_data_folder` | `gsmap_folder` (one product, in `config/input.local.txt`) |
| `path_out` | `output_folder` |
| `path_points` | `points_file` |
| `path_shp` + `das_field` | `shape_<name> = <path> \| <id field>`, one per shapefile, in `config/input.local.txt` |
| `wilayah_waktu` | `time_zone` |

### New

- **Extract** (`extract_region`): `box` (every cell + margin), `shape` (every cell
  sharing an area with the polygons of each `shape_<name>`, one folder each) or
  `points` (the cell of each point of `points_file`). Columns are named by the
  cell centre `<lat>_<lon>`, the same in every run.
- **Five rain outputs** for extract and thiessen (`rain_outputs`):
  `rain_hourly`, `rain_daily`, `rain_monthly`, `rain_yearly` and
  `rain_max_daily` with `_date` and `_valid`. Years start at `year_start_month`;
  an annual maximum needs `min_valid_fraction` of the days.
- **Thiessen** for every `shape_<name>`, with `weights.csv`. An areal value is
  empty when a cell with a weight in that region is missing (before, a
  missing cell counted as 0 mm).
- **Maps** (`visualize`): hourly, daily, monthly and yearly maps (`map_outputs`)
  of the extract region with BMKG classes and names, transparent dry cells,
  hatched incomplete cells, Natural Earth basemap, optional shaded relief
  (downloaded once into the folder of `basemap_relief_file`, never a stop when
  missing), the shapefile regions, files named by time. Extract and thiessen
  draw `map.png` of the cells used.
- `install.bat` creates the Python environment in `env\` from
  `environment.yml`; `run.bat` uses it and sets `GDAL_DATA`. `rasterio` and
  `libgdal-core` are pinned (1.5.0, 3.12): the newest builds fail to import on
  Windows (2026-10-17).
- **A page in the browser** (owner 2026-10-17): `run.bat` without arguments
  opens it from a small server on `127.0.0.1` (this computer only, random port,
  a key per start). Folders and files are chosen with *Telusuri* (browse), the
  data folder is checked (months found, duplicate months), a shapefile shows
  its CRS, polygons and columns for the id field, and the summary (region,
  period, cells x hours, output) is asked from the program as the fields
  change. *Jalankan* (run) saves the choices to `config/input.local.txt`
  (other lines kept), shows the log and lists the result folders with *Buka
  folder* (open). One run at a time; `--text-menu` keeps the console menu.
- With `--mode`, the summary and `Lanjut? [Y/n]` come before the data are
  read; `--no-menu` skips the question.
- `config/input.local.txt` (not in git) for the values of one computer; it
  replaces keys of `config/input.txt`. `output_folder` inside the program
  folder must be under `data/`.
- `region_margin_deg` (0.2) on every side of the region read.

### Changed behaviour

- `start_date` .. `end_date` are local rain days (`day_start_hour` in
  `time_zone`), dated by `daily_date_label = end` (owner 2026-10-17): Thursday =
  Wednesday 07.00 to Thursday 07.00.
- `time_zone = UTC` labels the end of the hour (UTC + 1 h), like the other
  zones; an unknown time zone is an error.
- A shapefile without a CRS is an error; any CRS is converted to EPSG:4326.
- Relative paths are taken from the folder of `run.py`.
- The grid is read from the `.nc` files (rounded to 2 decimals), no longer from
  a grid fixed in the code: files with another extent or with `lat` running
  south to north are read at the right cells.

### Fixed

- **Thiessen: areal rain taken from the wrong grid points.** The Thiessen
  polygons were named by position, but `shapely.voronoi_polygons` does not
  return them in the order of the points, so most polygons carried the rain
  of another grid point (14 of 16 in a 4 x 4 test; for a watershed near
  Yogyakarta, 23.99 instead of 27.46 mm on 1 Jan 2026). Each polygon now
  takes the point lying in it. Thiessen results of `v1.0.0` should be
  recomputed.
- Output redirected to a file or pipe (`run.py ... > log.txt`, scheduled
  runs) no longer stops with `UnicodeEncodeError` at the first "✅" message
  on Windows; `run.py` writes its output as UTF-8.
