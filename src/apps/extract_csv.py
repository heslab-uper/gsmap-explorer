
import numpy as np
import pandas as pd
from pathlib import Path

from core.local_time import local_offset_hours


def export_csv(data_subset, times, XX_subset, YY_subset, path_output, config=None):
    # UTC start-of-hour -> local end-of-hour (core.local_time)
    time_offset = local_offset_hours(config.get("wilayah_waktu"))

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
