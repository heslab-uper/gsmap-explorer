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


def resolve_path(text) -> Path:
    """``text`` as an absolute path; a relative one is taken from the folder of run.py."""
    p = Path(text).expanduser()
    return p if p.is_absolute() else PROGRAM_DIR / p
