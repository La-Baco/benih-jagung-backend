"""Endpoint untuk halaman admin Laravel: kelola dataset, unggah model, dan model aktif.

Semua endpoint di sini hanya menerima permintaan yang membawa header
X-Kunci-Layanan yang sama dengan variabel lingkungan KUNCI_LAYANAN. Flask
tidak dibuka ke internet, jadi kunci ini lapisan kedua bila ada layanan lain
di jaringan yang sama.
"""

import csv
import hashlib
import hmac
import io
import json
import os
import re
import shutil
import time
import zipfile

import cv2
import keras
import numpy as np
from flask import Blueprint, abort, jsonify, request, send_file

import config
import model_aktif
import prapemrosesan as pp

admin = Blueprint("admin", __name__, url_prefix="/admin")

POLA_BERKAS = re.compile(r"^[a-z_]+_(\d+)\.jpg$")
POLA_MODEL = re.compile(r"^\d{8}-\d{6}$")
LABEL_KELAS = {"layak_tanam": "Layak", "tidak_layak_tanam": "Tidak Layak"}

_md5_dataset = {}


def gagal(pesan, kode):
    return jsonify(status="gagal", pesan=pesan), kode


@admin.before_request
def cek_kunci():
    if not config.KUNCI_LAYANAN:
        return gagal("KUNCI_LAYANAN belum diatur di layanan Flask.", 503)
    kunci = request.headers.get("X-Kunci-Layanan", "")
    if not hmac.compare_digest(kunci, config.KUNCI_LAYANAN):
        return gagal("Kunci layanan tidak valid.", 403)


# ---------- Dataset ----------

def folder_kelas(nama_folder):
    if nama_folder not in config.KELAS_ASLI:
        abort(404)
    return config.FOLDER_DATASET / nama_folder


def nomor_berkas(nama):
    cocok = POLA_BERKAS.match(nama)
    return int(cocok.group(1)) if cocok else 0


def termasuk_data_penelitian(nama):
    # Citra nomor 1-500 adalah data skripsi. Data ini tidak bisa dihapus dari web
    # agar hasil di BAB IV tetap bisa diulang.
    return nomor_berkas(nama) <= config.JUMLAH_CITRA_PENELITIAN


def daftar_berkas(folder):
    return sorted((p.name for p in folder.glob("*.jpg")), key=nomor_berkas)


def md5_seluruh_dataset():
    for nama_folder in config.KELAS_ASLI:
        for path in (config.FOLDER_DATASET / nama_folder).glob("*.jpg"):
            kunci = (path.name, path.stat().st_mtime)
            if kunci not in _md5_dataset:
                _md5_dataset[kunci] = hashlib.md5(path.read_bytes()).hexdigest()
    return set(_md5_dataset.values())


@admin.get("/dataset")
def ringkasan_dataset():
    kelas = []
    for nama_folder in config.KELAS_ASLI:
        berkas = daftar_berkas(config.FOLDER_DATASET / nama_folder)
        tambahan = sum(1 for nama in berkas if not termasuk_data_penelitian(nama))
        kelas.append({"folder": nama_folder, "label": LABEL_KELAS[nama_folder],
                      "jumlah": len(berkas), "tambahan": tambahan})
    return jsonify(status="sukses", kelas=kelas)


@admin.get("/dataset/<nama_folder>")
def isi_dataset(nama_folder):
    folder = folder_kelas(nama_folder)
    halaman = max(1, request.args.get("halaman", 1, type=int))
    per_halaman = 24
    # Tambahan terbaru ditampilkan lebih dulu karena itulah yang biasanya diperiksa admin.
    berkas = list(reversed(daftar_berkas(folder)))
    potong = berkas[(halaman - 1) * per_halaman: halaman * per_halaman]
    return jsonify(
        status="sukses", total=len(berkas), halaman=halaman, per_halaman=per_halaman,
        berkas=[{"nama": nama, "data_penelitian": termasuk_data_penelitian(nama)} for nama in potong],
    )


@admin.get("/dataset/<nama_folder>/<nama>/kecil")
def gambar_kecil(nama_folder, nama):
    folder = folder_kelas(nama_folder)
    if not POLA_BERKAS.match(nama) or not (folder / nama).exists():
        abort(404)
    # Dibaca 1/4 resolusi langsung saat decode, jauh lebih cepat untuk foto 3000 piksel.
    citra = cv2.imread(str(folder / nama), cv2.IMREAD_REDUCED_COLOR_4)
    tinggi, lebar = citra.shape[:2]
    kecil = cv2.resize(citra, (240, round(tinggi * 240 / lebar)), interpolation=cv2.INTER_AREA)
    _, jpg = cv2.imencode(".jpg", kecil, [cv2.IMWRITE_JPEG_QUALITY, 80])
    respon = send_file(io.BytesIO(jpg.tobytes()), mimetype="image/jpeg")
    respon.headers["Cache-Control"] = "private, max-age=86400"
    return respon


@admin.post("/dataset/<nama_folder>")
def tambah_dataset(nama_folder):
    folder = folder_kelas(nama_folder)
    awalan = config.KELAS_ASLI[nama_folder] + "_"
    daftar = request.files.getlist("gambar")
    if not daftar:
        return gagal("Pilih minimal satu foto.", 400)

    md5_ada = md5_seluruh_dataset()
    nomor = max([nomor_berkas(n) for n in daftar_berkas(folder)] + [0])
    disimpan, ditolak = [], []
    for berkas in daftar:
        nama_asli = berkas.filename or "tanpa nama"
        isi = berkas.read()
        if not nama_asli.lower().endswith((".jpg", ".jpeg", ".png")):
            ditolak.append({"nama": nama_asli, "alasan": "bukan JPEG atau PNG"})
            continue
        citra = cv2.imdecode(np.frombuffer(isi, np.uint8), cv2.IMREAD_COLOR)
        if citra is None:
            ditolak.append({"nama": nama_asli, "alasan": "tidak dapat dibaca sebagai citra"})
            continue
        if hashlib.md5(isi).hexdigest() in md5_ada:
            ditolak.append({"nama": nama_asli, "alasan": "foto yang sama sudah ada di dataset"})
            continue
        _, _, biner = pp.ke_biner(pp.samakan_lebar(citra))
        if pp.cari_kotak_benih(biner) is None:
            ditolak.append({"nama": nama_asli, "alasan": "benih tidak terdeteksi, periksa alas hitam dan posisi benih"})
            continue

        nomor += 1
        nama_baru = f"{awalan}{nomor:03d}.jpg"
        # Prapemrosesan hanya membaca .jpg, jadi PNG disimpan ulang sebagai JPEG kualitas tinggi.
        if nama_asli.lower().endswith(".png"):
            cv2.imwrite(str(folder / nama_baru), citra, [cv2.IMWRITE_JPEG_QUALITY, 95])
        else:
            (folder / nama_baru).write_bytes(isi)
        md5_ada.add(hashlib.md5(isi).hexdigest())
        disimpan.append(nama_baru)

    return jsonify(status="sukses", disimpan=disimpan, ditolak=ditolak)


@admin.delete("/dataset/<nama_folder>/<nama>")
def hapus_dataset(nama_folder, nama):
    folder = folder_kelas(nama_folder)
    if not POLA_BERKAS.match(nama) or not (folder / nama).exists():
        return gagal("Berkas tidak ditemukan.", 404)
    if termasuk_data_penelitian(nama):
        return gagal("Citra penelitian (nomor 1-500) tidak dapat dihapus dari aplikasi.", 409)
    # Dipindah, bukan dihapus permanen, supaya salah hapus masih bisa dikembalikan dari server.
    tujuan = config.FOLDER_DATASET_TERHAPUS / nama_folder
    tujuan.mkdir(parents=True, exist_ok=True)
    shutil.move(str(folder / nama), str(tujuan / f"{time.strftime('%Y%m%d-%H%M%S')}_{nama}"))
    return jsonify(status="sukses")


@admin.get("/dataset/tambahan.zip")
def unduh_tambahan():
    """Foto tambahan dari admin, untuk dilatih ulang di laptop peneliti (bukan di server)."""
    isi = io.BytesIO()
    with zipfile.ZipFile(isi, "w", zipfile.ZIP_STORED) as arsip:
        for nama_folder in config.KELAS_ASLI:
            for nama in daftar_berkas(config.FOLDER_DATASET / nama_folder):
                if not termasuk_data_penelitian(nama):
                    arsip.write(config.FOLDER_DATASET / nama_folder / nama, f"{nama_folder}/{nama}")
    isi.seek(0)
    return send_file(isi, mimetype="application/zip", as_attachment=True,
                     download_name=f"foto_tambahan_{time.strftime('%Y%m%d')}.zip")


# ---------- Hasil penelitian (laptop) ----------

def hasil_penelitian():
    folder = config.FOLDER_HASIL_PENELITIAN
    path_perbandingan = folder / "05_evaluasi" / "perbandingan_skenario.csv"
    if not path_perbandingan.exists():
        return None

    with open(path_perbandingan, encoding="utf-8") as f:
        skenario = [
            {"skenario": b["skenario"], "jumlah_blok": int(b["jumlah_blok"]), "ukuran_batch": int(b["ukuran_batch"]),
             "jumlah_parameter": int(b["jumlah_parameter"]), "epoch_dijalankan": int(b["epoch_dijalankan"]),
             "epoch_terbaik": int(b["epoch_terbaik"]), "val_loss": float(b["val_loss_terbaik"]),
             "val_akurasi": float(b["val_akurasi"]), "val_f1": float(b["val_f1"]),
             "durasi_menit": float(b["durasi_menit"])}
            for b in csv.DictReader(f)
        ]

    # Model sistem dipilih 11_evaluasi_semua_skenario.py (loss uji terendah, saat ini S3). Bila hasil
    # skrip itu belum ada, dipakai model akhir 05_evaluasi.py (loss validasi terendah).
    folder_semua = folder / "05_evaluasi" / "semua_skenario"
    if (folder_semua / "hasil_semua_skenario.txt").exists():
        teks = (folder_semua / "hasil_semua_skenario.txt").read_text(encoding="utf-8")
        terpilih = re.search(r"Model untuk sistem\s*:\s*(S\d)", teks).group(1).lower()
        with open(folder_semua / "evaluasi_semua_skenario.csv", encoding="utf-8") as f:
            b = next(b for b in csv.DictReader(f) if b["skenario"].lower() == terpilih)
        tp, fn, fp, tn = (int(b[k]) for k in ("uji_tp", "uji_fn", "uji_fp", "uji_tn"))
        uji = {"jumlah": tp + fn + fp + tn, "tp": tp, "fn": fn, "fp": fp, "tn": tn,
               "akurasi": float(b["akurasi_uji"]), "presisi": float(b["presisi_uji"]),
               "recall": float(b["recall_uji"]), "f1": float(b["f1_uji"])}
        return hasil_dengan_perangkat(folder, skenario, terpilih, uji)

    teks = (folder / "05_evaluasi" / "hasil_evaluasi.txt").read_text(encoding="utf-8")
    terpilih = re.search(r"Model akhir\s*:\s*(S\d)", teks).group(1).lower()

    tp = fn = fp = tn = 0
    with open(folder / "05_evaluasi" / "prediksi_data_uji.csv", encoding="utf-8") as f:
        for b in csv.DictReader(f):
            if b["keterangan"] == "TP":
                tp += 1
            elif b["keterangan"] == "FN":
                fn += 1
            elif b["keterangan"] == "FP":
                fp += 1
            else:
                tn += 1
    presisi = tp / (tp + fp)
    recall = tp / (tp + fn)
    uji = {"jumlah": tp + fn + fp + tn, "tp": tp, "fn": fn, "fp": fp, "tn": tn,
           "akurasi": round((tp + tn) / (tp + fn + fp + tn), 4), "presisi": round(presisi, 4),
           "recall": round(recall, 4), "f1": round(2 * presisi * recall / (presisi + recall), 4)}
    return hasil_dengan_perangkat(folder, skenario, terpilih, uji)


def hasil_dengan_perangkat(folder, skenario, terpilih, uji):
    # Perangkat pelatihan diambil dari catatan 01_cek_lingkungan.py, bukan ditulis ulang di sini.
    perangkat = {}
    path_lingkungan = folder / "01_lingkungan" / "versi_perangkat_lunak_windows.txt"
    if path_lingkungan.exists():
        for baris in path_lingkungan.read_text(encoding="utf-8").splitlines():
            kunci, _, nilai = baris.partition(":")
            if kunci.strip() in ("Sistem operasi", "Prosesor", "RAM", "TensorFlow", "GPU"):
                perangkat[kunci.strip()] = nilai.strip()
    durasi = next((s["durasi_menit"] for s in skenario if s["skenario"] == terpilih), None)
    epoch = next((s["epoch_dijalankan"] for s in skenario if s["skenario"] == terpilih), None)
    return {"skenario": skenario, "terpilih": terpilih, "uji": uji,
            "perangkat": perangkat, "durasi_menit": durasi, "epoch": epoch}


@admin.get("/penelitian/<skenario>/kurva")
def kurva_penelitian(skenario):
    if skenario not in config.SKENARIO:
        abort(404)
    path = config.FOLDER_HASIL_PENELITIAN / "04_pelatihan" / skenario / "kurva_akurasi_loss.png"
    if not path.exists():
        abort(404)
    return send_file(path, mimetype="image/png")


# ---------- Model unggahan ----------
# Model dilatih di laptop peneliti (04_latih.py, 05_evaluasi.py), lalu berkas .keras-nya diunggah
# lewat halaman admin. VPS dipakai bersama, jadi server ini tidak menjalankan pelatihan.

def baca_model_unggahan(folder):
    info = json.loads((folder / "info.json").read_text(encoding="utf-8"))
    info["id"] = folder.name
    return info


def semua_model_unggahan():
    if not config.FOLDER_MODEL_UNGGAHAN.exists():
        return []
    folder = sorted((p for p in config.FOLDER_MODEL_UNGGAHAN.iterdir() if POLA_MODEL.match(p.name)), reverse=True)
    return [baca_model_unggahan(p) for p in folder]


def folder_model(id_model):
    if not POLA_MODEL.match(id_model) or not (config.FOLDER_MODEL_UNGGAHAN / id_model).exists():
        abort(404)
    return config.FOLDER_MODEL_UNGGAHAN / id_model


@admin.get("/model")
def daftar_model():
    pengaturan = json.loads(config.FILE_PRAPEMROSESAN.read_text(encoding="utf-8"))
    return jsonify(status="sukses", model_aktif=model_aktif.keterangan(), sisi_potong_aktif=pengaturan["sisi_potong"],
                   unggahan=semua_model_unggahan(), penelitian=hasil_penelitian(),
                   bisa_ganti_model=config.FOLDER_MODEL.resolve() != config.FOLDER_MODEL_PENELITIAN.resolve())


@admin.post("/model/unggah")
def unggah_model():
    berkas = request.files.get("berkas")
    if berkas is None or not berkas.filename.lower().endswith(".keras"):
        return gagal("Pilih berkas model berformat .keras.", 400)
    sisi = request.form.get("sisi_potong", type=int)
    if sisi is None or not config.UKURAN_CITRA <= sisi <= config.LEBAR_ACUAN:
        return gagal(f"Nilai S harus bilangan bulat {config.UKURAN_CITRA}-{config.LEBAR_ACUAN} piksel.", 400)

    id_model = time.strftime("%Y%m%d-%H%M%S")
    folder = config.FOLDER_MODEL_UNGGAHAN / id_model
    folder.mkdir(parents=True)
    berkas.save(folder / "model_akhir.keras")

    # Pemeriksaan ringan, bukan pelatihan: model harus bisa dimuat, menerima citra 224 x 224 x 3,
    # dan mengeluarkan satu peluang 0-1 seperti Custom CNN pada Tabel 3.6.
    try:
        model = keras.models.load_model(str(folder / "model_akhir.keras"))
    except Exception as e:  # berkas rusak atau bukan model Keras
        shutil.rmtree(folder)
        return gagal(f"Berkas tidak dapat dimuat sebagai model Keras ({type(e).__name__}).", 422)

    bentuk_masuk = tuple(model.input_shape[1:])
    bentuk_keluar = tuple(model.output_shape[1:])
    if bentuk_masuk != (config.UKURAN_CITRA, config.UKURAN_CITRA, 3) or bentuk_keluar != (1,):
        shutil.rmtree(folder)
        return gagal(f"Model harus menerima citra {config.UKURAN_CITRA}x{config.UKURAN_CITRA}x3 dan mengeluarkan satu "
                     f"peluang. Model ini: masukan {bentuk_masuk}, keluaran {bentuk_keluar}.", 422)

    uji = float(model(np.zeros((1, config.UKURAN_CITRA, config.UKURAN_CITRA, 3), np.float32), training=False).numpy()[0][0])
    if not 0 <= uji <= 1:
        shutil.rmtree(folder)
        return gagal("Keluaran model bukan peluang 0-1. Pastikan lapisan terakhir memakai sigmoid.", 422)

    pengaturan = {"sisi_potong": sisi, "batas_tepi": config.BATAS_TEPI, "lebar_acuan": config.LEBAR_ACUAN,
                  "kernel_opening": config.KERNEL_OPENING, "ukuran_citra": config.UKURAN_CITRA}
    (folder / "prapemrosesan.json").write_text(json.dumps(pengaturan, indent=2), encoding="utf-8")
    info = {"keterangan": request.form.get("keterangan", "")[:200], "nama_berkas": berkas.filename[:150],
            "sisi_potong": sisi, "jumlah_parameter": int(model.count_params()), "nama_arsitektur": model.name,
            "ukuran_mb": round((folder / "model_akhir.keras").stat().st_size / 1024 / 1024, 1),
            "diunggah": time.strftime("%Y-%m-%d %H:%M:%S"), "oleh": request.form.get("oleh", "")[:100]}
    (folder / "info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return jsonify(status="sukses", model=baca_model_unggahan(folder)), 201


@admin.delete("/model/<id_model>")
def hapus_model(id_model):
    folder = folder_model(id_model)
    if model_aktif.keterangan().get("sumber") == id_model:
        return gagal("Model ini sedang dipakai. Ganti ke model lain dulu sebelum menghapusnya.", 409)
    shutil.rmtree(folder)
    return jsonify(status="sukses")


@admin.post("/model/aktif")
def ganti_model():
    if config.FOLDER_MODEL.resolve() == config.FOLDER_MODEL_PENELITIAN.resolve():
        return gagal("Model penelitian tidak boleh ditimpa. Atur FOLDER_MODEL ke folder lain untuk memakai fitur ini.", 409)

    sumber = (request.get_json(silent=True) or {}).get("sumber", "")
    if sumber == "penelitian":
        asal = config.FOLDER_MODEL_PENELITIAN
        keterangan = {"sumber": "penelitian", "nama": "Model penelitian S3"}
    else:
        asal = folder_model(sumber)
        info = baca_model_unggahan(asal)
        keterangan = {"sumber": sumber, "nama": info["keterangan"] or info["nama_berkas"]}

    config.FOLDER_MODEL.mkdir(parents=True, exist_ok=True)
    # Disalin ke nama sementara dulu, lalu diganti sekaligus, supaya tidak ada model setengah tersalin.
    for nama in ["model_akhir.keras", "prapemrosesan.json"]:
        shutil.copy(asal / nama, config.FOLDER_MODEL / f"{nama}.baru")
        os.replace(config.FOLDER_MODEL / f"{nama}.baru", config.FOLDER_MODEL / nama)
    keterangan["diaktifkan"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (config.FOLDER_MODEL / "aktif.json").write_text(json.dumps(keterangan, indent=2), encoding="utf-8")
    model_aktif.muat()
    return jsonify(status="sukses", model_aktif=keterangan)
