"""Tahap 5: prapemrosesan seluruh citra dataset (Subbab 3.6).

Putaran pertama mencari kotak benih di setiap citra untuk menghitung sisi
persegi S (Persamaan 3-1). Putaran kedua memotong, mengubah ukuran, dan
menyimpan hasilnya ke dataset_olah/semua/<kelas>/.
"""

import csv
import json
import shutil

import cv2
import numpy as np

import config
import prapemrosesan as pp

FOLDER_BUKTI = config.FOLDER_BUKTI / "02_prapemrosesan"
FOLDER_SEMUA = config.FOLDER_OLAH / "semua"


def daftar_citra():
    hasil = []
    for folder, kelas in config.KELAS_ASLI.items():
        for path in sorted((config.FOLDER_DATASET / folder).glob("*.jpg")):
            hasil.append((path, kelas))
    return hasil


def cari_semua_kotak(daftar):
    data = []
    gagal = []
    for i, (path, kelas) in enumerate(daftar, 1):
        citra = pp.samakan_lebar(cv2.imread(str(path)))
        _, ambang, biner = pp.ke_biner(citra)
        kotak = pp.cari_kotak_benih(biner)
        if kotak is None:
            gagal.append(path.name)
        else:
            data.append({"berkas": path.name, "kelas": kelas, "ambang_otsu": int(ambang),
                         "x": kotak[0], "y": kotak[1], "w": kotak[2], "h": kotak[3]})
        if i % 100 == 0:
            print(f"  kotak benih: {i}/{len(daftar)}")
    return data, gagal


def simpan_lembar_cek(daftar_png):
    """Gabungkan 100 hasil potong per lembar supaya semua citra bisa dicek mata."""
    kecil = 112
    for nomor, mulai in enumerate(range(0, len(daftar_png), 100), 1):
        lembar = np.full((10 * (kecil + 14), 10 * kecil, 3), 255, np.uint8)
        for i, path in enumerate(daftar_png[mulai:mulai + 100]):
            baris, kolom = divmod(i, 10)
            y = baris * (kecil + 14)
            x = kolom * kecil
            lembar[y:y + kecil, x:x + kecil] = cv2.resize(cv2.imread(str(path)), (kecil, kecil))
            cv2.putText(lembar, path.stem.replace("tidak_layak", "TL"), (x + 2, y + kecil + 11),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 0, 0), 1)
        cv2.imwrite(str(FOLDER_BUKTI / f"cek_potongan_{nomor:02d}.jpg"), lembar)


def simpan_contoh_tahapan(path, sisi):
    """Satu gambar berisi tiap tahap prapemrosesan, untuk BAB IV."""
    citra = pp.samakan_lebar(cv2.imread(str(path)))
    abu, ambang, biner = pp.ke_biner(citra)
    x, y, w, h = pp.cari_kotak_benih(biner)

    kotak = citra.copy()
    cv2.rectangle(kotak, (x, y), (x + w, y + h), (0, 255, 0), 12)
    kiri = x + w // 2 - sisi // 2
    atas = y + h // 2 - sisi // 2
    cv2.rectangle(kotak, (kiri, atas), (kiri + sisi, atas + sisi), (0, 0, 255), 12)

    hasil = pp.ubah_ukuran(pp.potong_persegi(citra, (x, y, w, h), sisi))

    panel = [
        ("a. citra asli", citra),
        ("b. grayscale", cv2.cvtColor(abu, cv2.COLOR_GRAY2BGR)),
        (f"c. biner Otsu (T={int(ambang)})", cv2.cvtColor(biner, cv2.COLOR_GRAY2BGR)),
        ("d. kontur dan potongan", kotak),
        ("e. hasil 224 x 224", hasil),
    ]
    ukuran = 400
    gambar = np.full((ukuran + 40, len(panel) * (ukuran + 10), 3), 255, np.uint8)
    for i, (judul, isi) in enumerate(panel):
        x0 = i * (ukuran + 10)
        gambar[0:ukuran, x0:x0 + ukuran] = cv2.resize(isi, (ukuran, ukuran))
        cv2.putText(gambar, judul, (x0 + 5, ukuran + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.imwrite(str(FOLDER_BUKTI / f"contoh_tahapan_{path.stem}.jpg"), gambar)


def main():
    FOLDER_BUKTI.mkdir(parents=True, exist_ok=True)
    config.FOLDER_MODEL.mkdir(parents=True, exist_ok=True)

    daftar = daftar_citra()
    print(f"Jumlah citra: {len(daftar)}")

    print("Putaran 1: mencari kotak benih")
    data, gagal = cari_semua_kotak(daftar)
    if gagal:
        print("Benih tidak terdeteksi pada:", ", ".join(gagal))
        raise SystemExit("Periksa citra tersebut dulu, prapemrosesan dihentikan.")

    terbesar = max(max(d["w"], d["h"]) for d in data)
    sisi = terbesar + 2 * config.BATAS_TEPI
    print(f"max(w, h) terbesar = {terbesar} px, b = {config.BATAS_TEPI} px, S = {sisi} px")

    urut = sorted(data, key=lambda d: max(d["w"], d["h"]), reverse=True)
    print("Lima benih terbesar (cek apakah memang benih, bukan latar):")
    for d in urut[:5]:
        print(f"  {d['berkas']}: {max(d['w'], d['h'])} px")

    with open(FOLDER_BUKTI / "ukuran_benih.csv", "w", newline="", encoding="utf-8") as f:
        penulis = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        penulis.writeheader()
        penulis.writerows(data)

    pengaturan = {
        "sisi_potong": sisi,
        "batas_tepi": config.BATAS_TEPI,
        "max_wh_terbesar": terbesar,
        "lebar_acuan": config.LEBAR_ACUAN,
        "kernel_opening": config.KERNEL_OPENING,
        "ukuran_citra": config.UKURAN_CITRA,
    }
    config.FILE_PRAPEMROSESAN.write_text(json.dumps(pengaturan, indent=2), encoding="utf-8")
    shutil.copy(config.FILE_PRAPEMROSESAN, FOLDER_BUKTI / "prapemrosesan.json")

    print("Putaran 2: memotong dan menyimpan citra 224 x 224")
    if FOLDER_SEMUA.exists():
        shutil.rmtree(FOLDER_SEMUA)
    for kelas in config.NAMA_KELAS:
        (FOLDER_SEMUA / kelas).mkdir(parents=True)

    kotak_per_berkas = {d["berkas"]: (d["x"], d["y"], d["w"], d["h"]) for d in data}
    hasil_png = []
    for i, (path, kelas) in enumerate(daftar, 1):
        citra = pp.samakan_lebar(cv2.imread(str(path)))
        potongan = pp.ubah_ukuran(pp.potong_persegi(citra, kotak_per_berkas[path.name], sisi))
        tujuan = FOLDER_SEMUA / kelas / f"{path.stem}.png"
        cv2.imwrite(str(tujuan), potongan)
        hasil_png.append(tujuan)
        if i % 100 == 0:
            print(f"  disimpan: {i}/{len(daftar)}")

    simpan_lembar_cek(hasil_png)
    simpan_contoh_tahapan(daftar[0][0], sisi)
    simpan_contoh_tahapan(daftar[-1][0], sisi)
    print(f"Selesai. Hasil di {FOLDER_SEMUA}, bukti di {FOLDER_BUKTI}")


if __name__ == "__main__":
    main()
