"""Menyusun ulang gambar BAB IV dan lampiran agar terbaca saat dicetak (22 November 2026).

Isi citra tidak diubah; yang diubah hanya tata letaknya:
- tahapan prapemrosesan: 5 panel berjajar -> kisi 3 kolom
- augmentasi: 6 panel berjajar -> kisi 3 x 2 (rotasi kelipatan 90 derajat dan flip, sama dengan pelatihan)
- citra salah prediksi S3: 6 kolom -> 4 kolom dengan label lebih besar
- screenshot HP: bilah status atas (jam, ikon notifikasi) dan bilah navigasi bawah dipotong
Hasil ditulis ke folder gambar naskah LaTeX (argumen 1).
"""

import csv
import shutil
import sys
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np

import config

TUJUAN = Path(sys.argv[1])
BUKTI = config.FOLDER_BUKTI
HASIL = TUJUAN / "hasil"
LAMPIRAN = TUJUAN / "lampiran"
plt.rcParams.update({"font.size": 10})


def kisi_tahapan(sumber, tujuan, kolom=3):
    im = cv2.imread(str(sumber))
    putih = (im.min(axis=2) > 245).all(axis=0)          # kolom pemisah antarpanel
    tepi, mulai = [], None
    for x, p in enumerate(putih):
        if not p and mulai is None:
            mulai = x
        if p and mulai is not None:
            if x - mulai > 50:
                tepi.append((mulai, x))
            mulai = None
    if mulai is not None:
        tepi.append((mulai, len(putih)))
    panel = [im[:, a:b] for a, b in tepi]
    lebar = max(p.shape[1] for p in panel)
    panel = [cv2.copyMakeBorder(p, 0, 0, 0, lebar - p.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255))
             for p in panel]
    kosong = np.full_like(panel[0], 255)
    while len(panel) % kolom:
        panel.append(kosong)
    jarak = np.full((panel[0].shape[0], 20, 3), 255, np.uint8)
    baris = [np.hstack(sum(([p, jarak] for p in panel[i:i + kolom]), [])[:-1]) for i in range(0, len(panel), kolom)]
    jarak_baris = np.full((24, baris[0].shape[1], 3), 255, np.uint8)
    cv2.imwrite(str(tujuan), np.vstack(sum(([b, jarak_baris] for b in baris), [])[:-1]))
    print(tujuan.name, len(tepi), "panel")


def augmentasi():
    nama = "layak_020.png"        # benih utuh dengan ujung jelas, sehingga arah rotasi mudah terlihat
    path = next((config.FOLDER_OLAH / "semua").rglob(nama))
    im = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB)
    varian = [("asli (0°)", im), ("rotasi 90°", np.rot90(im, 1)), ("rotasi 180°", np.rot90(im, 2)),
              ("rotasi 270°", np.rot90(im, 3)), ("flip horizontal", im[:, ::-1]), ("flip vertikal", im[::-1])]
    fig, sumbu = plt.subplots(2, 3, figsize=(6.3, 4.5))
    for ax, (judul, v) in zip(sumbu.ravel(), varian):
        ax.imshow(v)
        ax.set_title(judul)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(HASIL / "augmentasi_kisi.png", dpi=220)
    plt.close(fig)


def salah_s3(kolom=6, ukuran=224):
    jenis = {}
    with open(config.FOLDER_DATASET / "jenis_kerusakan.csv", encoding="utf-8") as f:
        for b in csv.DictReader(f):
            jenis[b["berkas"].replace(".jpg", ".png")] = b["jenis_kerusakan"].replace("_", " ")
    with open(BUKTI / "05_evaluasi" / "semua_skenario" / "prediksi_uji_s3.csv", encoding="utf-8") as f:
        p = [b for b in csv.DictReader(f) if b["label"] != b["prediksi"]]
    p.sort(key=lambda b: (b["label"] == "0", b["berkas"]))     # FN dulu, lalu FP
    tinggi_label = 84
    baris = (len(p) + kolom - 1) // kolom
    lembar = np.full((baris * (ukuran + tinggi_label), kolom * (ukuran + 12), 3), 255, np.uint8)
    for i, b in enumerate(p):
        citra = cv2.imread(str(config.FOLDER_OLAH / "uji" / config.NAMA_KELAS[int(b["label"])] / b["berkas"]))
        r, k = divmod(i, kolom)
        y, x = r * (ukuran + tinggi_label), k * (ukuran + 12)
        lembar[y:y + ukuran, x:x + ukuran] = citra
        ket = "FN" if b["label"] == "1" else "FP"
        teks = [f"{ket}  {b['berkas'].replace('.png', '')}", f"skor {b['skor_kepercayaan_persen'].replace('.', ',')}%"]
        if ket == "FP":
            teks.append(jenis.get(b["berkas"], "-"))
        for j, t in enumerate(teks):
            cv2.putText(lembar, t, (x + 2, y + ukuran + 24 + j * 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2,
                        cv2.LINE_AA)
    cv2.imwrite(str(HASIL / "salah_prediksi_s3_besar.png"), lembar)


def potong_hp(sumber, tujuan):
    im = cv2.imread(str(sumber))
    cv2.imwrite(str(tujuan), im[110:2250])        # bilah status 0-110 px dan bilah navigasi bawah dibuang


def main():
    LAMPIRAN.mkdir(parents=True, exist_ok=True)
    kisi_tahapan(BUKTI / "02_prapemrosesan" / "contoh_tahapan_layak_001.jpg", HASIL / "tahapan_layak_kisi.png")
    kisi_tahapan(BUKTI / "02_prapemrosesan" / "contoh_tahapan_tidak_layak_500.jpg", HASIL / "tahapan_tidak_layak_kisi.png")
    augmentasi()
    salah_s3()

    android = BUKTI / "10_black_box" / "android"
    for nama, baru in {"03a_login_isian": "hp_login", "01a_registrasi_isian": "hp_registrasi",
                       "06a_tautan_terkirim": "hp_lupa_sandi", "07b_galeri_jpeg_hasil": "hp_hasil",
                       "10_riwayat_petani": "hp_riwayat"}.items():
        potong_hp(android / f"{nama}.png", HASIL / f"{baru}.png")
    for p in sorted(android.glob("[0-9]*.png")):
        potong_hp(p, LAMPIRAN / f"android_{p.name}")
    for p in sorted((BUKTI / "10_black_box" / "web").glob("[0-9]*.png")):
        shutil.copy(p, LAMPIRAN / f"web_{p.name}")
    for p in sorted((BUKTI / "02_prapemrosesan").glob("cek_potongan_*.jpg")):
        shutil.copy(p, LAMPIRAN / p.name)
    for s in config.SKENARIO:
        shutil.copy(BUKTI / "04_pelatihan" / s / "kurva_akurasi_loss.png", LAMPIRAN / f"kurva_{s}.png")
        shutil.copy(BUKTI / "04_pelatihan" / s / "confusion_matrix_validasi.png", LAMPIRAN / f"cm_validasi_{s}.png")
    shutil.copy(BUKTI / "01_lingkungan" / "log_01_cek_lingkungan.png", LAMPIRAN / "log_lingkungan.png")
    shutil.copy(BUKTI / "tanpa_augmentasi" / "perbandingan_augmentasi.png", LAMPIRAN / "perbandingan_augmentasi.png")
    print("lampiran:", len(list(LAMPIRAN.iterdir())), "berkas")


if __name__ == "__main__":
    main()
