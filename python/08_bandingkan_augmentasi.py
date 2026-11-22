"""Bahan pembahasan: pengaruh augmentasi pada keempat skenario.

Membandingkan tiga run dari ringkasan.json masing-masing (tanpa model dan tanpa data uji):
tanpa augmentasi, rotasi bebas (arsip run pertama), dan rotasi 4 arah (run akhir).
Selisih akurasi latih dan validasi di epoch terbaik dipakai sebagai petunjuk overfitting.
"""

import csv
import json

import matplotlib.pyplot as plt
import numpy as np

import config

RUN = [
    ("Tanpa augmentasi", config.FOLDER_BUKTI / "tanpa_augmentasi"),
    ("Rotasi bebas (arsip)", config.FOLDER_BUKTI / "arsip_rotasi_bebas" / "04_pelatihan"),
    ("Rotasi 4 arah (akhir)", config.FOLDER_BUKTI / "04_pelatihan"),
]
FOLDER_BUKTI = config.FOLDER_BUKTI / "tanpa_augmentasi"


def main():
    baris = []
    for nama_run, folder in RUN:
        for skenario in config.SKENARIO:
            path = folder / skenario / "ringkasan.json"
            if not path.exists():
                raise SystemExit(f"{path} belum ada.")
            r = json.loads(path.read_text(encoding="utf-8"))
            baris.append({
                "run": nama_run,
                "skenario": skenario.upper(),
                "epoch_dijalankan": r["epoch_dijalankan"],
                "epoch_terbaik": r["epoch_terbaik"],
                "val_loss_terbaik": r["val_loss_terbaik"],
                "val_akurasi": r["val_accuracy_epoch_terbaik"],
                "akurasi_latih": r["accuracy_latih_epoch_terbaik"],
                "selisih_latih_minus_validasi": round(r["accuracy_latih_epoch_terbaik"] - r["val_accuracy_epoch_terbaik"], 4),
                "durasi_menit": r["durasi_menit"],
            })

    with open(FOLDER_BUKTI / "perbandingan_augmentasi.csv", "w", newline="", encoding="utf-8") as f:
        penulis = csv.DictWriter(f, fieldnames=list(baris[0].keys()))
        penulis.writeheader()
        penulis.writerows(baris)

    print(f"{'Run':<24}{'Skenario':<10}{'Epoch':>6}{'Terbaik':>8}{'Val loss':>10}{'Val acc':>9}{'Latih acc':>11}{'Selisih':>9}")
    for b in baris:
        print(f"{b['run']:<24}{b['skenario']:<10}{b['epoch_dijalankan']:>6}{b['epoch_terbaik']:>8}{b['val_loss_terbaik']:>10.4f}"
              f"{b['val_akurasi']:>9.4f}{b['akurasi_latih']:>11.4f}{b['selisih_latih_minus_validasi']:>9.4f}")

    skenario = [s.upper() for s in config.SKENARIO]
    lebar = 0.27
    posisi = np.arange(len(skenario))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6))
    for i, (nama_run, _) in enumerate(RUN):
        data = [b for b in baris if b["run"] == nama_run]
        ax1.bar(posisi + (i - 1) * lebar, [b["val_loss_terbaik"] for b in data], lebar, label=nama_run)
        ax2.bar(posisi + (i - 1) * lebar, [b["selisih_latih_minus_validasi"] * 100 for b in data], lebar, label=nama_run)
    ax1.set_title("Loss validasi terbaik (makin kecil makin baik)")
    ax2.set_title("Akurasi latih dikurangi akurasi validasi (poin persen)")
    ax2.axhline(0, color="black", linewidth=0.8)
    for ax in (ax1, ax2):
        ax.set_xticks(posisi, skenario)
        ax.grid(axis="y", alpha=0.3)
        ax.legend(fontsize=9)
    fig.savefig(FOLDER_BUKTI / "perbandingan_augmentasi.png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"\nDisimpan ke {FOLDER_BUKTI}")


if __name__ == "__main__":
    main()
