"""Model yang sedang dipakai layanan prediksi.

Dipisah dari app.py karena halaman admin bisa mengganti model tanpa
mematikan layanan. Model dan nilai S selalu dimuat berpasangan, sebab
model hasil pelatihan ulang bisa memakai S yang berbeda.
"""

import json
import threading

import keras

import config

_kunci = threading.Lock()
_model = None
_sisi = None
# Model penyaring (jagung ketan putih / bukan) tidak bisa diganti dari halaman admin,
# jadi cukup dimuat sekali dari folder model penelitian.
_penyaring = keras.models.load_model(str(config.FILE_MODEL_PENYARING))


def muat():
    global _model, _sisi
    pengaturan = json.loads(config.FILE_PRAPEMROSESAN.read_text(encoding="utf-8"))
    model_baru = keras.models.load_model(str(config.FILE_MODEL_AKHIR))
    with _kunci:
        _model = model_baru
        _sisi = pengaturan["sisi_potong"]


def ambil():
    with _kunci:
        return _model, _sisi


def ambil_penyaring():
    return _penyaring


def keterangan():
    path = config.FOLDER_MODEL / "aktif.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"sumber": "penelitian", "nama": "Model penelitian S3", "diaktifkan": None}
