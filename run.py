import sys
import os
import argparse

# supaya bisa akses src/ (di samping run.py, dari folder mana pun dijalankan)
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from main import run_pipeline


def pilih_mode():
    print("=" * 30)
    print("      PILIH MODE PROGRAM")
    print("=" * 30)
    print("1. Extract CSV")
    print("2. Visualisasi")
    print("3. Hujan Regional (Thiessen)")
    print("4. Analisis Hujan (kala ulang, IDF, karakteristik jam-jaman)")
    print("5. Hujan di Titik Koordinat (jam-an dan harian)")
    print("6. Semua")
    print()

    mapping = {
        "1": "extract",
        "2": "visualize",
        "3": "thiessen",
        "4": "analysis",
        "5": "points",
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
        choices=["extract", "visualize", "thiessen", "analysis", "points", "all"],
        help="Pilih mode"
    )
    parser.add_argument(
        "--config",
        default="config/input.txt",
        help="Berkas config (bawaan: config/input.txt)"
    )

    args = parser.parse_args()

    # Jika --mode tidak diberikan → tampilkan menu
    mode = args.mode if args.mode else pilih_mode()

    run_pipeline(mode=mode, config_path=args.config)