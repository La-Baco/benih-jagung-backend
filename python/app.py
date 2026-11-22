"""Layanan prediksi Flask (Subbab 3.14, Tabel 3.13).

Hanya didengarkan di 127.0.0.1 karena yang memanggil adalah aplikasi Laravel
di komputer yang sama, bukan peramban pengguna. Di VPS layanan ini berada di
jaringan internal Docker dan tidak dibuka ke internet.

Layanan ini tidak melatih model. Model dilatih di perangkat pengembang dengan
04_latih.py dan 05_evaluasi.py, lalu dipasang di sini (folder model/ atau
lewat menu Model di halaman admin).

Menjalankan:
    python app.py
"""

import math

import cv2
import numpy as np
from flask import Flask, jsonify, request

import config
import model_aktif
import prapemrosesan as pp
from admin import admin

EKSTENSI_DIIZINKAN = {".jpg", ".jpeg", ".png"}

# Layanan ini hanya menjalankan prediksi. Pelatihan (04_latih.py) tidak pernah dijalankan di server.
KETERANGAN_PELATIHAN = ("Model dilatih di perangkat pengembang (laptop peneliti), bukan di server ini. "
                        "Layanan ini hanya menjalankan prediksi.")

app = Flask(__name__)
# Batas umum 60 MB (unggahan dataset bisa berisi beberapa foto). Hanya unggahan model .keras dari
# admin yang boleh lebih besar, dan itu datang dari Laravel di jaringan internal.
BATAS_UMUM = 60 * 1024 * 1024
BATAS_MODEL = 400 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = BATAS_MODEL
app.register_blueprint(admin)


@app.before_request
def batasi_ukuran():
    if request.path != "/admin/model/unggah" and (request.content_length or 0) > BATAS_UMUM:
        return gagal("Total unggahan melebihi 60 MB. Kirim foto dalam beberapa kali unggah.", 413)

model_aktif.muat()


def gagal(pesan, kode):
    return jsonify(status="gagal", pesan=pesan), kode


@app.errorhandler(413)
def berkas_terlalu_besar(_):
    return gagal("Ukuran model melebihi 400 MB.", 413)


@app.get("/")
def cek_layanan():
    return jsonify(status="aktif", model=model_aktif.keterangan(), pelatihan=KETERANGAN_PELATIHAN)


@app.post("/predict")
def predict():
    berkas = request.files.get("file")
    if berkas is None or berkas.filename == "":
        return gagal("Berkas citra wajib diisi.", 400)
    if request.content_length and request.content_length > 10 * 1024 * 1024:
        return gagal("Ukuran berkas melebihi 10 MB.", 413)

    ekstensi = "." + berkas.filename.rsplit(".", 1)[-1].lower() if "." in berkas.filename else ""
    if ekstensi not in EKSTENSI_DIIZINKAN:
        return gagal("Berkas harus berformat JPEG atau PNG.", 400)

    citra = cv2.imdecode(np.frombuffer(berkas.read(), np.uint8), cv2.IMREAD_COLOR)
    if citra is None:
        return gagal("Berkas tidak dapat dibaca sebagai citra.", 400)

    model, sisi = model_aktif.ambil()
    potongan = pp.proses_citra(citra, sisi)
    if potongan is None:
        return gagal("Benih tidak terdeteksi. Pastikan satu butir benih berada di tengah alas hitam.", 422)

    masukan = pp.ke_masukan_model(potongan)[np.newaxis, ...]
    peluang_layak = float(model(masukan, training=False).numpy()[0][0])

    # Persamaan 3-2 dan 3-3
    if peluang_layak >= 0.5:
        prediksi = "Layak"
        skor = peluang_layak * 100
    else:
        prediksi = "Tidak Layak"
        skor = (1 - peluang_layak) * 100

    # Dipotong ke bawah, bukan dibulatkan, supaya peluang 0,99997 tidak tampil sebagai 100% (kesan pasti benar).
    return jsonify(status="sukses", prediksi=prediksi, skor_kepercayaan=math.floor(round(skor * 100, 6)) / 100)


def samakan_skala_frame(citra):
    """Ubah ukuran frame kamera supaya satu piksel mewakili luas yang sama dengan citra dataset.

    Citra dataset berbentuk persegi, jadi lebarnya sama dengan sisi pendek sensor kamera
    (sensor HP umumnya 4:3). Frame kamera biasanya 16:9 dan sisi pendeknya sudah terpotong,
    sehingga bila lebar frame langsung dijadikan 3000 px, benih tampak 1,33 kali lebih besar
    daripada di dataset. Sisi pendek sensor dihitung ulang dari sisi panjang frame.
    """
    tinggi, lebar = citra.shape[:2]
    panjang, pendek = max(tinggi, lebar), min(tinggi, lebar)
    sisi_pendek_sensor = 0.75 * panjang if panjang / pendek >= 4 / 3 else pendek
    skala = config.LEBAR_ACUAN / sisi_pendek_sensor
    if skala == 1:
        return citra
    return cv2.resize(citra, (round(lebar * skala), round(tinggi * skala)), interpolation=cv2.INTER_AREA)


@app.post("/deteksi")
def deteksi():
    """Mode kamera aplikasi HP: beberapa benih dalam satu frame.

    Ini perluasan di luar ruang lingkup skripsi (Batasan no. 4 hanya satu benih
    per citra) dan akurasinya tidak dievaluasi di BAB IV. Model dan prapemrosesan
    tetap sama; yang ditambahkan hanya pencarian semua kontur benih.
    """
    berkas = request.files.get("file")
    if berkas is None:
        return gagal("Frame kamera wajib dikirim.", 400)
    citra = cv2.imdecode(np.frombuffer(berkas.read(), np.uint8), cv2.IMREAD_COLOR)
    if citra is None:
        return gagal("Frame tidak dapat dibaca sebagai citra.", 400)

    model, sisi = model_aktif.ambil()
    citra = samakan_skala_frame(citra)
    tinggi, lebar = citra.shape[:2]
    _, _, biner = pp.ke_biner(citra)
    daftar_kontur = sorted(pp.cari_semua_kontur_benih(biner), key=cv2.contourArea, reverse=True)
    citra_hsv = cv2.cvtColor(citra, cv2.COLOR_BGR2HSV)
    daftar_kontur = [k for k in daftar_kontur[:30] if pp.mirip_benih(citra_hsv, k)][:config.JUMLAH_MAKS_DETEKSI]
    if not daftar_kontur:
        return jsonify(status="sukses", lebar=lebar, tinggi=tinggi, benih=[])

    # Model dilatih dengan satu benih per potongan. Bila benih lain ikut masuk ke potongan,
    # benih itu ditutup dengan warna alas supaya potongannya menyerupai data latih.
    # Median dihitung dari 1 tiap 8x8 piksel: hasilnya sama, tetapi 1,5 detik lebih cepat di VPS.
    warna_alas = np.median(citra[::8, ::8][biner[::8, ::8] == 0], axis=0).astype(np.uint8)
    topeng_semua = []
    for k in daftar_kontur:
        topeng = np.zeros(biner.shape, np.uint8)
        cv2.drawContours(topeng, [k], -1, 255, cv2.FILLED)
        topeng_semua.append(cv2.dilate(topeng, np.ones((31, 31), np.uint8)))

    masukan, kotak = [], []
    for i, k in enumerate(daftar_kontur):
        bersih = citra.copy()
        for j, topeng in enumerate(topeng_semua):
            if j != i:
                bersih[topeng > 0] = warna_alas
        x, y, w, h = cv2.boundingRect(k)
        masukan.append(pp.ke_masukan_model(pp.ubah_ukuran(pp.potong_persegi(bersih, (x, y, w, h), sisi))))
        kotak.append((x, y, w, h))

    peluang = model(np.stack(masukan), training=False).numpy().ravel()
    benih = []
    for (x, y, w, h), p in zip(kotak, peluang):
        benih.append({
            # Koordinat dibagi ukuran citra, jadi aplikasi bisa menggambar kotak di layar ukuran apa pun.
            "x": round(x / lebar, 4), "y": round(y / tinggi, 4),
            "w": round(w / lebar, 4), "h": round(h / tinggi, 4),
            "peluang_layak": round(float(p), 4),
            "prediksi": "Layak" if p >= 0.5 else "Tidak Layak",
        })
    return jsonify(status="sukses", lebar=lebar, tinggi=tinggi, benih=benih)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
