import os
from pathlib import Path

FOLDER_PYTHON = Path(__file__).resolve().parent

# Di laptop semua folder mengikuti struktur proyek. Di VPS ketiganya diarahkan ke
# volume data lewat variabel lingkungan, supaya model yang diunggah admin tidak
# menimpa model penelitian yang ikut di dalam image.
FOLDER_PROYEK = Path(os.environ.get("FOLDER_PROYEK", FOLDER_PYTHON.parent.parent))
FOLDER_BUKTI = Path(os.environ.get("FOLDER_BUKTI", FOLDER_PROYEK / "bukti"))
FOLDER_MODEL = Path(os.environ.get("FOLDER_MODEL", FOLDER_PYTHON / "model"))

FOLDER_DATASET = FOLDER_PROYEK / "dataset"
FOLDER_OLAH = FOLDER_PROYEK / "dataset_olah"

# Dipakai halaman admin (kelola dataset dan model unggahan).
FOLDER_MODEL_PENELITIAN = FOLDER_PYTHON / "model"
FOLDER_HASIL_PENELITIAN = Path(os.environ.get("FOLDER_HASIL_PENELITIAN", FOLDER_PROYEK / "bukti"))
FOLDER_MODEL_UNGGAHAN = FOLDER_PROYEK / "model_unggahan"
FOLDER_DATASET_TERHAPUS = FOLDER_PROYEK / "dataset_terhapus"
JUMLAH_CITRA_PENELITIAN = 500
KUNCI_LAYANAN = os.environ.get("KUNCI_LAYANAN", "")

FILE_PRAPEMROSESAN = FOLDER_MODEL / "prapemrosesan.json"
FILE_MODEL_AKHIR = FOLDER_MODEL / "model_akhir.keras"

# Nama folder di dataset asli -> nama kelas di dataset_olah (Tabel 3.3)
KELAS_ASLI = {
    "layak_tanam": "layak",
    "tidak_layak_tanam": "tidak_layak",
}

# Urutan ditetapkan eksplisit agar tidak_layak = 0 dan layak = 1 (Subbab 3.7)
NAMA_KELAS = ["tidak_layak", "layak"]

UKURAN_CITRA = 224
LEBAR_ACUAN = 3000
BATAS_TEPI = 50
KERNEL_OPENING = 21

# Mode kamera (beberapa benih sekaligus): batas max(w, h) kontur pada lebar 3000 px.
# Benih terkecil di dataset 504 px dan terbesar 1230 px (bukti/02_prapemrosesan/ukuran_benih.csv).
SISI_MIN_DETEKSI = 250
SISI_MAKS_DETEKSI = 1600
JUMLAH_MAKS_DETEKSI = 10
# Kontur hanya dianggap benih bila warnanya seperti benih dan sekelilingnya gelap seperti alas.
# Rentang di dataset (HSV OpenCV): hue 16-21, saturasi 41-154 untuk benih putih dan sampai
# 220 untuk benih kuning/oranye (kriteria "warna bukan putih"), value 145-228, value cincin
# alas 64-128. Batas di bawah diberi kelonggaran untuk cahaya yang berbeda.
HUE_BENIH = (8, 32)
SATURASI_BENIH = (20, 240)
VALUE_MIN_BENIH = 110
VALUE_MAKS_ALAS = 150

RANDOM_SEED = 42
# 70:15:15 per kelas. Dengan 500 citra per kelas hasilnya 350, 75, dan 75 (Tabel 3.5).
PROPORSI_BAGIAN = {"latih": 0.70, "validasi": 0.15, "uji": 0.15}

# Tabel 3.7
LEARNING_RATE = 0.001
EPOCH_MAKS = 100
PATIENCE = 10
DROPOUT = 0.5

# Tabel 3.8
SKENARIO = {
    "s1": {"jumlah_blok": 3, "batch": 16},
    "s2": {"jumlah_blok": 3, "batch": 32},
    "s3": {"jumlah_blok": 4, "batch": 16},
    "s4": {"jumlah_blok": 4, "batch": 32},
}
