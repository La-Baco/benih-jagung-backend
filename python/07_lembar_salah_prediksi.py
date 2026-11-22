"""Bahan telaah FP dan FN menurut jenis kerusakan (Subbab 3.10 langkah 3).

Membaca prediksi_data_uji.csv hasil 05_evaluasi.py dan dataset/jenis_kerusakan.csv,
lalu menyusun lembar citra yang salah diprediksi dan tabel kesalahan per jenis kerusakan.
Model tidak dijalankan lagi di sini.
"""

import collections
import csv

import cv2
import numpy as np

import config

FOLDER_BUKTI = config.FOLDER_BUKTI / "05_evaluasi"
FILE_JENIS = config.FOLDER_DATASET / "jenis_kerusakan.csv"
UKURAN = 224


def baca_jenis():
    if not FILE_JENIS.exists():
        return {}
    with open(FILE_JENIS, encoding="utf-8") as f:
        return {b["berkas"].replace(".jpg", ".png"): b["jenis_kerusakan"] for b in csv.DictReader(f)}


def simpan_lembar(salah, jenis):
    kolom = 6
    baris = (len(salah) + kolom - 1) // kolom
    lembar = np.full((baris * (UKURAN + 64), kolom * (UKURAN + 8), 3), 255, np.uint8)
    for i, b in enumerate(salah):
        kelas = config.NAMA_KELAS[int(b["label"])]
        citra = cv2.imread(str(config.FOLDER_OLAH / "uji" / kelas / b["berkas"]))
        r, k = divmod(i, kolom)
        y, x = r * (UKURAN + 64), k * (UKURAN + 8)
        lembar[y:y + UKURAN, x:x + UKURAN] = citra
        teks = [
            f"{b['keterangan']}  {b['berkas'].replace('.png', '')}",
            f"peluang layak {float(b['peluang_layak']):.4f}",
            jenis.get(b["berkas"], "-").replace("_", " "),
        ]
        for j, t in enumerate(teks):
            cv2.putText(lembar, t, (x + 2, y + UKURAN + 17 + j * 19), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    cv2.imwrite(str(FOLDER_BUKTI / "salah_prediksi_data_uji.jpg"), lembar)


def main():
    with open(FOLDER_BUKTI / "prediksi_data_uji.csv", encoding="utf-8") as f:
        prediksi = list(csv.DictReader(f))
    jenis = baca_jenis()

    salah = sorted((b for b in prediksi if b["keterangan"] in ("FP", "FN")), key=lambda b: (b["keterangan"], b["berkas"]))
    simpan_lembar(salah, jenis)

    print(f"Citra uji yang salah diprediksi: {len(salah)}")
    for b in salah:
        print(f"  {b['keterangan']}  {b['berkas']:<22} peluang layak {float(b['peluang_layak']):.4f}  "
              f"jenis kerusakan: {jenis.get(b['berkas'], '-')}")

    # Hanya benih tidak layak yang punya jenis kerusakan; kesalahannya selalu berupa FP.
    total = collections.Counter()
    lolos = collections.Counter()
    for b in prediksi:
        if b["label"] == "0":
            j = jenis.get(b["berkas"], "-")
            total[j] += 1
            if b["keterangan"] == "FP":
                lolos[j] += 1

    with open(FOLDER_BUKTI / "kesalahan_per_jenis_kerusakan.csv", "w", newline="", encoding="utf-8") as f:
        penulis = csv.writer(f)
        penulis.writerow(["jenis_kerusakan", "jumlah_di_data_uji", "lolos_sebagai_layak_FP", "persen_lolos"])
        print(f"\n{'Jenis kerusakan (data uji)':<28}{'Jumlah':>8}{'FP':>5}{'Lolos':>9}")
        for j, n in total.most_common():
            persen = lolos[j] / n * 100
            penulis.writerow([j, n, lolos[j], f"{persen:.1f}"])
            print(f"{j:<28}{n:>8}{lolos[j]:>5}{persen:>8.1f}%")
    print(f"\nDisimpan ke {FOLDER_BUKTI}")


if __name__ == "__main__":
    main()
