"""Read ``config/input.txt``: one ``key = value`` per line, ``#`` starts a comment."""

from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parents[2]
"""Folder of run.py; relative paths in the config are taken from here."""


def read_config(path) -> dict[str, str]:
    """Keys and values as text. An empty value stays ``""``; quotes around a value are removed.

    A key given twice is an error (the second would silently win).
    """
    config, lines = {}, {}
    with open(path, encoding="utf-8-sig") as f:
        for n, line in enumerate(f, 1):
            line = line.split("#", 1)[0].strip()
            if not line or "=" not in line:
                continue
            key, val = (p.strip() for p in line.split("=", 1))
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
                val = val[1:-1].strip()
            if key in config:
                raise ValueError(f"{path}: key '{key}' given twice (lines {lines[key]} and {n})")
            config[key], lines[key] = val, n
    return config


def local_config_path(path) -> Path:
    """``config/input.txt`` -> ``config/input.local.txt``: machine values, not in the repository."""
    path = Path(path)
    return path.with_name(f"{path.stem}.local{path.suffix}")


def read_config_with_local(path) -> tuple[dict[str, str], Path | None, list[str]]:
    """The config, with every key of the local config (if present) replacing its value.

    Returns the merged keys, the local file (None when absent) and the keys it set.
    """
    config = read_config(path)
    local = local_config_path(path)
    if not local.is_file():
        return config, None, []
    overrides = read_config(local)
    config.update(overrides)
    return config, local, list(overrides)


def resolve_path(text) -> Path:
    """``text`` as an absolute path; a relative one is taken from the folder of run.py."""
    p = Path(text).expanduser()
    return p if p.is_absolute() else PROGRAM_DIR / p
