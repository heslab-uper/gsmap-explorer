import argparse
import os
import sys

# supaya bisa akses src/ (di samping run.py, dari folder mana pun dijalankan)
PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(PROGRAM_DIR, "src"))

# Keluaran selalu UTF-8: tanpa ini print berisi "✅" berhenti dengan UnicodeEncodeError
# (cp1252) saat keluaran dialihkan ke berkas atau pipe di Windows, mis. run terjadwal.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

from main import MODES, run_pipeline  # noqa: E402

LABELS = {"extract": "Extract (hujan jam-jaman, harian, bulanan, tahunan, maksimum harian)",
          "visualize": "Visualisasi (peta hujan)",
          "thiessen": "Thiessen (hujan wilayah per shapefile)"}


def pilih_mode():
    print("=" * 30)
    print("      PILIH MODE PROGRAM")
    print("=" * 30)
    for k, m in enumerate(MODES, 1):
        print(f"{k}. {LABELS[m]}")
    print()
    while True:
        try:
            choice = input(f"Pilih opsi (1-{len(MODES)}): ").strip()
        except EOFError:
            raise SystemExit("Dibatalkan.") from None
        if choice.isdigit() and 1 <= int(choice) <= len(MODES):
            return MODES[int(choice) - 1]
        print("Pilihan tidak valid!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=MODES, help="Pilih mode (tanpa ini: menu)")
    parser.add_argument("--config", default=os.path.join(PROGRAM_DIR, "config", "input.txt"),
                        help="Berkas config (bawaan: config/input.txt di samping run.py)")
    parser.add_argument("--no-menu", action="store_true",
                        help="Tanpa pertanyaan Lanjut? (mis. run terjadwal)")
    args = parser.parse_args()
    mode = args.mode if args.mode else pilih_mode()
    run_pipeline(mode=mode, config_path=args.config, menu=not args.no_menu)
