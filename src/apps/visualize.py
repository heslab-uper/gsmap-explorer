"""Rain maps: hourly, daily, monthly, yearly (``map_outputs``) and the map of the extracted grid points.

Layers, bottom to top: shaded relief (``basemap_relief_file``, optional) or
plain land, sea, rain (below the first class bound: transparent, so the
relief shows), incomplete cells (hatched), coastline, country and province
borders (Natural Earth 10m), shapefile regions, largest places. Class bounds
and their category names come from the config (``map_levels_*``,
``map_names_*``). The frame is built once and only the rain layer and the
titles change between maps.
"""

from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe   # noqa: E402
import matplotlib.pyplot as plt       # noqa: E402
import numpy as np                    # noqa: E402
import pandas as pd                   # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap   # noqa: E402

from apps.extract_series import product_label   # noqa: E402
from core.shapefile import read_shapefile       # noqa: E402

PC = ccrs.PlateCarree()
MONTHS = ("Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
          "November", "Desember")
WEEKDAYS = ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu")
UNITS = {"hourly": "mm/jam", "daily": "mm/hari", "monthly": "mm/bulan", "yearly": "mm/tahun"}
TITLES = {"hourly": "Hujan per jam", "daily": "Hujan harian", "monthly": "Hujan bulanan", "yearly": "Hujan tahunan"}

# Look of the map (not user choices): a light neutral base so the blue rain classes stand out.
SEA = "#f7f7f5"
LAND = "#ebe8e1"
INK = "#3a3a3a"
HATCH = "#8f8f8f"
HALO = [pe.withStroke(linewidth=2.2, foreground="white")]


def _date_id(t) -> str:
    return f"{t.day} {MONTHS[t.month - 1][:3]} {t.year}"


def ramp(n: int) -> ListedColormap:
    """``n`` blues, light to dark, starting at a step visible on the light base (never near-white)."""
    colors = plt.get_cmap("Blues")(np.linspace(0.32, 1.0, n))
    colors[:, 3] = 0.92   # a little of the relief shows through; set here, not on the layer (it would
    cmap = ListedColormap(colors)   # also fill the transparent dry cells)
    cmap.set_under((0, 0, 0, 0))   # below the first bound: dry, transparent
    cmap.set_bad((0, 0, 0, 0))     # missing: drawn by the hatch layer
    return cmap


def _natural_earth(category: str, name: str):
    """Path of a Natural Earth 10m layer (downloaded by cartopy once), or None with a note."""
    try:
        return shpreader.natural_earth(resolution="10m", category=category, name=name)
    except Exception as exc:   # noqa: BLE001 - offline or server down: the map is drawn without it
        print(f"  note: Natural Earth layer {name} not available ({type(exc).__name__}); drawn without it")
        return None


def _geoms(path) -> list:
    """Geometries of a shapefile; records without one (some Natural Earth layers have them) are skipped."""
    return [g for g in shpreader.Reader(path).geometries() if g is not None and not g.is_empty]


def _edges(centres: np.ndarray) -> np.ndarray:
    """Cell edges from regular cell centres (either direction)."""
    step = (centres[-1] - centres[0]) / (len(centres) - 1) if len(centres) > 1 else 0.1
    return np.concatenate([centres - step / 2, [centres[-1] + step / 2]])


def read_relief(path, extent):
    """Window of a grayscale relief raster over ``extent``: (array, [left, right, bottom, top])."""
    import rasterio
    from rasterio.windows import from_bounds

    with rasterio.open(path) as src:
        geographic = src.crs is not None and src.crs.to_epsg() == 4326
        whole_earth = all(abs(a - b) < 1e-6 for a, b in zip(src.bounds, (-180, -90, 180, 90)))
        if not geographic and not (src.crs is None and whole_earth):
            raise ValueError(f"basemap_relief_file {path}: CRS {src.crs} with bounds {tuple(src.bounds)}; "
                             f"expected EPSG:4326 (or no CRS on a raster covering -180..180, -90..90)")
        min_lon, max_lon, min_lat, max_lat = extent
        window = from_bounds(min_lon, min_lat, max_lon, max_lat, src.transform).round_offsets().round_lengths()
        arr = src.read(1, window=window, boundless=True, fill_value=0)
        left, bottom, right, top = src.window_bounds(window)
    return arr, [left, right, bottom, top]


class MapCanvas:
    """One map frame over ``extent`` with its basemap; ``draw`` puts a rain field in it and saves it."""

    def __init__(self, extent, lon, lat, maps, settings, *, kind: str, regions=None, id_field=None,
                 class_names: bool = True):
        self.kind, self.lon, self.lat = kind, lon, lat
        min_lon, max_lon, min_lat, max_lat = extent
        width = 8.0
        height = max(3.0, width * (max_lat - min_lat) / (max_lon - min_lon))
        self.fig = plt.figure(figsize=(width + 2.4, height + 1.4))
        ax = self.ax = self.fig.add_axes([0.06, 0.1, 0.74, 0.8], projection=PC)
        ax.set_extent(extent, crs=PC)
        ax.set_facecolor(SEA)

        relief = None
        if maps.relief_file is not None:
            try:
                relief = read_relief(maps.relief_file, extent)
            except (ImportError, OSError, ValueError) as exc:   # no rasterio, unreadable file: optional layer
                print(f"  note: relief {maps.relief_file} not drawn ({type(exc).__name__}: {exc}); map without relief")
        if relief is not None:
            arr, ext = relief
            ax.imshow(arr, extent=ext, origin="upper", cmap="gray", vmin=0, vmax=255, alpha=0.55,
                      transform=PC, zorder=0, interpolation="bilinear")
            ocean = _natural_earth("physical", "ocean")
            if ocean:
                ax.add_feature(cfeature.ShapelyFeature(_geoms(ocean), PC),
                               facecolor=SEA, edgecolor="none", zorder=1)
        else:
            land = _natural_earth("physical", "land")
            if land:
                ax.add_feature(cfeature.ShapelyFeature(_geoms(land), PC),
                               facecolor=LAND, edgecolor="none", zorder=0)

        # rain and its classes
        levels, names = maps.levels[kind], (maps.names[kind] if class_names else [])
        self.cmap, self.norm = ramp(len(levels)), BoundaryNorm(levels, len(levels), extend="max")
        self.mesh = ax.pcolormesh(lon, lat, np.full((len(lat), len(lon)), np.nan), cmap=self.cmap,
                                  norm=self.norm, shading="nearest", transform=PC, zorder=2)
        self.lon_edges, self.lat_edges = _edges(lon), _edges(lat)
        self.hatch = None

        for name, style in (("coastline", dict(linewidth=0.6, edgecolor=INK)),
                            ("admin_0_boundary_lines_land", dict(linewidth=0.6, edgecolor=INK, linestyle="--")),
                            ("admin_1_states_provinces_lines", dict(linewidth=0.4, edgecolor="#7d7d7d"))):
            path = _natural_earth("physical" if name == "coastline" else "cultural", name)
            if path:
                ax.add_feature(cfeature.ShapelyFeature(_geoms(path), PC),
                               facecolor="none", zorder=4, **style)

        if regions is not None:
            ax.add_geometries(regions.geometry, crs=PC, facecolor="none", edgecolor="#1b1b1b",
                              linewidth=1.0, zorder=5)
            groups = regions.dissolve(by=id_field)
            if 0 < len(groups) <= maps.label_max:
                # regions closer than 4 % of the map width share one label (and a marker, so a region
                # smaller than a pixel still shows where it is)
                gap = 0.04 * (max_lon - min_lon)
                labels = []
                for rid, geom in zip(groups.index, groups.geometry):
                    p = geom.representative_point()
                    near = next((lb for lb in labels if np.hypot(p.x - lb[1], p.y - lb[2]) < gap), None)
                    if near:
                        near[0].append(str(rid))
                    else:
                        labels.append(([str(rid)], p.x, p.y))
                for ids, x, y in labels:
                    ax.plot(x, y, marker="s", markersize=3.5, markerfacecolor="none", markeredgecolor="#1b1b1b",
                            transform=PC, zorder=6)
                    ax.text(x, y, " " + ", ".join(ids), fontsize=7.5, ha="left", va="center", color="#1b1b1b",
                            transform=PC, zorder=6, path_effects=HALO)

        if maps.cities > 0:
            self._places(extent, maps.cities)

        gl = ax.gridlines(crs=PC, draw_labels=True, linewidth=0.3, color="#9a9a9a", alpha=0.6, linestyle="--")
        gl.top_labels = gl.right_labels = False
        gl.xlabel_style = gl.ylabel_style = {"size": 8, "color": "#555555"}

        cax = self.fig.add_axes([0.83, 0.16, 0.022, 0.62])
        cbar = self.fig.colorbar(self.mesh, cax=cax, extend="max", ticks=levels, spacing="uniform")
        cbar.ax.tick_params(labelsize=8)
        cbar.ax.set_yticklabels([f"{v:g}" for v in levels])
        cbar.ax.set_title(UNITS[kind], fontsize=8, loc="left", pad=8)
        self._class_names(cbar, names)
        self.missing_key = self.fig.text(0.83, 0.1, "", fontsize=7.5, color="#555555")

        self.title = ax.text(0, 1.075, "", transform=ax.transAxes, fontsize=13, weight="bold", color="#1f1f1f")
        self.subtitle = ax.text(0, 1.025, "", transform=ax.transAxes, fontsize=9.5, color="#444444")
        product = product_label(settings.gsmap_folder)
        ax.text(0, -0.09, f"GSMaP {product} (JAXA), diolah gsmap-explorer. Basemap: Natural Earth.",
                transform=ax.transAxes, fontsize=7, color="#777777", va="top")

    def _places(self, extent, n):
        path = _natural_earth("cultural", "populated_places")
        if not path:
            return
        min_lon, max_lon, min_lat, max_lat = extent
        found = []
        for rec in shpreader.Reader(path).records():
            x, y = rec.geometry.x, rec.geometry.y
            if min_lon <= x <= max_lon and min_lat <= y <= max_lat:
                found.append((rec.attributes.get("POP_MAX") or 0, rec.attributes.get("NAME", ""), x, y))
        # largest first; a place closer than 4 % of the map width to a larger one is left out
        gap = 0.04 * (max_lon - min_lon)
        kept = []
        for pop, name, x, y in sorted(found, reverse=True):
            if len(kept) < n and all(np.hypot(x - kx, y - ky) >= gap for _, _, kx, ky in kept):
                kept.append((pop, name, x, y))
        for _, name, x, y in kept:
            self.ax.plot(x, y, marker="o", markersize=2.8, color="#1f1f1f", transform=PC, zorder=6)
            self.ax.text(x, y, f" {name}", fontsize=7.5, color="#1f1f1f", va="bottom", transform=PC, zorder=6,
                         path_effects=HALO)

    def _class_names(self, cbar, names):
        """Category names beside the colour bar; neighbouring classes with one name share a label."""
        if not names:
            return
        n = len(names)
        spans, start = [], 0
        for i in range(1, n + 1):
            if i == n or names[i] != names[start]:
                spans.append((start, i - 1, names[start]))
                start = i
        for first, last, name in spans:
            # classes 0 .. n-2 fill the bar, the last (open) class is the arrow above it
            pos = [(k + 0.5) / (n - 1) if k < n - 1 else 1.04 for k in (first, last)]
            cbar.ax.text(3.6, sum(pos) / 2, name, transform=cbar.ax.transAxes, ha="left", va="center",
                         fontsize=7.5, color="#444444")

    def draw(self, field: np.ndarray, title: str, subtitle: str, out: Path) -> None:
        missing = np.isnan(field)
        self.mesh.set_array(np.ma.masked_invalid(field).ravel())
        if self.hatch is not None:
            self.hatch.remove()
            self.hatch = None
        if missing.any():
            self.hatch = self.ax.pcolor(self.lon_edges, self.lat_edges,
                                        np.ma.masked_where(~missing, np.ones_like(field)), hatch="////",
                                        facecolor="none", edgecolor=HATCH, linewidth=0, transform=PC, zorder=3)
            self.missing_key.set_text("//// data tidak lengkap")
        else:
            self.missing_key.set_text("")
        self.title.set_text(title)
        self.subtitle.set_text(subtitle + ("  (data tidak ada)" if missing.all() else ""))
        out.parent.mkdir(parents=True, exist_ok=True)
        self.fig.savefig(out, dpi=150, bbox_inches="tight", pad_inches=0.15)

    def close(self):
        plt.close(self.fig)


def map_extent(grid, margin_extent):
    """The cells read (region + margin, whole cells): the map shows exactly the data, no empty strip."""
    le, ae = _edges(grid.lon), _edges(grid.lat)
    return [le.min(), le.max(), ae.min(), ae.max()]


def _regions(settings):
    if settings.shapefile is None:
        return None
    return read_shapefile(settings.shapefile, settings.shapefile_id_field)


def plot_maps(grid, settings, maps, extent) -> None:
    """The maps of ``map_outputs`` in ``<output_folder>/visualization_output/<kind>/``."""
    out_dir = settings.output_folder / "visualization_output"
    regions, tz = _regions(settings), settings.time_zone
    h = settings.day_start_hour
    for kind in maps.outputs:
        table = {"hourly": grid.hourly, "daily": grid.daily, "monthly": grid.monthly, "yearly": grid.yearly}[kind]
        if kind in ("monthly", "yearly"):
            skipped = [str(i) for i, row in table.iterrows() if row.isna().all()]
            if skipped:
                print(f"  {kind}: {', '.join(skipped)} not whole in the period or with a missing day: no map")
            table = table.dropna(how="all")
        if table.empty:
            if kind in ("hourly", "daily"):
                print(f"  {kind}: no map (no data in the period)")
            continue
        canvas = MapCanvas(map_extent(grid, extent), grid.lon, grid.lat, maps, settings, kind=kind,
                           regions=regions, id_field=settings.shapefile_id_field)
        for k, (idx, row) in enumerate(table.iterrows(), 1):
            if kind == "hourly":
                sub, name = f"{_date_id(idx)}, {idx:%H.%M} {tz}", f"rain_hourly_{idx:%Y%m%d_%H%M}.png"
            elif kind == "daily":
                d = idx
                start = d if settings.daily_date_label == "start" else d - pd.Timedelta(days=1)
                end = start + pd.Timedelta(days=1)
                sub = (f"{WEEKDAYS[d.weekday()]}, {_date_id(d)}  "
                       f"({_date_id(start)} {h:02d}.00 - {_date_id(end)} {h:02d}.00 {tz})")
                name = f"rain_daily_{d:%Y%m%d}.png"
            elif kind == "monthly":
                y, m = idx.split("-")
                sub, name = f"{MONTHS[int(m) - 1]} {y}", f"rain_monthly_{y}{m}.png"
            else:
                sub, name = f"{idx}", f"rain_yearly_{idx}.png"
            canvas.draw(grid.field(row), TITLES[kind], sub, out_dir / kind / name)
            if kind == "hourly" and k % 100 == 0:
                print(f"  hourly maps: {k} / {len(table)}")
        canvas.close()
        print(f"  {kind}: {len(table)} map(s) in {out_dir / kind}")
    print(f"✅ Visualisasi tersimpan di: {out_dir}")


def plot_grid_points(grid, settings, maps, extent, out: Path) -> None:
    """Map of the extracted grid points over the period mean; point numbers as in koordinat.csv."""
    field, kind, what = grid.period_mean()
    canvas = MapCanvas(map_extent(grid, extent), grid.lon, grid.lat, maps, settings, kind=kind,
                       regions=_regions(settings), id_field=settings.shapefile_id_field, class_names=False)
    lon2, lat2 = np.meshgrid(grid.lon, grid.lat)
    canvas.ax.scatter(lon2.ravel(), lat2.ravel(), s=3, color="#1f1f1f", transform=PC, zorder=7, linewidths=0)
    n = lon2.size
    if n <= maps.label_max:
        for i, (x, y) in enumerate(zip(lon2.ravel(), lat2.ravel()), 1):
            canvas.ax.text(x, y, f" {i}", fontsize=6.5, color="#1f1f1f", va="bottom", transform=PC, zorder=7,
                           path_effects=HALO)
        note = "nomor = point_<n> di koordinat.csv dan hujan_grid.csv"
    else:
        note = f"{n} titik > map_label_max = {maps.label_max}: nomor titik lihat koordinat.csv"
    canvas.draw(field, f"Titik grid hasil ekstraksi ({n} titik)", f"{what}; {note}", out)
    canvas.close()
    print(f"  grid point map: {out}")
