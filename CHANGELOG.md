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
