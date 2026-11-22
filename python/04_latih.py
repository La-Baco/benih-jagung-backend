"""Tahap 7: pelatihan Custom CNN untuk skenario S1 sampai S4 (Subbab 3.8 dan 3.9).

Contoh:
    python 04_latih.py s1
    python 04_latih.py semua
"""

import argparse
import json
import time

import keras
import matplotlib.pyplot as plt
import tensorflow as tf
from keras import layers

import config

# Memori GPU dipakai bertahap, tidak langsung dihabiskan, supaya laptop tetap responsif.
for gpu in tf.config.list_physical_devices("GPU"):
    tf.config.experimental.set_memory_growth(gpu, True)


def augmentasi(citra, label):
    """Flip horizontal, flip vertikal, dan rotasi acak 0, 90, 180, atau 270 derajat (Subbab 3.7).

    Rotasi kelipatan 90 derajat tidak memerlukan interpolasi, jadi piksel benih tetap utuh
    dan tidak ada sudut kosong yang harus diisi. Warna dan kecerahan tidak diubah.
    """
    citra = tf.image.random_flip_left_right(citra)
    citra = tf.image.random_flip_up_down(citra)
    putaran = tf.random.uniform([], minval=0, maxval=4, dtype=tf.int32)
    citra = tf.image.rot90(citra, k=putaran)
    return citra, label


def muat_data(bagian, batch, acak=False, dengan_augmentasi=False):
    data = keras.utils.image_dataset_from_directory(
        str(config.FOLDER_OLAH / bagian),
        labels="inferred",
        label_mode="binary",
        class_names=config.NAMA_KELAS,
        image_size=(config.UKURAN_CITRA, config.UKURAN_CITRA),
        batch_size=None,
        shuffle=False,
    )
    data = data.cache()

    # Data latih selalu diacak ulang tiap epoch, dengan atau tanpa augmentasi.
    if acak:
        data = data.shuffle(1000, seed=config.RANDOM_SEED, reshuffle_each_iteration=True)
    if dengan_augmentasi:
        data = data.map(augmentasi)

    normalisasi = layers.Rescaling(1.0 / 255)
    data = data.batch(batch).map(lambda x, y: (normalisasi(x), y))
    return data.prefetch(tf.data.AUTOTUNE)


def simpan_contoh_rotasi(tujuan):
    """Satu citra latih ditampilkan pada empat arah rotasi dan dua arah flip."""
    path = sorted((config.FOLDER_OLAH / "latih" / "tidak_layak").glob("*.png"))[0]
    citra = tf.io.decode_png(tf.io.read_file(str(path)), channels=3)
    contoh = [
        ("asli (0°)", citra),
        ("rotasi 90°", tf.image.rot90(citra, k=1)),
        ("rotasi 180°", tf.image.rot90(citra, k=2)),
        ("rotasi 270°", tf.image.rot90(citra, k=3)),
        ("flip horizontal", tf.image.flip_left_right(citra)),
        ("flip vertikal", tf.image.flip_up_down(citra)),
    ]
    fig, sumbu = plt.subplots(1, len(contoh), figsize=(3 * len(contoh), 3.4))
    for ax, (judul, gambar) in zip(sumbu, contoh):
        ax.imshow(gambar.numpy())
        ax.set_title(judul, fontsize=11)
        ax.axis("off")
    fig.suptitle(f"Contoh augmentasi pada {path.name}", fontsize=12)
    fig.savefig(tujuan, dpi=120, bbox_inches="tight")
    plt.close(fig)


def simpan_batch_pertama(data_latih, nama_skenario, tujuan):
    """Menyimpan batch latih pertama persis seperti yang diterima model (sudah diaugmentasi)."""
    citra, label = next(iter(data_latih))
    jumlah = citra.shape[0]
    kolom = 8
    baris = (jumlah + kolom - 1) // kolom
    fig, sumbu = plt.subplots(baris, kolom, figsize=(kolom * 1.8, baris * 2.0))
    for i, ax in enumerate(sumbu.ravel()):
        ax.axis("off")
        if i < jumlah:
            ax.imshow(citra[i].numpy())
            ax.set_title(config.NAMA_KELAS[int(label[i][0])], fontsize=8)
    fig.suptitle(f"{nama_skenario.upper()}: batch latih pertama setelah augmentasi ({jumlah} citra)", fontsize=12)
    fig.savefig(tujuan, dpi=110, bbox_inches="tight")
    plt.close(fig)


def bangun_model(jumlah_blok):
    """Arsitektur Tabel 3.6. Varian 3 blok tidak memakai konvolusi dan pooling ke-4."""
    jumlah_filter = [32, 64, 128, 128][:jumlah_blok]

    model = keras.Sequential(name=f"custom_cnn_{jumlah_blok}_blok")
    model.add(keras.Input(shape=(config.UKURAN_CITRA, config.UKURAN_CITRA, 3)))
    for i, filter_ in enumerate(jumlah_filter, 1):
        model.add(layers.Conv2D(filter_, (3, 3), padding="same", activation="relu", name=f"konvolusi_{i}"))
        model.add(layers.MaxPooling2D((2, 2), name=f"max_pooling_{i}"))
    model.add(layers.Flatten(name="flatten"))
    model.add(layers.Dense(128, activation="relu", name="fully_connected"))
    model.add(layers.Dropout(config.DROPOUT, name="dropout"))
    model.add(layers.Dense(1, activation="sigmoid", name="keluaran"))

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=config.LEARNING_RATE),
        loss=keras.losses.BinaryCrossentropy(),
        metrics=["accuracy"],
    )
    return model


def simpan_kurva(riwayat, epoch_terbaik, judul, tujuan):
    epoch = range(1, len(riwayat["loss"]) + 1)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

    ax1.plot(epoch, riwayat["accuracy"], label="latih")
    ax1.plot(epoch, riwayat["val_accuracy"], label="validasi")
    ax1.set_title(f"Akurasi {judul}")
    ax1.set_ylabel("akurasi")

    ax2.plot(epoch, riwayat["loss"], label="latih")
    ax2.plot(epoch, riwayat["val_loss"], label="validasi")
    ax2.set_title(f"Loss {judul}")
    ax2.set_ylabel("binary cross-entropy")

    for ax in (ax1, ax2):
        ax.axvline(epoch_terbaik, color="gray", linestyle="--", linewidth=1)
        ax.set_xlabel("epoch")
        ax.grid(alpha=0.3)
        ax.legend()

    fig.tight_layout()
    fig.savefig(tujuan, dpi=150)
    plt.close(fig)


def latih_skenario(nama, dengan_augmentasi=True):
    pengaturan = config.SKENARIO[nama]
    # Run tanpa augmentasi hanya pembanding untuk pembahasan; hasilnya disimpan terpisah.
    if dengan_augmentasi:
        folder = config.FOLDER_BUKTI / "04_pelatihan" / nama
        judul = nama.upper()
    else:
        folder = config.FOLDER_BUKTI / "tanpa_augmentasi" / nama
        judul = f"{nama.upper()} (tanpa augmentasi)"
    folder.mkdir(parents=True, exist_ok=True)

    daftar_gpu = tf.config.list_physical_devices("GPU")
    if daftar_gpu:
        perangkat = "GPU " + tf.config.experimental.get_device_details(daftar_gpu[0]).get("device_name", "")
    else:
        perangkat = "CPU"

    print(f"\n=== Skenario {judul}: {pengaturan['jumlah_blok']} blok, batch {pengaturan['batch']} ===")
    print(f"Perangkat pelatihan: {perangkat}")
    print(f"Augmentasi: {'flip H/V + rotasi 0/90/180/270' if dengan_augmentasi else 'tidak dipakai'}")
    keras.backend.clear_session()
    keras.utils.set_random_seed(config.RANDOM_SEED)

    data_latih = muat_data("latih", pengaturan["batch"], acak=True, dengan_augmentasi=dengan_augmentasi)
    data_validasi = muat_data("validasi", pengaturan["batch"])

    if dengan_augmentasi:
        folder_augmentasi = config.FOLDER_BUKTI / "augmentasi" / nama
        folder_augmentasi.mkdir(parents=True, exist_ok=True)
        simpan_contoh_rotasi(config.FOLDER_BUKTI / "augmentasi" / "contoh_rotasi_4_arah_dan_flip.png")
        simpan_batch_pertama(data_latih, nama, folder_augmentasi / "batch_latih_pertama.png")

    model = bangun_model(pengaturan["jumlah_blok"])
    baris_summary = []
    model.summary(print_fn=lambda teks, **_: baris_summary.append(teks))
    (folder / "arsitektur.txt").write_text("\n".join(baris_summary), encoding="utf-8")
    model.summary()

    callbacks = [
        keras.callbacks.EarlyStopping(monitor="val_loss", patience=config.PATIENCE,
                                      restore_best_weights=True, verbose=1),
        keras.callbacks.ModelCheckpoint(str(folder / f"model_{nama}.keras"), monitor="val_loss",
                                        save_best_only=True, verbose=1),
        keras.callbacks.CSVLogger(str(folder / "riwayat_epoch.csv")),
    ]

    mulai = time.time()
    hasil = model.fit(data_latih, validation_data=data_validasi, epochs=config.EPOCH_MAKS,
                      callbacks=callbacks, verbose=2)
    durasi = time.time() - mulai

    riwayat = hasil.history
    indeks = min(range(len(riwayat["val_loss"])), key=lambda i: riwayat["val_loss"][i])
    ringkasan = {
        "skenario": nama,
        "jumlah_blok": pengaturan["jumlah_blok"],
        "ukuran_batch": pengaturan["batch"],
        "jumlah_parameter": model.count_params(),
        "perangkat": perangkat,
        "epoch_dijalankan": len(riwayat["loss"]),
        "berhenti_lebih_awal": len(riwayat["loss"]) < config.EPOCH_MAKS,
        "epoch_terbaik": indeks + 1,
        "val_loss_terbaik": round(riwayat["val_loss"][indeks], 4),
        "val_accuracy_epoch_terbaik": round(riwayat["val_accuracy"][indeks], 4),
        "loss_latih_epoch_terbaik": round(riwayat["loss"][indeks], 4),
        "accuracy_latih_epoch_terbaik": round(riwayat["accuracy"][indeks], 4),
        "durasi_menit": round(durasi / 60, 1),
    }
    (folder / "ringkasan.json").write_text(json.dumps(ringkasan, indent=2), encoding="utf-8")
    simpan_kurva(riwayat, indeks + 1, judul, folder / "kurva_akurasi_loss.png")

    print(json.dumps(ringkasan, indent=2))
    print(f"Bukti tersimpan di {folder}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("skenario", choices=[*config.SKENARIO, "semua"])
    parser.add_argument("--tanpa-augmentasi", action="store_true",
                        help="run pembanding tanpa flip dan rotasi, disimpan di bukti/tanpa_augmentasi")
    args = parser.parse_args()

    daftar = list(config.SKENARIO) if args.skenario == "semua" else [args.skenario]
    for nama in daftar:
        latih_skenario(nama, dengan_augmentasi=not args.tanpa_augmentasi)


if __name__ == "__main__":
    main()
