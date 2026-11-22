"""Evaluasi keempat skenario pada data latih, validasi, dan uji (permintaan peneliti, 22 November 2026).

Tujuannya dua:
1. Laporan BAB IV menampilkan hasil uji semua skenario, bukan hanya model akhir.
2. Memilih model untuk sistem yang tidak overfitting dan tidak terlalu percaya diri.

Aturan pemilihan model sistem ditetapkan sebelum skrip dijalankan:
- Ukuran utama adalah loss BCE pada data uji. Loss ini naik bila model salah, dan naik
  jauh lebih besar bila model salah dengan keyakinan tinggi.
- Bila selisih loss uji dua skenario kurang dari 0,01, dipilih yang parameternya lebih sedikit.
Tanda overfitting dilaporkan dari selisih akurasi latih dan akurasi uji, serta rasio loss uji
terhadap loss latih. Data latih dinilai tanpa augmentasi dan tanpa dropout (mode inferensi).
"""

import csv
import json

import keras
import matplotlib.pyplot as plt
import numpy as np

import config

FOLDER_PELATIHAN = config.FOLDER_BUKTI / "04_pelatihan"
FOLDER_BUKTI = config.FOLDER_BUKTI / "05_evaluasi" / "semua_skenario"
NAMA_BAGIAN = ("latih", "validasi", "uji")


def muat_data(bagian):
    data = keras.utils.image_dataset_from_directory(
        str(config.FOLDER_OLAH / bagian), labels="inferred", label_mode="binary",
        class_names=config.NAMA_KELAS, image_size=(config.UKURAN_CITRA, config.UKURAN_CITRA),
        batch_size=32, shuffle=False, verbose=False,
    )
    nama = [p.replace("\\", "/").split("/")[-1] for p in data.file_paths]
    normalisasi = keras.layers.Rescaling(1.0 / 255)
    data = data.map(lambda x, y: (normalisasi(x), y))
    label = np.concatenate([y.numpy().ravel() for _, y in data]).astype(int)
    return data, nama, label


def bce(label, peluang):
    p = np.clip(peluang, 1e-7, 1 - 1e-7)
    return float(-np.mean(label * np.log(p) + (1 - label) * np.log(1 - p)))


def metrik(label, peluang):
    prediksi = (peluang >= 0.5).astype(int)
    tp = int(np.sum((label == 1) & (prediksi == 1)))
    fn = int(np.sum((label == 1) & (prediksi == 0)))
    fp = int(np.sum((label == 0) & (prediksi == 1)))
    tn = int(np.sum((label == 0) & (prediksi == 0)))
    akurasi = (tp + tn) / len(label)
    presisi = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * presisi * recall / (presisi + recall) if presisi + recall else 0.0
    skor = np.maximum(peluang, 1 - peluang)          # Persamaan skor kepercayaan
    salah = prediksi != label
    # Expected calibration error, 10 selang skor: rata-rata selisih keyakinan dan ketepatan.
    ece = 0.0
    for a, b in zip(np.linspace(0.5, 1.0, 11)[:-1], np.linspace(0.5, 1.0, 11)[1:]):
        di = (skor >= a) & ((skor < b) if b < 1.0 else (skor <= b))
        if di.any():
            ece += di.mean() * abs(skor[di].mean() - (~salah[di]).mean())
    return {
        "tp": tp, "fn": fn, "fp": fp, "tn": tn, "akurasi": akurasi, "presisi": presisi,
        "recall": recall, "f1": f1, "loss": bce(label, peluang), "ece": float(ece),
        "skor_rata": float(skor.mean()),
        "skor_tampil_99_99": int(np.sum(np.floor(skor * 10000) / 100 >= 99.99)),
        "salah_yakin_95": int(np.sum(salah & (skor >= 0.95))),
        "prediksi": prediksi, "peluang": peluang,
    }


def main():
    FOLDER_BUKTI.mkdir(parents=True, exist_ok=True)
    data = {b: muat_data(b) for b in NAMA_BAGIAN}
    hasil = []
    for nama in config.SKENARIO:
        ringkasan = json.loads((FOLDER_PELATIHAN / nama / "ringkasan.json").read_text(encoding="utf-8"))
        model = keras.models.load_model(str(FOLDER_PELATIHAN / nama / f"model_{nama}.keras"))
        m = {b: metrik(data[b][2], model.predict(data[b][0], verbose=0).ravel()) for b in NAMA_BAGIAN}
        hasil.append({"skenario": nama, "ringkasan": ringkasan, **m})

        with open(FOLDER_BUKTI / f"prediksi_uji_{nama}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["berkas", "label", "peluang_layak", "prediksi", "skor_kepercayaan_persen"])
            for berkas, y, p, yt in zip(data["uji"][1], data["uji"][2], m["uji"]["peluang"], m["uji"]["prediksi"]):
                w.writerow([berkas, y, f"{p:.6f}", yt, f"{np.floor(max(p, 1 - p) * 10000) / 100:.2f}"])

    kolom = ["skenario", "jumlah_blok", "ukuran_batch", "jumlah_parameter", "epoch_terbaik",
             "akurasi_latih", "loss_latih", "akurasi_validasi", "loss_validasi",
             "uji_tp", "uji_fn", "uji_fp", "uji_tn", "akurasi_uji", "presisi_uji", "recall_uji", "f1_uji",
             "loss_uji", "ece_uji", "skor_rata_uji", "uji_skor_tampil_99_99", "uji_salah_dengan_skor_95",
             "selisih_akurasi_latih_uji", "rasio_loss_uji_latih"]
    baris = []
    for h in hasil:
        r = h["ringkasan"]
        baris.append({
            "skenario": h["skenario"].upper(), "jumlah_blok": r["jumlah_blok"], "ukuran_batch": r["ukuran_batch"],
            "jumlah_parameter": r["jumlah_parameter"], "epoch_terbaik": r["epoch_terbaik"],
            "akurasi_latih": round(h["latih"]["akurasi"], 4), "loss_latih": round(h["latih"]["loss"], 4),
            "akurasi_validasi": round(h["validasi"]["akurasi"], 4), "loss_validasi": round(h["validasi"]["loss"], 4),
            "uji_tp": h["uji"]["tp"], "uji_fn": h["uji"]["fn"], "uji_fp": h["uji"]["fp"], "uji_tn": h["uji"]["tn"],
            "akurasi_uji": round(h["uji"]["akurasi"], 4), "presisi_uji": round(h["uji"]["presisi"], 4),
            "recall_uji": round(h["uji"]["recall"], 4), "f1_uji": round(h["uji"]["f1"], 4),
            "loss_uji": round(h["uji"]["loss"], 4), "ece_uji": round(h["uji"]["ece"], 4),
            "skor_rata_uji": round(h["uji"]["skor_rata"], 4),
            "uji_skor_tampil_99_99": h["uji"]["skor_tampil_99_99"],
            "uji_salah_dengan_skor_95": h["uji"]["salah_yakin_95"],
            "selisih_akurasi_latih_uji": round(h["latih"]["akurasi"] - h["uji"]["akurasi"], 4),
            "rasio_loss_uji_latih": round(h["uji"]["loss"] / h["latih"]["loss"], 2),
        })
    with open(FOLDER_BUKTI / "evaluasi_semua_skenario.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolom)
        w.writeheader()
        w.writerows(baris)

    # Aturan pemilihan model sistem (lihat docstring).
    urut = sorted(baris, key=lambda b: b["loss_uji"])
    terpilih = urut[0]
    for calon in urut[1:]:
        if calon["loss_uji"] - terpilih["loss_uji"] < 0.01 and calon["jumlah_parameter"] < terpilih["jumlah_parameter"]:
            terpilih = calon

    teks = ["Evaluasi keempat skenario (latih 700, validasi 150, uji 150 citra)", ""]
    teks.append(f"{'':<4}{'AkLatih':>8}{'LsLatih':>8}{'AkVal':>7}{'LsVal':>7}{'AkUji':>7}{'Pres':>7}{'Rec':>7}"
                f"{'F1':>7}{'LsUji':>7}{'ECE':>7}{'FP':>4}{'FN':>4}{'>=99,99':>8}{'Salah>=95%':>11}{'Selisih':>8}{'Rasio':>7}")
    for b in baris:
        teks.append(f"{b['skenario']:<4}{b['akurasi_latih']:>8.4f}{b['loss_latih']:>8.4f}{b['akurasi_validasi']:>7.4f}"
                    f"{b['loss_validasi']:>7.4f}{b['akurasi_uji']:>7.4f}{b['presisi_uji']:>7.4f}{b['recall_uji']:>7.4f}"
                    f"{b['f1_uji']:>7.4f}{b['loss_uji']:>7.4f}{b['ece_uji']:>7.4f}{b['uji_fp']:>4}{b['uji_fn']:>4}"
                    f"{b['uji_skor_tampil_99_99']:>8}{b['uji_salah_dengan_skor_95']:>11}"
                    f"{b['selisih_akurasi_latih_uji']:>8.4f}{b['rasio_loss_uji_latih']:>7.2f}")
    teks += ["", f"Model untuk sistem: {terpilih['skenario']} (loss uji terendah; selisih < 0,01 -> parameter lebih sedikit)"]
    print("\n".join(teks))
    (FOLDER_BUKTI / "hasil_semua_skenario.txt").write_text("\n".join(teks) + "\n", encoding="utf-8")

    # Sebaran skor kepercayaan pada data uji: benar vs salah.
    fig, sumbu = plt.subplots(1, 4, figsize=(16, 3.6), sharey=True)
    for ax, h in zip(sumbu, hasil):
        skor = np.maximum(h["uji"]["peluang"], 1 - h["uji"]["peluang"]) * 100
        salah = h["uji"]["prediksi"] != data["uji"][2]
        ax.hist([skor[~salah], skor[salah]], bins=np.linspace(50, 100, 11), stacked=True,
                label=["benar", "salah"], color=["#4c78a8", "#e45756"])
        ax.set_title(f"{h['skenario'].upper()}: loss uji {h['uji']['loss']:.3f}")
        ax.set_xlabel("skor kepercayaan (%)")
    sumbu[0].set_ylabel("jumlah citra uji")
    sumbu[0].legend()
    fig.tight_layout()
    fig.savefig(FOLDER_BUKTI / "sebaran_skor_kepercayaan.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
