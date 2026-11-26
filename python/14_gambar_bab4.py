"""Bahan gambar dan tabel BAB IV dari hasil yang sudah ada (model tidak dilatih ulang).

Membaca:
- bukti/04_pelatihan/s1-s4/riwayat_epoch.csv dan ringkasan.json
- bukti/05_evaluasi/semua_skenario/prediksi_uji_s1-s4.csv (hasil 11_evaluasi_semua_skenario.py)
- dataset/jenis_kerusakan.csv
Menulis ke bukti/05_evaluasi/semua_skenario/:
- kurva_empat_skenario.png, confusion_matrix_empat_skenario.png
- salah_prediksi_<skenario sistem>.jpg, kesalahan_per_jenis_kerusakan_<skenario sistem>.csv
"""

import collections
import csv
import json

import cv2
import matplotlib.pyplot as plt
import numpy as np

import config

FOLDER_PELATIHAN = config.FOLDER_BUKTI / "04_pelatihan"
FOLDER = config.FOLDER_BUKTI / "05_evaluasi" / "semua_skenario"
UKURAN = 224


def baca_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# Ukuran gambar dibuat dekat dengan ukuran cetak (lebar teks 14 cm), sehingga huruf 10 pt tetap terbaca.
plt.rcParams.update({"font.size": 10})


def kurva():
    # Akurasi dan loss dipisah menjadi dua gambar 2 x 2 agar masing-masing muat satu halaman.
    for kunci, judul, berkas in (("accuracy", "Akurasi", "kurva_akurasi_empat_skenario.png"),
                                 ("loss", "Loss", "kurva_loss_empat_skenario.png")):
        fig, sumbu = plt.subplots(2, 2, figsize=(6.8, 5.0), sharex=False)
        for ax, nama in zip(sumbu.ravel(), config.SKENARIO):
            r = baca_csv(FOLDER_PELATIHAN / nama / "riwayat_epoch.csv")
            ring = json.loads((FOLDER_PELATIHAN / nama / "ringkasan.json").read_text(encoding="utf-8"))
            epoch = [int(b["epoch"]) + 1 for b in r]
            ax.plot(epoch, [float(b[kunci]) for b in r], label="latih")
            ax.plot(epoch, [float(b["val_" + kunci]) for b in r], label="validasi")
            ax.axvline(ring["epoch_terbaik"], color="gray", linestyle="--", linewidth=1)
            ax.set_title(f"{judul} {nama.upper()} ({ring['jumlah_blok']} blok, batch {ring['ukuran_batch']})")
            ax.set_xlabel("epoch")
            ax.grid(alpha=0.3)
        sumbu[0, 0].legend()
        fig.tight_layout()
        fig.savefig(FOLDER / berkas, dpi=200)
        plt.close(fig)


def confusion_matrix():
    fig, sumbu = plt.subplots(2, 2, figsize=(6.2, 5.6))
    for ax, nama in zip(sumbu.ravel(), config.SKENARIO):
        p = baca_csv(FOLDER / f"prediksi_uji_{nama}.csv")
        y = np.array([int(b["label"]) for b in p])
        yt = np.array([int(b["prediksi"]) for b in p])
        m = np.array([[np.sum((y == 1) & (yt == 1)), np.sum((y == 1) & (yt == 0))],
                      [np.sum((y == 0) & (yt == 1)), np.sum((y == 0) & (yt == 0))]])
        ax.imshow(m, cmap="Blues", vmin=0, vmax=75)
        for (i, j), v in np.ndenumerate(m):
            ax.text(j, i, f"{['TP', 'FN', 'FP', 'TN'][i * 2 + j]} = {v}", ha="center", va="center",
                    fontsize=12, color="white" if v > 40 else "black")
        ax.set_xticks([0, 1], ["Prediksi\nLayak", "Prediksi\nTidak Layak"])
        ax.set_yticks([0, 1], ["Layak", "Tidak\nLayak"])
        ax.set_title(nama.upper())
    for ax in sumbu[:, 0]:
        ax.set_ylabel("Label sebenarnya")
    fig.tight_layout()
    fig.savefig(FOLDER / "confusion_matrix_empat_skenario.png", dpi=200)
    plt.close(fig)


def salah_model_sistem():
    """Citra uji yang salah diprediksi model sistem (config.SKENARIO_SISTEM)."""
    sk = config.SKENARIO_SISTEM
    jenis = {b["berkas"].replace(".jpg", ".png"): b["jenis_kerusakan"]
             for b in baca_csv(config.FOLDER_DATASET / "jenis_kerusakan.csv")}
    p = baca_csv(FOLDER / f"prediksi_uji_{sk}.csv")
    for b in p:
        b["keterangan"] = {("1", "1"): "TP", ("1", "0"): "FN", ("0", "1"): "FP", ("0", "0"): "TN"}[(b["label"], b["prediksi"])]
    salah = sorted((b for b in p if b["keterangan"] in ("FP", "FN")), key=lambda b: (b["keterangan"], b["berkas"]))

    kolom = 6
    baris = (len(salah) + kolom - 1) // kolom
    lembar = np.full((baris * (UKURAN + 64), kolom * (UKURAN + 8), 3), 255, np.uint8)
    for i, b in enumerate(salah):
        citra = cv2.imread(str(config.FOLDER_OLAH / "uji" / config.NAMA_KELAS[int(b["label"])] / b["berkas"]))
        r, k = divmod(i, kolom)
        y, x = r * (UKURAN + 64), k * (UKURAN + 8)
        lembar[y:y + UKURAN, x:x + UKURAN] = citra
        for j, t in enumerate((f"{b['keterangan']}  {b['berkas'].replace('.png', '')}",
                               f"skor {b['skor_kepercayaan_persen']}%",
                               jenis.get(b["berkas"], "-").replace("_", " "))):
            cv2.putText(lembar, t, (x + 2, y + UKURAN + 17 + j * 19), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    cv2.imwrite(str(FOLDER / f"salah_prediksi_{sk}.jpg"), lembar)

    total, lolos = collections.Counter(), collections.Counter()
    for b in p:
        if b["label"] == "0":
            total[jenis.get(b["berkas"], "-")] += 1
            lolos[jenis.get(b["berkas"], "-")] += b["keterangan"] == "FP"
    with open(FOLDER / f"kesalahan_per_jenis_kerusakan_{sk}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["jenis_kerusakan", "jumlah_di_data_uji", "lolos_sebagai_layak_FP"])
        for j, n in total.most_common():
            w.writerow([j, n, lolos[j]])
    print(f"Salah prediksi {sk.upper()}:")
    for b in salah:
        print(f"  {b['keterangan']} {b['berkas']:<22} skor {b['skor_kepercayaan_persen']:>6}%  {jenis.get(b['berkas'], '-')}")
    print(f"\nJenis kerusakan (data uji {sk.upper()}): jumlah / lolos FP")
    for j, n in total.most_common():
        print(f"  {j:<26}{n:>4}{lolos[j]:>4}")


def sebaran():
    fig, sumbu = plt.subplots(2, 2, figsize=(6.8, 5.2), sharey=True)
    for ax, nama in zip(sumbu.ravel(), config.SKENARIO):
        p = baca_csv(FOLDER / f"prediksi_uji_{nama}.csv")
        skor = np.array([float(b["skor_kepercayaan_persen"]) for b in p])
        salah = np.array([b["label"] != b["prediksi"] for b in p])
        ax.hist([skor[~salah], skor[salah]], bins=np.linspace(50, 100, 11), stacked=True,
                label=["benar", "salah"], color=["#4c78a8", "#e45756"])
        ax.set_title(f"{nama.upper()}: {int(salah.sum())} salah, {int((skor >= 99.99).sum())} skor 99,99%")
        ax.set_xlabel("skor kepercayaan (%)")
        ax.grid(alpha=0.3)
    for ax in sumbu[:, 0]:
        ax.set_ylabel("jumlah citra uji")
    sumbu[0, 0].legend()
    fig.tight_layout()
    fig.savefig(FOLDER / "sebaran_skor_kepercayaan.png", dpi=200)
    plt.close(fig)

if __name__ == "__main__":
    kurva()
    confusion_matrix()
    sebaran()
    salah_model_sistem()
