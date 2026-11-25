"""Tahap penyaring objek (3/4): melatih Custom CNN penyaring "jagung ketan putih / bukan".

Arsitektur, optimizer, learning rate, early stopping, dan augmentasi sama persis dengan
model kelayakan (fungsi bangun_model dan augmentasi di 04_latih.py), memakai pengaturan
skenario config.SKENARIO_PENYARING (S3: 4 blok, batch 16). Yang berbeda hanya datanya
(dataset_penyaring dari 18_bentuk_data_penyaring.py) dan arti keluarannya:
peluang objek adalah jagung ketan putih.

Dijalankan di laptop, bukan di VPS:
    python 19_latih_penyaring.py
"""

import importlib
import json
import shutil
import time

import keras
import tensorflow as tf
from keras import layers

import config

latih = importlib.import_module("04_latih")

FOLDER_DATA = config.FOLDER_PROYEK / "dataset_penyaring"
FOLDER_BUKTI = config.FOLDER_BUKTI / "12_penyaring_objek" / "pelatihan"


def muat_data(bagian, batch, acak=False):
    data = keras.utils.image_dataset_from_directory(
        str(FOLDER_DATA / bagian),
        labels="inferred",
        label_mode="binary",
        class_names=config.NAMA_KELAS_PENYARING,
        image_size=(config.UKURAN_CITRA, config.UKURAN_CITRA),
        batch_size=None,
        shuffle=False,
    )
    # Disimpan di memori sebagai uint8 (nilai piksel tetap sama) supaya seluruh data latih
    # muat di buffer acak; 5.600 citra float32 akan memakan ±3,4 GB.
    jumlah = data.cardinality()
    data = data.map(lambda x, y: (tf.cast(x, tf.uint8), y)).cache()
    if acak:
        data = data.shuffle(jumlah, seed=config.RANDOM_SEED, reshuffle_each_iteration=True).map(latih.augmentasi)
    normalisasi = layers.Rescaling(1.0 / 255)
    return data.batch(batch).map(lambda x, y: (normalisasi(tf.cast(x, tf.float32)), y)).prefetch(tf.data.AUTOTUNE)


def main():
    pengaturan = config.SKENARIO[config.SKENARIO_PENYARING]
    FOLDER_BUKTI.mkdir(parents=True, exist_ok=True)
    keras.backend.clear_session()
    keras.utils.set_random_seed(config.RANDOM_SEED)

    data_latih = muat_data("latih", pengaturan["batch"], acak=True)
    data_validasi = muat_data("validasi", pengaturan["batch"])

    model = latih.bangun_model(pengaturan["jumlah_blok"])
    baris_summary = []
    model.summary(print_fn=lambda teks, **_: baris_summary.append(teks))
    (FOLDER_BUKTI / "arsitektur.txt").write_text("\n".join(baris_summary), encoding="utf-8")

    file_model = FOLDER_BUKTI / "model_penyaring.keras"
    callbacks = [
        keras.callbacks.EarlyStopping(monitor="val_loss", patience=config.PATIENCE,
                                      restore_best_weights=True, verbose=1),
        keras.callbacks.ModelCheckpoint(str(file_model), monitor="val_loss", save_best_only=True, verbose=1),
        keras.callbacks.CSVLogger(str(FOLDER_BUKTI / "riwayat_epoch.csv")),
    ]
    mulai = time.time()
    hasil = model.fit(data_latih, validation_data=data_validasi, epochs=config.EPOCH_MAKS,
                      callbacks=callbacks, verbose=2)
    durasi = time.time() - mulai

    riwayat = hasil.history
    indeks = min(range(len(riwayat["val_loss"])), key=lambda i: riwayat["val_loss"][i])
    ringkasan = {
        "model": "penyaring jagung ketan putih / bukan",
        "arsitektur": f"Custom CNN {pengaturan['jumlah_blok']} blok (sama dengan {config.SKENARIO_PENYARING.upper()})",
        "ukuran_batch": pengaturan["batch"],
        "jumlah_parameter": model.count_params(),
        "perangkat": "GPU" if tf.config.list_physical_devices("GPU") else "CPU",
        "epoch_dijalankan": len(riwayat["loss"]),
        "epoch_terbaik": indeks + 1,
        "val_loss_terbaik": round(riwayat["val_loss"][indeks], 4),
        "val_accuracy_epoch_terbaik": round(riwayat["val_accuracy"][indeks], 4),
        "loss_latih_epoch_terbaik": round(riwayat["loss"][indeks], 4),
        "accuracy_latih_epoch_terbaik": round(riwayat["accuracy"][indeks], 4),
        "durasi_menit": round(durasi / 60, 1),
    }
    (FOLDER_BUKTI / "ringkasan.json").write_text(json.dumps(ringkasan, indent=2), encoding="utf-8")
    latih.simpan_kurva(riwayat, indeks + 1, "penyaring objek", FOLDER_BUKTI / "kurva_akurasi_loss.png")

    # Model yang dipakai layanan Flask
    shutil.copy2(file_model, config.FILE_MODEL_PENYARING)
    print(json.dumps(ringkasan, indent=2))
    print(f"Model penyaring disalin ke {config.FILE_MODEL_PENYARING}")


if __name__ == "__main__":
    main()
