"""Natural Earth 10m shaded relief for the maps: downloaded once into the folder of ``basemap_relief_file``."""

import urllib.request
import zipfile
from pathlib import Path

RELIEF_URL = "https://naturalearth.s3.us-west-2.amazonaws.com/10m_raster/SR_HR.zip"
"""Natural Earth 10m shaded relief, large size, in the S3 bucket of NACIS (registry.opendata.aws/naturalearth).
The link of naturalearthdata.com answered HTTP 500 (2026-10-17); this bucket holds the same 42.31 MB file."""

RELIEF_ZIP_BYTES = 44_367_365
"""Size of SR_HR.zip in the bucket (read 2026-10-17): a shorter download is an error."""

RELIEF_TIF = "SR_HR.tif"
RELIEF_MEMBERS = ("SR_HR.tif", "SR_HR.tfw", "SR_HR.prj", "SR_HR.VERSION.txt", "SR_HR.README.html")
"""Files of SR_HR.zip (21600 x 10800 uint8 GeoTIFF, EPSG:4326 from its .prj; checked 2026-10-17)."""


def relief_path(path: Path) -> tuple[Path, bool]:
    """``basemap_relief_file`` -> (the .tif to draw, whether it must be downloaded).

    A .tif is used as it is (it must exist). Anything else is a folder that
    holds, or will hold, SR_HR.tif.
    """
    if path.suffix.lower() in (".tif", ".tiff"):
        if not path.is_file():
            raise FileNotFoundError(f"{path} not found (give a folder instead to download the Natural Earth relief)")
        return path, False
    if path.exists() and not path.is_dir():
        raise ValueError(f"{path} is neither a .tif nor a folder")
    tif = path / RELIEF_TIF
    return tif, not tif.is_file()


def download_relief(tif: Path) -> Path:
    """Download SR_HR.zip into the folder of ``tif`` and unpack its files; returns ``tif``."""
    folder = tif.parent
    folder.mkdir(parents=True, exist_ok=True)
    part = folder / "SR_HR.zip.part"
    print(f"Basemap relief: {tif} not found; downloading Natural Earth shaded relief once")
    print(f"  {RELIEF_URL} ({RELIEF_ZIP_BYTES / 2**20:.1f} MiB) -> {folder}")
    req = urllib.request.Request(RELIEF_URL, headers={"User-Agent": "gsmap-explorer"})
    done, step = 0, 0
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(part, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if done * 10 // RELIEF_ZIP_BYTES > step:
                    step = done * 10 // RELIEF_ZIP_BYTES
                    print(f"  {min(step, 10) * 10:3d} %")
        if done != RELIEF_ZIP_BYTES:
            raise ValueError(f"relief download has {done} bytes, expected {RELIEF_ZIP_BYTES}")
        with zipfile.ZipFile(part) as z:
            names = z.namelist()
            unknown = [n for n in names if n not in RELIEF_MEMBERS]
            if unknown or RELIEF_TIF not in names:
                raise ValueError(f"{RELIEF_URL} holds unexpected files {unknown or names}; not unpacked")
            z.extractall(folder)
    finally:
        part.unlink(missing_ok=True)   # our own partial or used download: the next run starts clean
    print(f"  unpacked {len(names)} files in {folder}")
    return tif
