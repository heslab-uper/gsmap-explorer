import sys
import os
import argparse

# supaya bisa akses src/ (di samping run.py, dari folder mana pun dijalankan)
PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(PROGRAM_DIR, "src"))

from main import run_pipeline


def pilih_mode():
    print("=" * 30)
    print("      PILIH MODE PROGRAM")
    print("=" * 30)
    print("1. Extract CSV")
    print("2. Visualisasi")
    print("3. Hujan Regional (Thiessen)")
    print("4. Analisis Hujan (kala ulang, IDF, karakteristik jam-jaman)")
    print("5. Ekstraksi Deret Hujan (titik / box / batas shapefile)")
    print("6. Semua")
    print()

    mapping = {
        "1": "extract",
        "2": "visualize",
        "3": "thiessen",
        "4": "analysis",
        "5": "series",
        "6": "all"
    }

    while True:
        choice = input("Pilih opsi (1/2/3/4/5/6): ").strip()

        if choice in mapping:
            return mapping[choice]

        print("Pilihan tidak valid!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mode",
        choices=["extract", "visualize", "thiessen", "analysis", "series", "all"],
        help="Pilih mode"
    )
    parser.add_argument(
        "--config",
        default=os.path.join(PROGRAM_DIR, "config", "input.txt"),
        help="Berkas config (bawaan: config/input.txt di samping run.py)"
    )
    parser.add_argument(
        "--no-menu",
        action="store_true",
        help="Mode series: pakai nilai config tanpa pertanyaan di layar"
    )

    args = parser.parse_args()

    # Jika --mode tidak diberikan → tampilkan menu
    mode = args.mode if args.mode else pilih_mode()

    run_pipeline(mode=mode, config_path=args.config, menu=not args.no_menu)