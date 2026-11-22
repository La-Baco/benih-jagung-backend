"""Tahap 8: memilih skenario dan mengevaluasi model akhir pada data uji (Subbab 3.10).

Keempat skenario dibandingkan pada data validasi, lalu yang loss validasinya
terendah menjadi model akhir. Data uji baru dipakai di sini, satu kali, untuk
model akhir saja.
"""

import csv
import json
import shutil

import keras
import matplotlib.pyplot as plt
import numpy as np

import config

FOLDER_PELATIHAN = config.FOLDER_BUKTI / "04_pelatihan"
FOLDER_BUKTI = config.FOLDER_BUKTI / "05_evaluasi"
FILE_JENIS_KERUSAKAN = config.FOLDER_DATASET / "jenis_kerusakan.csv"


def muat_data(bagian):
    data = keras.utils.image_dataset_from_directory(
        str(config.FOLDER_OLAH / bagian),
        labels="inferred",
        label_mode="binary",
        class_names=config.NAMA_KELAS,
        image_size=(config.UKURAN_CITRA, config.UKURAN_CITRA),
        batch_size=32,
        shuffle=False,
        verbose=False,
    )
    nama_berkas = [p.replace("\\", "/").split("/")[-1] for p in data.file_paths]
    normalisasi = keras.layers.Rescaling(1.0 / 255)
    data = data.map(lambda x, y: (normalisasi(x), y))
    label = np.concatenate([y.numpy().ravel() for _, y in data]).astype(int)
    return data, nama_berkas, label


def hitung_metrik(label, peluang):
    prediksi = (peluang >= 0.5).astype(int)  # Persamaan 3-2
    tp = int(np.sum((label == 1) & (prediksi == 1)))
    fn = int(np.sum((label == 1) & (prediksi == 0)))
    fp = int(np.sum((label == 0) & (prediksi == 1)))
    tn = int(np.sum((label == 0) & (prediksi == 0)))

    # Persamaan 2-16 sampai 2-19
    akurasi = (tp + tn) / (tp + tn + fp + fn)
    presisi = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * presisi * recall / (presisi + recall) if presisi + recall else 0.0
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "akurasi": akurasi,
            "presisi": presisi, "recall": recall, "f1": f1, "prediksi": prediksi}


def simpan_gambar_confusion_matrix(m, judul, tujuan):
    matriks = np.array([[m["tp"], m["fn"]], [m["fp"], m["tn"]]])
    fig, ax = plt.subplots(figsize=(5, 4.5))
    ax.imshow(matriks, cmap="Blues")
    for (i, j), nilai in np.ndenumerate(matriks):
        warna = "white" if nilai > matriks.max() / 2 else "black"
        ax.text(j, i, str(nilai), ha="center", va="center", fontsize=16, color=warna)
    ax.set_xticks([0, 1], ["Prediksi Layak", "Prediksi Tidak Layak"])
    ax.set_yticks([0, 1], ["Layak", "Tidak Layak"])
    ax.set_ylabel("Label sebenarnya")
    ax.set_title(judul)
    fig.savefig(tujuan, dpi=150, bbox_inches="tight")
    plt.close(fig)


def bandingkan_skenario():
    data_validasi, _, label_validasi = muat_data("validasi")

    baris = []
    for nama in config.SKENARIO:
        path = FOLDER_PELATIHAN / nama / "ringkasan.json"
        if not path.exists():
            raise SystemExit(f"Ringkasan {nama} belum ada. Jalankan 04_latih.py {nama} dulu.")
        ringkasan = json.loads(path.read_text(encoding="utf-8"))

        model = keras.models.load_model(str(FOLDER_PELATIHAN / nama / f"model_{nama}.keras"))
        m = hitung_metrik(label_validasi, model.predict(data_validasi, verbose=0).ravel())
        simpan_gambar_confusion_matrix(m, f"Confusion matrix data validasi {nama.upper()}",
                                       FOLDER_PELATIHAN / nama / "confusion_matrix_validasi.png")

        baris.append({
            **ringkasan,
            "val_tp": m["tp"], "val_fn": m["fn"], "val_fp": m["fp"], "val_tn": m["tn"],
            "val_akurasi": round(m["akurasi"], 4), "val_presisi": round(m["presisi"], 4),
            "val_recall": round(m["recall"], 4), "val_f1": round(m["f1"], 4),
        })

    with open(FOLDER_BUKTI / "perbandingan_skenario.csv", "w", newline="", encoding="utf-8") as f:
        penulis = csv.DictWriter(f, fieldnames=list(baris[0].keys()))
        penulis.writeheader()
        penulis.writerows(baris)

    print("Perbandingan skenario pada data validasi (150 citra)")
    print(f"{'Skenario':<9}{'Blok':>5}{'Batch':>6}{'Epoch':>6}{'Terbaik':>8}{'Val loss':>10}"
          f"{'Akurasi':>9}{'Presisi':>9}{'Recall':>8}{'F1':>8}{'FP':>4}{'FN':>4}")
    for r in baris:
        print(f"{r['skenario'].upper():<9}{r['jumlah_blok']:>5}{r['ukuran_batch']:>6}{r['epoch_dijalankan']:>6}"
              f"{r['epoch_terbaik']:>8}{r['val_loss_terbaik']:>10.4f}{r['val_akurasi']:>9.4f}{r['val_presisi']:>9.4f}"
              f"{r['val_recall']:>8.4f}{r['val_f1']:>8.4f}{r['val_fp']:>4}{r['val_fn']:>4}")

    terpilih = min(baris, key=lambda r: r["val_loss_terbaik"])
    print(f"\nModel akhir: {terpilih['skenario'].upper()} (loss validasi terendah)")
    return terpilih["skenario"]


def baca_jenis_kerusakan():
    if not FILE_JENIS_KERUSAKAN.exists():
        return {}
    with open(FILE_JENIS_KERUSAKAN, encoding="utf-8") as f:
        return {b["berkas"]: b["jenis_kerusakan"] for b in csv.DictReader(f)}


def main():
    FOLDER_BUKTI.mkdir(parents=True, exist_ok=True)
    skenario = bandingkan_skenario()

    model = keras.models.load_model(str(FOLDER_PELATIHAN / skenario / f"model_{skenario}.keras"))
    data_uji, nama_berkas, label = muat_data("uji")
    peluang = model.predict(data_uji, verbose=0).ravel()
    m = hitung_metrik(label, peluang)

    laporan = "\n".join([
        f"Model akhir      : {skenario.upper()}",
        f"Jumlah data uji  : {len(label)} (layak {int(label.sum())}, tidak layak {int((label == 0).sum())})",
        "",
        "Confusion matrix (kelas positif = layak)",
        f"{'':<22}{'Prediksi Layak':>16}{'Prediksi Tidak Layak':>22}",
        f"{'Layak':<22}{'TP = ' + str(m['tp']):>16}{'FN = ' + str(m['fn']):>22}",
        f"{'Tidak layak':<22}{'FP = ' + str(m['fp']):>16}{'TN = ' + str(m['tn']):>22}",
        "",
        f"Akurasi  : {m['akurasi']:.4f} ({m['akurasi'] * 100:.2f}%)",
        f"Presisi  : {m['presisi']:.4f} ({m['presisi'] * 100:.2f}%), dengan FP = {m['fp']}",
        f"Recall   : {m['recall']:.4f} ({m['recall'] * 100:.2f}%)",
        f"F1-score : {m['f1']:.4f} ({m['f1'] * 100:.2f}%)",
    ])
    print("\n" + laporan)
    (FOLDER_BUKTI / "hasil_evaluasi.txt").write_text(laporan + "\n", encoding="utf-8")
    simpan_gambar_confusion_matrix(m, f"Confusion matrix data uji ({skenario.upper()})",
                                   FOLDER_BUKTI / "confusion_matrix.png")

    jenis = baca_jenis_kerusakan()
    with open(FOLDER_BUKTI / "prediksi_data_uji.csv", "w", newline="", encoding="utf-8") as f:
        penulis = csv.writer(f)
        penulis.writerow(["berkas", "label", "peluang_layak", "prediksi", "keterangan", "jenis_kerusakan"])
        for nama, y, p, y_topi in zip(nama_berkas, label, peluang, m["prediksi"]):
            if y == y_topi:
                keterangan = "TP" if y == 1 else "TN"
            else:
                keterangan = "FN" if y == 1 else "FP"
            penulis.writerow([nama, y, f"{p:.4f}", y_topi, keterangan, jenis.get(nama.replace(".png", ".jpg"), "")])

    shutil.copy(FOLDER_PELATIHAN / skenario / f"model_{skenario}.keras", config.FILE_MODEL_AKHIR)
    print(f"\nModel akhir disalin ke {config.FILE_MODEL_AKHIR}")
    print(f"Bukti tersimpan di {FOLDER_BUKTI}")


if __name__ == "__main__":
    main()
