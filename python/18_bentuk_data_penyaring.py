"""Tahap penyaring objek (2/4): membentuk dataset 224 x 224 untuk model penyaring.

Dua kelas (label 1 = kelas positif, sama seperti penomoran di Subbab 3.7):
    jagung_ketan_putih        (1)  seluruh 1.000 citra penelitian, layak maupun tidak layak
    bukan_jagung_ketan_putih  (0)  stiker dari 17_siapkan_objek_bukan_ketan.py

Setiap citra dibuat persis seperti yang akan diterima model saat dipakai: potongan persegi
yang berpusat pada objek, lalu diperkecil ke 224 x 224 (Subbab 3.6).

Supaya model tidak menilai dari latar, kedua kelas muncul di latar yang sama:
  - jagung ketan putih: potongan asli dari dataset_olah (latar alas penelitian), ditambah satu
    salinan yang benihnya dipindah ke latar lain (warna polos atau tekstur DTD).
  - bukan jagung ketan putih: setiap stiker ditempel dua kali, sekali di atas potongan alas
    penelitian dan sekali di atas latar lain.

Pembagian data:
  - jagung ketan putih mengikuti pembagian penelitian (dataset_olah/latih, validasi, uji),
    jadi citra uji model kelayakan juga menjadi citra uji penyaring.
  - stiker dibagi 70:15:15 per kategori dengan seed 42. Dua salinan dari stiker yang sama
    selalu berada di bagian yang sama.
  - kategori almond tidak dipakai untuk latih/validasi. Seluruhnya masuk ke folder
    uji_kategori_baru untuk melihat perilaku model terhadap benda yang belum pernah dilihat.

Keluaran: <proyek>/dataset_penyaring/{latih,validasi,uji,uji_kategori_baru}/<kelas>/*.png
          <proyek>/dataset_penyaring/daftar_citra.csv
"""

import csv
import importlib
import io
import random
import shutil

import cv2
import numpy as np
import pyarrow.parquet as pq
from PIL import Image

import config
import prapemrosesan as pp

SUMBER = importlib.import_module("17_siapkan_objek_bukan_ketan").SUMBER

FOLDER_OBJEK = config.FOLDER_PROYEK / "dataset_objek"
FOLDER_PENYARING = config.FOLDER_PROYEK / "dataset_penyaring"
KATEGORI_UJI_BARU = {"almond"}
UKURAN = config.UKURAN_CITRA
KETAN, BUKAN = config.NAMA_KELAS_PENYARING[1], config.NAMA_KELAS_PENYARING[0]


class Latar:
    """Sumber latar: potongan alas penelitian, warna polos, dan tekstur DTD."""

    def __init__(self, rng):
        self.rng = rng
        self.peneliti = [cv2.imread(str(p)) for p in sorted((FOLDER_OBJEK / "latar_peneliti").glob("*.jpg"))]
        path_dtd = next((FOLDER_OBJEK / "sumber_publik" / "latar_tekstur").glob("*.parquet"))
        self.dtd = []
        for sel in pq.read_table(path_dtd, columns=["image"]).column("image").to_pylist():
            rgb = np.array(Image.open(io.BytesIO(sel["bytes"])).convert("RGB"))
            self.dtd.append(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))

    def alas_peneliti(self):
        latar = self.rng.choice(self.peneliti)
        latar = np.rot90(latar, self.rng.randint(0, 3)).copy()
        return cv2.resize(latar, (UKURAN, UKURAN), interpolation=cv2.INTER_AREA)

    def lain(self):
        if self.rng.random() < 0.3:
            tekstur = self.rng.choice(self.dtd)
            tinggi, lebar = tekstur.shape[:2]
            sisi = self.rng.randint(min(tinggi, lebar) // 2, min(tinggi, lebar))
            y, x = self.rng.randint(0, tinggi - sisi), self.rng.randint(0, lebar - sisi)
            return cv2.resize(tekstur[y:y + sisi, x:x + sisi], (UKURAN, UKURAN), interpolation=cv2.INTER_AREA)
        # Warna polos dengan gradasi cahaya dan sedikit derau, menyerupai foto alas polos.
        hsv = np.uint8([[[self.rng.randint(0, 179), self.rng.randint(0, 255), self.rng.randint(25, 245)]]])
        warna = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0].astype(np.float32)
        sumbu = np.linspace(-1, 1, UKURAN, dtype=np.float32)
        arah = self.rng.uniform(0, 2 * np.pi)
        gradasi = np.cos(arah) * sumbu[None, :] + np.sin(arah) * sumbu[:, None]
        latar = warna[None, None, :] * (1 + self.rng.uniform(0, 0.25) * gradasi[..., None])
        latar += np.random.default_rng(self.rng.randint(0, 2**31)).normal(0, self.rng.uniform(1, 6), latar.shape)
        return np.clip(latar, 0, 255).astype(np.uint8)


def tempel(latar, objek_bgr, alfa):
    """Tempel objek berukuran sama dengan latar memakai alfa 0-1 yang tepinya dihaluskan."""
    alfa = cv2.GaussianBlur(alfa.astype(np.float32), (3, 3), 0)[..., None]
    return (objek_bgr * alfa + latar * (1 - alfa)).astype(np.uint8)


def turunkan_kualitas(citra, rng):
    """Variasi kualitas foto (resolusi, derau, kecerahan) untuk kedua kelas."""
    if rng.random() < 0.3:
        faktor = rng.uniform(0.3, 0.7)
        kecil = cv2.resize(citra, None, fx=faktor, fy=faktor, interpolation=cv2.INTER_AREA)
        citra = cv2.resize(kecil, (UKURAN, UKURAN), interpolation=cv2.INTER_LINEAR)
    hasil = citra.astype(np.float32) * rng.uniform(0.85, 1.15) + rng.uniform(-12, 12)
    if rng.random() < 0.3:
        hasil += np.random.default_rng(rng.randint(0, 2**31)).normal(0, rng.uniform(2, 7), hasil.shape)
    return np.clip(hasil, 0, 255).astype(np.uint8)


def ketan_di_latar_lain(path_asli, sisi, latar, rng):
    """Pindahkan benih dari foto penelitian ke latar lain, dengan potongan yang sama seperti Subbab 3.6."""
    citra = pp.samakan_lebar(cv2.imread(str(path_asli)))
    _, _, biner = pp.ke_biner(citra)
    kotak = pp.cari_kotak_benih(biner)
    if kotak is None:
        return None
    topeng = np.zeros(biner.shape, np.uint8)
    kontur, _ = cv2.findContours(biner, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cocok = [k for k in kontur if cv2.boundingRect(k) == kotak]
    cv2.drawContours(topeng, cocok, -1, 255, cv2.FILLED)
    objek = pp.ubah_ukuran(pp.potong_persegi(citra, kotak, sisi))
    alfa = pp.ubah_ukuran(pp.potong_persegi(topeng, kotak, sisi)) / 255.0
    return turunkan_kualitas(tempel(latar, objek, alfa), rng)


def stiker_di_latar(stiker, latar, rng):
    """Putar stiker acak, skalakan sehingga sisi terpanjangnya 35-92 % sisi potongan, taruh di tengah.

    Rentang 35-92 % mengikuti benih di dataset: max(w, h) 504-1230 px pada potongan S = 1330 px.
    """
    sudut = rng.uniform(0, 360)
    tinggi, lebar = stiker.shape[:2]
    matriks = cv2.getRotationMatrix2D((lebar / 2, tinggi / 2), sudut, 1.0)
    cos, sin = abs(matriks[0, 0]), abs(matriks[0, 1])
    lebar_baru, tinggi_baru = int(tinggi * sin + lebar * cos), int(tinggi * cos + lebar * sin)
    matriks[0, 2] += lebar_baru / 2 - lebar / 2
    matriks[1, 2] += tinggi_baru / 2 - tinggi / 2
    putar = cv2.warpAffine(stiker, matriks, (lebar_baru, tinggi_baru), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    ys, xs = np.nonzero(putar[..., 3] > 127)
    if len(xs) == 0:
        return None
    putar = putar[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

    skala = rng.uniform(0.35, 0.92) * UKURAN / max(putar.shape[:2])
    putar = cv2.resize(putar, None, fx=skala, fy=skala,
                       interpolation=cv2.INTER_AREA if skala < 1 else cv2.INTER_LINEAR)
    tinggi, lebar = putar.shape[:2]
    y, x = (UKURAN - tinggi) // 2, (UKURAN - lebar) // 2
    objek = latar.copy()
    alfa = np.zeros((UKURAN, UKURAN), np.float32)
    objek[y:y + tinggi, x:x + lebar] = putar[..., :3]
    alfa[y:y + tinggi, x:x + lebar] = putar[..., 3] / 255.0
    return turunkan_kualitas(tempel(latar, objek, alfa), rng)


def bagi_stiker(rng):
    """Kembalikan {bagian: [(kategori, path)]}; almond seluruhnya ke uji_kategori_baru."""
    bagian = {"latih": [], "validasi": [], "uji": [], "uji_kategori_baru": []}
    for folder in sorted((FOLDER_OBJEK / "stiker_bukan").iterdir()):
        if folder.name not in SUMBER:
            continue
        daftar = sorted(folder.glob("*.png"))
        if folder.name in KATEGORI_UJI_BARU:
            bagian["uji_kategori_baru"] += [(folder.name, p) for p in daftar]
            continue
        rng.shuffle(daftar)
        n_latih = round(len(daftar) * config.PROPORSI_BAGIAN["latih"])
        n_validasi = round(len(daftar) * config.PROPORSI_BAGIAN["validasi"])
        bagian["latih"] += [(folder.name, p) for p in daftar[:n_latih]]
        bagian["validasi"] += [(folder.name, p) for p in daftar[n_latih:n_latih + n_validasi]]
        bagian["uji"] += [(folder.name, p) for p in daftar[n_latih + n_validasi:]]
    return bagian


def main():
    rng = random.Random(config.RANDOM_SEED)
    sisi = 1330  # S dari prapemrosesan penelitian (model/prapemrosesan.json)
    latar = Latar(rng)
    if FOLDER_PENYARING.exists():
        shutil.rmtree(FOLDER_PENYARING)

    baris = []

    def simpan(bagian, kelas, nama, citra, asal, kategori, jenis_latar):
        folder = FOLDER_PENYARING / bagian / kelas
        folder.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(folder / nama), citra)
        baris.append({"bagian": bagian, "kelas": kelas, "berkas": nama, "kategori": kategori,
                      "latar": jenis_latar, "asal": asal})

    # Kelas jagung ketan putih
    nama_folder_asli = {v: k for k, v in config.KELAS_ASLI.items()}
    for bagian in ["latih", "validasi", "uji"]:
        for kelas_kelayakan in ["layak", "tidak_layak"]:
            for path in sorted((config.FOLDER_OLAH / bagian / kelas_kelayakan).glob("*.png")):
                simpan(bagian, KETAN, f"asli_{path.name}", cv2.imread(str(path)),
                       f"dataset_olah/{bagian}/{kelas_kelayakan}/{path.name}", kelas_kelayakan, "alas_penelitian")
                path_asli = config.FOLDER_DATASET / nama_folder_asli[kelas_kelayakan] / (path.stem + ".jpg")
                hasil = ketan_di_latar_lain(path_asli, sisi, latar.lain(), rng)
                if hasil is not None:
                    simpan(bagian, KETAN, f"latarlain_{path.name}", hasil,
                           f"dataset/{nama_folder_asli[kelas_kelayakan]}/{path_asli.name}", kelas_kelayakan, "lain")
        print(f"{bagian}: kelas {KETAN} selesai")

    # Kelas bukan jagung ketan putih
    for bagian, daftar in bagi_stiker(rng).items():
        for kategori, path in daftar:
            stiker = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            for jenis_latar, ambil in [("alas_penelitian", latar.alas_peneliti), ("lain", latar.lain)]:
                hasil = stiker_di_latar(stiker, ambil(), rng)
                if hasil is not None:
                    awalan = "alas" if jenis_latar == "alas_penelitian" else "latarlain"
                    simpan(bagian, BUKAN, f"{awalan}_{path.stem}.png", hasil,
                           f"stiker_bukan/{kategori}/{path.name}", kategori, jenis_latar)
        print(f"{bagian}: kelas {BUKAN} selesai")

    with open(FOLDER_PENYARING / "daftar_citra.csv", "w", newline="", encoding="utf-8") as f:
        penulis = csv.DictWriter(f, fieldnames=["bagian", "kelas", "berkas", "kategori", "latar", "asal"])
        penulis.writeheader()
        penulis.writerows(baris)

    for bagian in ["latih", "validasi", "uji", "uji_kategori_baru"]:
        jumlah = {k: sum(1 for b in baris if b["bagian"] == bagian and b["kelas"] == k) for k in [KETAN, BUKAN]}
        print(bagian, jumlah)


if __name__ == "__main__":
    main()
