"""Bukti bahwa layanan Flask memproses citra sama persis dengan data pelatihan.

Beberapa citra uji asli diproses lewat fungsi yang dipakai app.py, lalu
dibandingkan dengan citra uji yang dibaca Keras saat evaluasi.
"""

import csv
import json

import cv2
import keras
import numpy as np
import tensorflow as tf

import config
import prapemrosesan as pp

FOLDER_BUKTI = config.FOLDER_BUKTI / "06_layanan_flask"


def main():
    FOLDER_BUKTI.mkdir(parents=True, exist_ok=True)
    sisi = json.loads(config.FILE_PRAPEMROSESAN.read_text(encoding="utf-8"))["sisi_potong"]
    model = keras.models.load_model(str(config.FILE_MODEL_AKHIR))
    folder_asli = {kelas: folder for folder, kelas in config.KELAS_ASLI.items()}

    with open(config.FOLDER_BUKTI / "03_pembagian_dataset" / "pembagian_dataset.csv", encoding="utf-8") as f:
        uji = [b for b in csv.DictReader(f) if b["bagian"] == "uji"]
    contoh = uji[:5] + uji[-5:]

    baris = [f"{'berkas':<22}{'selisih piksel maks':>21}{'peluang (Flask)':>17}{'peluang (Keras)':>17}"]
    selisih_terbesar = 0.0
    for b in contoh:
        path_asli = config.FOLDER_DATASET / folder_asli[b["kelas"]] / b["berkas"].replace(".png", ".jpg")
        dari_flask = pp.ke_masukan_model(pp.proses_citra(cv2.imread(str(path_asli)), sisi))

        png = tf.io.decode_png(tf.io.read_file(str(config.FOLDER_OLAH / "uji" / b["kelas"] / b["berkas"])), channels=3)
        dari_keras = png.numpy().astype(np.float32) / 255.0

        selisih = float(np.abs(dari_flask - dari_keras).max())
        selisih_terbesar = max(selisih_terbesar, selisih)
        p_flask = float(model(dari_flask[np.newaxis], training=False)[0][0])
        p_keras = float(model(dari_keras[np.newaxis], training=False)[0][0])
        baris.append(f"{b['berkas']:<22}{selisih:>21.6f}{p_flask:>17.4f}{p_keras:>17.4f}")

    baris.append("")
    baris.append("HASIL: prapemrosesan identik" if selisih_terbesar == 0
                 else f"HASIL: ada selisih {selisih_terbesar}, periksa urutan kanal atau resize")
    laporan = "\n".join(baris)
    print(laporan)
    (FOLDER_BUKTI / "cek_konsistensi.txt").write_text(laporan + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
