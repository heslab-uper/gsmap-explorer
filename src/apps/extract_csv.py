
import numpy as np
import pandas as pd
from pathlib import Path


def export_csv(data_subset, times, XX_subset, YY_subset, path_output, config=None):
    wilayah_waktu = config.get("wilayah_waktu")
    # GSMaP time is UTC and marks the START of each hourly period.
    # Offset = time zone (WIB +7, WITA +8, WIT +9) + 1 h, so the label
    # marks the END of the period (rain that has already fallen).
    if wilayah_waktu == "WIB":
        time_offset = 8
    elif wilayah_waktu == "WITA":
        time_offset = 9
    elif wilayah_waktu == "WIT":
        time_offset = 10
    else:
        time_offset = 0

    times = [t + pd.Timedelta(hours=time_offset) for t in times]

    path_output = Path(path_output) / "csv_output"
    path_output.mkdir(parents=True, exist_ok=True)

    XX_subset, YY_subset = np.meshgrid(XX_subset, YY_subset)
    name_point = [f"point_{i+1}" for i in range(XX_subset.size)]

    # koordinat
    df_koordinat = pd.DataFrame({
        'lon': XX_subset.flatten(),
        'lat': YY_subset.flatten(),
        'name': name_point
    })
    df_koordinat.to_csv(path_output / "koordinat.csv", index=False)

    # data hujan
    df_hujan = pd.DataFrame(
        data_subset.reshape(data_subset.shape[0], -1),
        columns=name_point
    )

    df_hujan.insert(0, 'time', [t.strftime("%Y-%m-%d %H:00:00") for t in times])
    df_hujan.to_csv(path_output / "hujan_grid.csv", index=False)

    print("✅ CSV berhasil dibuat:", path_output)
