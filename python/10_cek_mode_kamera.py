"""Bukti bahwa endpoint /deteksi (mode kamera) memberi kelas yang sama dengan /predict.

Setiap kelima citra uji dikirim ke /predict seperti foto biasa, lalu diperkecil
ke lebar 3000, 1920, dan 1280 piksel dan dikirim ke /deteksi seperti frame
kamera. Uji ini hanya memakai foto satu benih; akurasi untuk beberapa benih
sekaligus tidak dapat diukur karena dataset tidak berisi foto seperti itu.
"""

import csv
import io

import cv2
import numpy as np

import config
import prapemrosesan as pp
from app import app

FOLDER_BUKTI = config.FOLDER_BUKTI / "08_mode_kamera"


def peluang_dari_predict(respon):
    skor = respon["skor_kepercayaan"] / 100
    return skor if respon["prediksi"] == "Layak" else 1 - skor


def main():
    FOLDER_BUKTI.mkdir(parents=True, exist_ok=True)
    klien = app.test_client()
    folder_asli = {kelas: folder for folder, kelas in config.KELAS_ASLI.items()}
    with open(config.FOLDER_BUKTI / "03_pembagian_dataset" / "pembagian_dataset.csv", encoding="utf-8") as f:
        uji = [b for b in csv.DictReader(f) if b["bagian"] == "uji"][::5]

    baris = [f"Jumlah citra uji yang dicek: {len(uji)} (setiap kelima dari 150)", ""]
    for lebar in [3000, 1920, 1280]:
        sama, jumlah_kontur_salah, selisih = 0, 0, []
        for b in uji:
            path = config.FOLDER_DATASET / folder_asli[b["kelas"]] / b["berkas"].replace(".png", ".jpg")
            citra = cv2.imread(str(path))
            dari_predict = klien.post("/predict", data={"file": (open(path, "rb"), "a.jpg")},
                                      content_type="multipart/form-data").get_json()
            kecil = cv2.resize(citra, (lebar, round(citra.shape[0] * lebar / citra.shape[1])), interpolation=cv2.INTER_AREA)
            frame = cv2.imencode(".jpg", kecil, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()
            dari_deteksi = klien.post("/deteksi", data={"file": (io.BytesIO(frame), "frame.jpg")},
                                      content_type="multipart/form-data").get_json()
            if len(dari_deteksi["benih"]) != 1:
                jumlah_kontur_salah += 1
                continue
            p1 = peluang_dari_predict(dari_predict)
            p2 = dari_deteksi["benih"][0]["peluang_layak"]
            selisih.append(abs(p1 - p2))
            sama += (p1 >= 0.5) == (p2 >= 0.5)
        baris.append(f"Frame lebar {lebar:>4} px: kelas sama {sama}/{len(uji)}, jumlah benih terdeteksi != 1: "
                     f"{jumlah_kontur_salah}, selisih peluang rata-rata {sum(selisih) / len(selisih):.4f}, "
                     f"maksimum {max(selisih):.4f}")

    # Saringan warna (prapemrosesan.mirip_benih) tidak boleh menolak benih dataset.
    lolos, semua = 0, 0
    for folder in config.KELAS_ASLI:
        for path in sorted((config.FOLDER_DATASET / folder).glob("*.jpg")):
            citra = pp.samakan_lebar(cv2.imread(str(path)))
            _, _, biner = pp.ke_biner(citra)
            kontur = pp.cari_semua_kontur_benih(biner)
            hsv = cv2.cvtColor(citra, cv2.COLOR_BGR2HSV)
            semua += 1
            lolos += any(pp.mirip_benih(hsv, k) for k in kontur)
    baris += ["", f"Benih dataset yang lolos saringan warna mode kamera: {lolos}/{semua}"]

    # Benda bukan benih di atas alas hitam harus ditolak.
    alas = pp.samakan_lebar(cv2.imread(str(config.FOLDER_DATASET / "layak_tanam" / "layak_001.jpg")))
    _, _, biner = pp.ke_biner(alas)
    x, y, w, h = pp.cari_kotak_benih(biner)
    alas[y - 20:y + h + 20, x - 20:x + w + 20] = np.median(alas[::8, ::8].reshape(-1, 3), axis=0)
    papan = np.indices((600, 600)).sum(axis=0) // 100 % 2 * 255
    benda = {
        "kotak hijau": lambda c: cv2.rectangle(c, (1000, 1000), (1600, 1700), (40, 170, 40), cv2.FILLED),
        "kertas putih": lambda c: cv2.rectangle(c, (1000, 1000), (1600, 1700), (235, 235, 235), cv2.FILLED),
        "papan catur": lambda c: c.__setitem__((slice(1000, 1600), slice(1000, 1600)), papan[..., None]),
    }
    for nama, gambar in benda.items():
        citra = alas.copy()
        gambar(citra)
        _, _, biner = pp.ke_biner(citra)
        hsv = cv2.cvtColor(citra, cv2.COLOR_BGR2HSV)
        diterima = sum(pp.mirip_benih(hsv, k) for k in pp.cari_semua_kontur_benih(biner))
        baris.append(f"Benda bukan benih ({nama}): {'ditolak' if diterima == 0 else f'{diterima} kontur dianggap benih'}")

    laporan = "\n".join(baris)
    print(laporan)
    (FOLDER_BUKTI / "cek_mode_kamera.txt").write_text(laporan + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
