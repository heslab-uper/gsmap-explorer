"""The page of gsmap-explorer: a server on this computer only (127.0.0.1) and the page in the browser.

``run.bat`` (``run.py`` without ``--mode``) starts it. The page asks the server
through ``/api/...``; every call carries the token written into the page, so
another site open in the browser cannot drive the program. Closing the console
window, Ctrl+C or the page's "Tutup program" button stops the server.

API (POST, JSON in and out):

- ``/api/info``        program folder, config file, current values of the config
- ``/api/browse``      drives, or the folders (and .shp / .csv files) of a folder
- ``/api/check_data``  a GSMaP folder: product, first and last month, number of months
- ``/api/shape_info``  a shapefile: CRS, polygons, columns with examples, a name for its output folder
- ``/api/points_info`` a CSV of points: number and names
- ``/api/summary``     the run of the page's values, checked and sized by ``main.prepare_run``; nothing saved
- ``/api/save``        the page's values into config/input.local.txt
- ``/api/run``         save, check, then run in a thread (one at a time); its messages also stay in the console
- ``/api/job``         state of the run, its new messages, and at the end the folders it wrote
- ``/api/open_folder`` open a result folder (inside the output folder of the run) in Explorer
- ``/api/quit``        stop the server
"""

import json
import os
import secrets
import string
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import re

from apps.rain_tables import RAIN_OUTPUTS
from core.local_time import TIME_ZONE_HOURS
from core.reader import MONTH_FILE
from utils.config_reader import PROGRAM_DIR, local_config_path, read_config_with_local, resolve_path
from utils.settings import EXTRACT_REGIONS, MAP_OUTPUTS

PAGE = Path(__file__).resolve().parents[1] / "web" / "index.html"
FILE_KINDS = {"folder": (), "shp": (".shp",), "csv": (".csv",)}
MODES = ("extract", "visualize", "thiessen")   # main.MODES; not imported to keep the page light to start
VALUE_KEYS = ("gsmap_folder", "extract_region", "min_lon", "max_lon", "min_lat", "max_lat", "points_file",
              "start_date", "end_date", "output_folder", "time_zone", "day_start_hour")


def current_values(cfg: dict) -> dict:
    """The values the page shows, from config/input.txt + config/input.local.txt (paths made absolute)."""
    values = {k: cfg.get(k, "") for k in VALUE_KEYS}
    for k in ("gsmap_folder", "points_file", "output_folder"):
        if values[k]:
            values[k] = str(resolve_path(values[k]))
    values["rain_outputs"] = [p.strip() for p in cfg.get("rain_outputs", "").split(",") if p.strip()]
    values["map_outputs"] = [p.strip() for p in cfg.get("map_outputs", "").split(",") if p.strip()]
    values["shapes"] = []
    for key, value in cfg.items():
        if key.startswith("shape_") and value.count("|") == 1:
            path, field = (p.strip() for p in value.split("|"))
            values["shapes"].append({"name": key[len("shape_"):], "path": str(resolve_path(path)), "id_field": field})
    return values


def shape_info(path: str) -> dict:
    """What the page needs to know of a shapefile: CRS, polygons, columns (with examples), a name for it."""
    import geopandas as gpd
    from core.shapefile import read_shapefile

    p = resolve_path(path)
    read_shapefile(p)   # the checks of the program first: readable, CRS present, polygons present
    raw = gpd.read_file(p)
    columns = []
    for c in raw.columns:
        if c == "geometry":
            continue
        values = raw[c].dropna().astype(str)
        columns.append({"name": c, "unique": int(values.nunique()), "examples": list(values.unique()[:3])})
    name = re.sub(r"[^a-z0-9]+", "_", p.stem.lower()).strip("_") or "shape"
    return {"path": str(p), "name": name, "crs": raw.crs.to_string(), "polygons": len(raw), "columns": columns}


def form_to_config(form: dict) -> dict[str, str]:
    """Keys of the config from the values of the page; empty values are left out (the config keeps its own)."""
    out = {}
    for k in VALUE_KEYS:
        v = str(form.get(k) if form.get(k) is not None else "").strip()
        if v:
            out[k] = v
    for k in ("rain_outputs", "map_outputs"):
        if form.get(k):
            out[k] = ",".join(form[k])
    for s in form.get("shapes", []):
        out[f"shape_{s['name']}"] = f"{s['path']} | {s.get('id_field', '')}"
    return out


def merged_config(config_path, form: dict) -> dict:
    """config/input.txt + config/input.local.txt, then the page (its shapefiles replace every shape_ key)."""
    config, _, _ = read_config_with_local(config_path)
    config = {k: v for k, v in config.items() if not k.startswith("shape_")}
    config.update(form_to_config(form))
    return config


def summary(config_path, form: dict) -> dict:
    """What the run of ``form`` reads (the console summary), checked by the program; nothing is saved."""
    from main import PlanError, prepare_run
    from utils.settings import SettingsError

    try:
        plan = prepare_run(merged_config(config_path, form), form.get("mode", "extract"))
    except (SettingsError, PlanError, FileNotFoundError) as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "lines": plan.summary(), "cells": plan.cells, "hours": plan.hours,
            "values": plan.cells * plan.hours, "extent": plan.extent, "output": str(plan.settings.output_folder),
            "missing_months": plan.missing_months}


def save_local(local_path: Path, form: dict) -> list[str]:
    """Write the values of the page into config/input.local.txt; returns the keys written.

    Keys already there are updated in place, new keys are added at the end, shape_ keys no longer on the
    page are removed; other lines (comments, basemap_relief_file, ...) are kept as they are.
    """
    values = form_to_config(form)
    lines = local_path.read_text(encoding="utf-8").splitlines() if local_path.is_file() else [
        "# Config lokal komputer ini (tidak masuk git), ditulis halaman gsmap-explorer.",
        "# Kunci di sini menimpa kunci yang sama di input.txt."]
    out, done = [], set()
    for line in lines:
        head = line.split("#", 1)[0]
        key = head.split("=", 1)[0].strip() if "=" in head else ""
        if key.startswith("shape_") and key not in values:
            continue                          # a shapefile removed on the page
        if key in values:
            out.append(f"{key} = {values[key]}")
            done.add(key)
        else:
            out.append(line)
    out += [f"{k} = {v}" for k, v in values.items() if k not in done]
    local_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return list(values)


class Job:
    """One run started from the page: its messages, state and the files it wrote."""

    def __init__(self, plan):
        self.plan = plan
        self.lines: list[str] = []
        self.status = "running"          # running, done, failed
        self.error = ""
        self.started = time.time()
        self.finished = None
        self.lock = threading.Lock()

    def write(self, text: str) -> None:
        with self.lock:
            for part in text.splitlines():
                self.lines.append(part)

    def results(self) -> list[dict]:
        """Folders under the output folder holding files written by this run, with their count."""
        root = Path(self.plan.settings.output_folder)
        folders = {}
        if root.is_dir():
            for f in root.rglob("*"):
                try:
                    if f.is_file() and f.stat().st_mtime >= self.started:
                        folders[f.parent] = folders.get(f.parent, 0) + 1
                except OSError:
                    continue
        return [{"path": str(d), "name": str(d.relative_to(root)), "files": n} for d, n in sorted(folders.items())]


class Tee:
    """stdout of the run: still printed in the console window, and kept for the page."""

    def __init__(self, console, job: Job):
        self.console, self.job, self.buffer = console, job, ""

    def write(self, text: str) -> int:
        self.buffer += text
        if "\n" in self.buffer:
            done, self.buffer = self.buffer.rsplit("\n", 1)
            self.job.write(done)
        try:
            self.console.write(text)
        except UnicodeEncodeError:   # console not UTF-8 (run.py sets it; a bare python may not): the page keeps the text
            enc = self.console.encoding or "ascii"
            self.console.write(text.encode(enc, "replace").decode(enc))
        return len(text)

    def flush(self) -> None:
        self.console.flush()


def _run_job(job: Job) -> None:
    from main import execute

    tee = Tee(sys.stdout, job)
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = tee
    try:
        execute(job.plan)
        job.status = "done"
    except Exception as exc:   # noqa: BLE001 - shown on the page; the server keeps running
        job.write("".join(traceback.format_exception(exc)[-3:]))
        job.error = f"{type(exc).__name__}: {exc}"
        job.status = "failed"
    finally:
        if tee.buffer:
            job.write(tee.buffer)
        sys.stdout, sys.stderr = old_out, old_err
        job.finished = time.time()


def start_run(server, form: dict) -> dict:
    """Save the page's values, check and size the run, then start it in a thread (one at a time)."""
    from main import PlanError, prepare_run
    from utils.settings import SettingsError

    if server.job is not None and server.job.status == "running":
        return {"ok": False, "message": "Masih ada proses yang berjalan."}
    save_local(local_config_path(server.config_path), form)
    try:
        plan = prepare_run(merged_config(server.config_path, form), form.get("mode", "extract"))
    except (SettingsError, PlanError, FileNotFoundError) as exc:
        return {"ok": False, "message": str(exc)}
    job = Job(plan)
    job.write("\n".join(plan.summary()))
    server.job = job
    threading.Thread(target=_run_job, args=(job,), daemon=True).start()
    return {"ok": True}


def job_state(server, since: int) -> dict:
    job = server.job
    if job is None:
        return {"status": "none", "lines": [], "next": 0}
    with job.lock:
        lines = job.lines[since:]
        nxt = len(job.lines)
    end = job.finished or time.time()
    state = {"status": job.status, "lines": lines, "next": nxt, "seconds": round(end - job.started),
             "error": job.error}
    if job.status != "running":
        state["results"] = job.results()
    return state


def open_folder(server, path: str) -> dict:
    """Open a result folder in Explorer; only folders inside the output folder of the last run."""
    job = server.job
    if job is None:
        raise ValueError("belum ada hasil")
    folder = Path(path).resolve()
    root = Path(job.plan.settings.output_folder).resolve()
    if not folder.is_dir() or not folder.is_relative_to(root):
        raise ValueError(f"{folder} bukan folder hasil run ini")
    if os.name == "nt":
        os.startfile(folder)
    return {"ok": True}


def points_info(path: str) -> dict:
    """Points of a CSV name,lat,lon, checked as the program does."""
    from apps.extract_points import read_points_file

    p = resolve_path(path)
    pts = read_points_file(p)
    return {"path": str(p), "count": len(pts), "names": list(pts["name"][:5])}


def drives() -> list[str]:
    """Drive roots of this computer (Windows) or ``/``."""
    if os.name != "nt":
        return ["/"]
    return [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]


def browse(path: str | None, kind: str) -> dict:
    """The folders of ``path`` (and its files of ``kind``), or the drives when ``path`` is empty."""
    if kind not in FILE_KINDS:
        raise ValueError(f"kind {kind!r}")
    if not path:
        return {"path": "", "parent": None, "entries": [{"name": d, "path": d, "type": "dir"} for d in drives()]}
    folder = resolve_path(path)
    if not folder.is_dir():
        raise ValueError(f"{folder} bukan folder")
    entries = []
    try:
        for p in sorted(folder.iterdir(), key=lambda q: q.name.lower()):
            if p.name.startswith(("$", ".")):
                continue
            try:
                if p.is_dir():
                    entries.append({"name": p.name, "path": str(p), "type": "dir"})
                elif p.suffix.lower() in FILE_KINDS[kind]:
                    entries.append({"name": p.name, "path": str(p), "type": "file"})
            except OSError:   # an entry that cannot be read (link, permission)
                continue
    except PermissionError:
        raise ValueError(f"{folder}: tidak ada izin membuka folder ini") from None
    parent = folder.parent
    return {"path": str(folder), "parent": "" if parent == folder else str(parent), "entries": entries}


def check_data(path: str) -> dict:
    """GSMaP monthly files in ``path`` or one level of subfolders (year folders): what the page shows."""
    if not path:
        return {"ok": False, "message": "Pilih folder data GSMaP."}
    folder = resolve_path(path)
    if not folder.is_dir():
        return {"ok": False, "message": f"Folder tidak ditemukan: {folder}"}
    months, dupes = {}, []
    files = list(folder.glob("*.nc")) + list(folder.glob("*/*.nc"))
    for f in files:
        m = MONTH_FILE.search(f.name)
        if m:
            ym = f"{m.group(1)}-{m.group(2)}"
            if ym in months:
                dupes.append(ym)
            months[ym] = f
    if not months:
        return {"ok": False, "message": "Tidak ada berkas GSMaP bulanan (*_YYYYMM.nc atau *_YYYY_MM.nc) di folder "
                                        "ini atau subfolder tahunnya."}
    if dupes:
        return {"ok": False, "message": f"Ada dua berkas untuk bulan yang sama ({', '.join(sorted(set(dupes))[:3])}): "
                                        f"satu folder hanya untuk satu produk."}
    keys = sorted(months)
    product = "_".join(folder.parts[-4:-1]) if folder.name == "NC" else folder.name
    return {"ok": True, "product": product, "first": keys[0], "last": keys[-1], "count": len(keys),
            "message": f"{product}, data tersedia {keys[0]} .. {keys[-1]} ({len(keys)} bulan)"}


class Handler(BaseHTTPRequestHandler):
    server_version = "gsmap-explorer"

    def log_message(self, *args):   # no access log in the console
        pass

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, data) -> None:
        self._send(code, json.dumps(data).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        if urlparse(self.path).path == "/":
            page = PAGE.read_text(encoding="utf-8").replace("__TOKEN__", self.server.token)
            self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.headers.get("X-Token") != self.server.token:
            self._json(403, {"error": "token"})
            return
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            if path == "/api/info":
                config, _, _ = read_config_with_local(self.server.config_path)
                self._json(200, {"program_dir": str(PROGRAM_DIR), "config": str(self.server.config_path),
                                 "values": current_values(config),
                                 "options": {"modes": list(MODES), "regions": list(EXTRACT_REGIONS),
                                             "time_zones": list(TIME_ZONE_HOURS), "rain_outputs": list(RAIN_OUTPUTS),
                                             "map_outputs": list(MAP_OUTPUTS)}})
            elif path == "/api/browse":
                self._json(200, browse(body.get("path"), body.get("kind", "folder")))
            elif path == "/api/check_data":
                self._json(200, check_data(body.get("path", "")))
            elif path == "/api/shape_info":
                self._json(200, shape_info(body.get("path", "")))
            elif path == "/api/points_info":
                self._json(200, points_info(body.get("path", "")))
            elif path == "/api/summary":
                self._json(200, summary(self.server.config_path, body))
            elif path == "/api/run":
                self._json(200, start_run(self.server, body))
            elif path == "/api/job":
                self._json(200, job_state(self.server, int(body.get("since", 0))))
            elif path == "/api/open_folder":
                self._json(200, open_folder(self.server, body.get("path", "")))
            elif path == "/api/save":
                keys = save_local(local_config_path(self.server.config_path), body)
                self._json(200, {"ok": True, "file": str(local_config_path(self.server.config_path)), "keys": keys})
            elif path == "/api/quit":
                self._json(200, {"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                self._json(404, {"error": "not found"})
        except (ValueError, OSError) as exc:   # shown on the page, the server keeps running
            self._json(400, {"error": str(exc)})


def make_server(config_path) -> ThreadingHTTPServer:
    """A server on 127.0.0.1 at a free port, with a fresh token."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.token = secrets.token_urlsafe(16)
    server.config_path = Path(config_path)
    server.job = None
    return server


def serve(config_path, open_browser: bool = True) -> None:
    """Start the page and wait until it is closed."""
    server = make_server(config_path)
    url = f"http://127.0.0.1:{server.server_port}/"
    print("=" * 60)
    print("  gsmap-explorer berjalan di peramban:")
    print(f"  {url}")
    print("  Biarkan jendela ini terbuka. Tutup jendela ini (atau tombol")
    print("  'Tutup program' di halaman) untuk berhenti.")
    print("=" * 60, flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("gsmap-explorer ditutup.")
