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

import cv2
import numpy as np
from flask import Flask, jsonify, request

import config
import deteksi_objek
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
    return jsonify(status="aktif", model=model_aktif.keterangan(), pelatihan=KETERANGAN_PELATIHAN,
                   penyaring="Custom CNN jagung ketan putih / bukan (model/model_penyaring.keras)")


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
    citra = pp.samakan_lebar(citra)
    daftar_objek = deteksi_objek.analisis(citra, model_aktif.ambil_penyaring(), model, sisi)
    if not daftar_objek:
        return gagal("Objek tidak terdeteksi. Letakkan satu butir benih di tengah alas polos, "
                     "lalu foto dari atas.", 422)

    # Hasil utama adalah objek terbesar, sesuai satu benih per foto (Batasan Masalah).
    # Skor kepercayaan memakai Persamaan 3-2 dan 3-3, dipotong ke bawah 2 desimal supaya
    # peluang 0,99997 tidak tampil sebagai 100% (kesan pasti benar).
    utama = daftar_objek[0]
    tinggi, lebar = citra.shape[:2]
    return jsonify(status="sukses", prediksi=utama["prediksi"], skor_kepercayaan=utama["skor_kepercayaan"],
                   jenis=utama["jenis"], objek=[kotak_relatif(o, lebar, tinggi) for o in daftar_objek])


def kotak_relatif(objek, lebar, tinggi):
    """Koordinat dibagi ukuran citra, jadi aplikasi bisa menggambar kotak di layar ukuran apa pun."""
    hasil = dict(objek)
    hasil.update(x=round(objek["x"] / lebar, 4), y=round(objek["y"] / tinggi, 4),
                 w=round(objek["w"] / lebar, 4), h=round(objek["h"] / tinggi, 4))
    return hasil


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
    """Mode kamera aplikasi HP: beberapa objek dalam satu frame.

    Ini perluasan di luar ruang lingkup skripsi (Batasan no. 4 hanya satu benih
    per citra) dan akurasinya tidak dievaluasi di BAB IV. Alurnya sama dengan
    /predict (deteksi objek, penyaring, kelayakan); ukuran objek dibatasi pada
    rentang ukuran benih karena jarak kamera ke alas kurang lebih tetap.
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
    daftar_objek = deteksi_objek.analisis(citra, model_aktif.ambil_penyaring(), model, sisi,
                                          sisi_min=config.SISI_MIN_DETEKSI, sisi_maks=config.SISI_MAKS_DETEKSI)
    return jsonify(status="sukses", lebar=lebar, tinggi=tinggi,
                   benih=[kotak_relatif(o, lebar, tinggi) for o in daftar_objek])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
