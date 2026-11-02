"""Build docs/manual.pdf from docs/manual.md (for the developer, not for users).

Markdown -> HTML with the `markdown` package (env heslab-dev), then HTML -> PDF
with Microsoft Edge in headless mode (no pandoc or LaTeX needed). Users get the
PDF as it is; they need neither package.

    python docs/build_manual.py                     # writes docs/manual.pdf
    python docs/build_manual.py --output D:/x.pdf   # another output file
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import markdown

DOCS = Path(__file__).resolve().parent
SOURCE = DOCS / "manual.md"
OUTPUT = DOCS / "manual.pdf"

CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10.5pt;
       line-height: 1.45; color: #1a1a1a; }
h1 { font-size: 20pt; border-bottom: 2px solid #1f5f8b; padding-bottom: 4px; }
h2 { font-size: 14pt; color: #1f5f8b; margin-top: 1.4em;
     break-after: avoid; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin-top: 1.1em; break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 0.6em 0;
        font-size: 9.5pt; break-inside: avoid; }
th, td { border: 1px solid #b8c4cc; padding: 3px 6px; text-align: left;
         vertical-align: top; }
th { background: #e8eff4; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #f1f3f5;
       padding: 0 2px; }
pre { background: #f1f3f5; padding: 6px 8px; border-radius: 3px;
      white-space: pre-wrap; break-inside: avoid; }
pre code { padding: 0; }
blockquote { border-left: 3px solid #1f5f8b; margin-left: 0; padding-left: 10px;
             color: #333; }
.toc { border: 1px solid #b8c4cc; padding: 4px 12px; margin: 1em 0; }
.toc ul { list-style: none; padding-left: 1em; }
.toc > ul { padding-left: 0; }
a { color: #1f5f8b; text-decoration: none; }
"""


def find_edge():
    """Path of msedge.exe: MSEDGE_EXE, then the standard install folders."""
    candidates = [os.environ.get("MSEDGE_EXE")]
    for var in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        root = os.environ.get(var)
        if root:
            candidates.append(os.path.join(root, "Microsoft", "Edge", "Application", "msedge.exe"))
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    sys.exit("Microsoft Edge not found; set MSEDGE_EXE to the path of msedge.exe.")


def wait_for_file(path, timeout):
    """True once path exists with a non-zero size that is the same twice in a row."""
    last = -1
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        size = path.stat().st_size if path.is_file() else 0
        if size > 0 and size == last:
            return True
        last = size
        time.sleep(1)
    return False


def to_html(text):
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "toc"],
        extension_configs={"toc": {"title": "Daftar isi", "toc_depth": "2"}},
    )
    return (
        '<!doctype html><html lang="id"><head><meta charset="utf-8">'
        f"<title>Petunjuk GSMaP Explorer</title><style>{CSS}</style></head>"
        f"<body>{body}</body></html>"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUTPUT, help=f"PDF to write (default {OUTPUT})")
    args = parser.parse_args()
    output = args.output.resolve()

    print(f"source : {SOURCE}")
    print(f"output : {output}")
    edge = find_edge()
    print(f"edge   : {edge}")

    work = Path(tempfile.mkdtemp(prefix="gsmap_manual_"))
    try:
        page = work / "manual.html"
        page.write_text(to_html(SOURCE.read_text(encoding="utf-8")), encoding="utf-8")
        pdf = work / "manual.pdf"
        # Own profile folder, so a running Edge window does not take the job over.
        subprocess.run(
            [edge, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--user-data-dir={work / 'profile'}", f"--print-to-pdf={pdf}", page.as_uri()],
            check=True, timeout=120, capture_output=True,
        )
        # msedge.exe may return before the PDF is written (checked 2026-11-01):
        # wait until the file exists and its size stops changing.
        if not wait_for_file(pdf, timeout=60):
            sys.exit("Edge wrote no PDF within 60 s.")
        output.parent.mkdir(parents=True, exist_ok=True)
        tmp = output.with_name(output.name + ".new")
        shutil.copyfile(pdf, tmp)
        os.replace(tmp, output)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"written: {output} ({output.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
