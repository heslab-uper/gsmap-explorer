# Changelog

## Unreleased

Config `config/input.txt` reorganised (owner 2026-10-17). A config of an
earlier version has to be rewritten: its old keys are not read, and each
missing new key stops the program with its name.

### Renamed or merged keys

| Before | Now |
|---|---|
| `path_nc`, `gsmap_data_folder` | `gsmap_folder` (one product, required, no example value) |
| `path_out` | `output_folder` |
| `path_points` | `points_file` |
| `path_shp` (`None` = no shapefile) | `shapefile` (empty = no shapefile) |
| `das_field` | `shapefile_id_field` |
| `wilayah_waktu` | `time_zone` |
| `series_selection` | `series_region` |
| `series_confirm_values` | `series_max_values` |
| `duration_minutes` | `intensity_durations_minutes` |

Removed: `gsmap_product` (one product per folder), `path_temp`, `var_name`,
`time_dim`, `lat_dim`, `lon_dim` (never read; the `.nc` names are fixed by
the file format).

### Changed behaviour

- `start_date` .. `end_date` are local rain days (`day_start_hour` in
  `time_zone`) in every mode; before, the modes other than `series` read
  UTC dates. For WIB with `day_start_hour = 7` the hours read are the same.
- `time_zone = UTC` labels the end of the hour (UTC + 1 h), like the other
  zones; before, any value other than WIB/WITA/WIT gave UTC start-of-hour
  labels silently. An unknown time zone is now an error.
- A shapefile without a CRS is an error; before, `thiessen` and the series
  mode took it as EPSG:4326.
- Relative paths are taken from the folder of `run.py`, from wherever it is
  started.
- The series menu no longer remembers its answers (`series_last.txt`); its
  defaults are always the config values.
- Every key is checked before any data is read; a polygon with an empty
  `shapefile_id_field` and a region outside the data are errors.
- The modes extract, visualize, thiessen, analysis and all read the grid
  from the `.nc` files (rounded to 2 decimals), no longer from a grid fixed
  in the code (90.05..150.05, 15.05..-15.05). Files with another extent or
  with `lat` running south to north are now read at the right cells; before,
  they failed or were shifted. Coordinates in `koordinat.csv` are the
  rounded centres (106.05, not 106.04999999999909). A region bound lying
  exactly on a cell centre now includes that cell, as documented; the fixed
  grid lost it to rounding.

- Maps rewritten (`visualize`): hourly, daily, monthly and yearly maps
  (`map_outputs`) with BMKG classes and names, transparent dry cells, hatched
  incomplete cells, Natural Earth basemap with optional shaded relief, the
  shapefile regions, and files named by time in one folder per kind. Every
  mode writing `csv_output/` also draws `grid_points_map.png`.
- `region_margin_deg` (0.2): the data read, the maps and the series `box` /
  `shape` cover the region + this margin on every side. Before: the box
  exactly, the shapefile bounds + 0.1 to 0.15 degree; the series no margin.
- `daily_date_label = end` in the config (owner 2026-10-17): a day is dated
  by the day its window ends (Thursday = Wednesday 07.00 to Thursday 07.00).
- Machine values in `config/input.local.txt` (not in git), which replaces
  keys of `config/input.txt`; `gsmap_folder` is empty in the repository.
- `output_folder` inside the program folder must be under `data/`.
- `basemap_relief_file` may be a folder (e.g. `data/basemap`): the Natural
  Earth 10m shaded relief is downloaded into it once. The relief is
  optional: missing, not downloadable or unreadable gives a note and maps
  without it, never a stop.
- A missing `gsmap_folder` or `basemap_relief_file` points to
  `config/input.local.txt`.

### Fixed

- **Thiessen: areal rain taken from the wrong grid points.** The Thiessen
  polygons were named by position, but `shapely.voronoi_polygons` does not
  return them in the order of the points, so most polygons carried the rain
  of another grid point (14 of 16 in a 4 x 4 test; for a watershed near
  Yogyakarta, 23.99 instead of 27.46 mm on 1 Jan 2026). Each polygon now
  takes the point lying in it. Results of `thiessen` and of `analysis` with
  a shapefile from earlier versions should be recomputed.
- Output redirected to a file or pipe (`run.py ... > log.txt`, scheduled
  runs) no longer stops with `UnicodeEncodeError` at the first "✅" message
  on Windows; `run.py` writes its output as UTF-8.
