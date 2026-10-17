import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
from datetime import timedelta
from matplotlib.colors import BoundaryNorm

from core.local_time import local_offset_hours

def plot_map(data, times, XX, YY, settings, extent=None):

    # ========================
    # SUBSET EXTENT (optional)
    # ========================
    if extent is not None:
        min_lon, max_lon, min_lat, max_lat = extent

        lon_mask = (XX >= min_lon) & (XX <= max_lon)
        lat_mask = (YY >= min_lat) & (YY <= max_lat)

        data = data[:, lat_mask, :][:, :, lon_mask]
        XX = XX[lon_mask]
        YY = YY[lat_mask]

    # ========================
    # GRID
    # ========================
    XX_mesh, YY_mesh = np.meshgrid(XX, YY)
    projection = ccrs.PlateCarree()

    # ========================
    # TIMEZONE
    # ========================
    time_zone = settings.time_zone
    # UTC start-of-hour -> local end-of-hour (core.local_time)
    time_offset = local_offset_hours(time_zone)

    # ========================
    # OUTPUT
    # ========================
    output_dir = settings.output_folder / "visualization_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ========================
    # PREPROCESS DATA
    # ========================
    data = data.copy()

    # hanya buang nilai negatif (0 masih valid hujan)
    data[data <= 0] = np.nan

    # ========================
    # COLOR SCALE GLOBAL
    # ========================

    levels = [0.1, 1, 2, 5, 10, 20, 50, 100]

    cmap = plt.get_cmap("Blues", len(levels)-1)
    norm = BoundaryNorm(levels, cmap.N)


    # ========================
    # LOOP PLOTTING
    # ========================
    for i, time in enumerate(times):

        fig = plt.figure(figsize=(12, 7))
        ax = plt.axes(projection=projection)

        

        dx = np.mean(np.diff(XX))
        dy = np.mean(np.diff(YY))

        ax.set_extent(
            [
                XX.min() - dx/2,
                XX.max() + dx/2,
                YY.min() - dy/2,
                YY.max() + dy/2,
            ],
            crs=projection)





        # ========================
        # PLOT DATA
        # ========================

        im = ax.pcolormesh(
            XX_mesh,
            YY_mesh,
            data[i],
            cmap=cmap,
            norm=norm,
            transform=projection,
            shading="auto",
        )


        # ========================
        # COLORBAR
        # ========================
        cbar = plt.colorbar(im, ax=ax, shrink=0.7, pad=0.03)
        cbar.set_label("Hujan (mm/jam)", fontsize=10)

        # ========================
        # MAP FEATURES
        # ========================
        ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
        ax.add_feature(cfeature.BORDERS, linestyle=":")
        # ax.add_feature(cfeature.LAND, facecolor="lightyellow", alpha=0.5)
        # ax.add_feature(cfeature.OCEAN, facecolor="lightblue", alpha=0.3)

        # ========================
        # GRIDLINES
        # ========================
        gl = ax.gridlines(draw_labels=True, linestyle="--", alpha=0.5)
        gl.top_labels = False
        gl.right_labels = False

        # ========================
        # TIME
        # ========================
        adjusted_time = time + timedelta(hours=time_offset)
        strftime_time = adjusted_time.strftime("%Y-%m-%d %H:%M")



        # ========================
        # JIKA DATA KOSONG
        # ========================
        if np.all(np.isnan(data[i])):
            ax.text(
                0.5, 0.5, "No Data",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=14,
                color="red",
                weight="bold"
            )

        # ========================
        # TITLE (HARUS DI LUAR IF)
        # ========================

        fig.suptitle(
            f"Intensitas Hujan\n{strftime_time} ({time_zone})",
            fontsize=12,
            fontweight="bold",
            y=0.98
        )

        fig.subplots_adjust(top=0.85)




        # ========================
        # SAVE
        # ========================

        plt.savefig(
            output_dir / f"precip_{i:03d}.png",
            dpi=150
        )


        plt.close()

    print(f"✅ Visualisasi tersimpan di: {output_dir}")