"""Confusion matrix data uji setiap skenario untuk lampiran naskah (27 November 2026).

Dihitung ulang dari bukti/05_evaluasi/semua_skenario/prediksi_uji_s*.csv; gaya gambar sama dengan
confusion_matrix_validasi.png hasil 04_latih.py. Argumen: folder gambar/lampiran naskah LaTeX.
"""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import config

TUJUAN = Path(sys.argv[1])


def main():
    for s in config.SKENARIO:
        with open(config.FOLDER_BUKTI / "05_evaluasi" / "semua_skenario" / f"prediksi_uji_{s}.csv", encoding="utf-8") as f:
            data = list(csv.DictReader(f))
        # baris = label sebenarnya (Layak, Tidak Layak), kolom = prediksi (Layak, Tidak Layak)
        cm = np.zeros((2, 2), int)
        for b in data:
            cm[1 - int(b["label"]), 1 - int(b["prediksi"])] += 1
        fig, ax = plt.subplots(figsize=(4.8, 4.1))
        ax.imshow(cm, cmap="Blues", vmin=0, vmax=cm.max())
        for i in range(2):
            for j in range(2):
                ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=16,
                        color="white" if cm[i, j] > cm.max() / 2 else "black")
        ax.set_xticks([0, 1], ["Prediksi Layak", "Prediksi Tidak Layak"])
        ax.set_yticks([0, 1], ["Layak", "Tidak Layak"])
        ax.set_ylabel("Label sebenarnya")
        ax.set_title(f"Confusion matrix data uji {s.upper()}")
        fig.tight_layout()
        fig.savefig(TUJUAN / f"cm_uji_{s}.png", dpi=150)
        plt.close(fig)
        print(s, "TP FN FP TN =", cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1])


if __name__ == "__main__":
    main()
