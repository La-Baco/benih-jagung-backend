"""Tahap penyaring objek (2/4): membentuk dataset 224 x 224 untuk model penyaring.

Dua kelas (label 1 = kelas positif, sama seperti penomoran di Subbab 3.7):
    jagung_ketan_putih        (1)  seluruh 1.000 citra penelitian, layak maupun tidak layak
    bukan_jagung_ketan_putih  (0)  stiker dari 17_siapkan_objek_bukan_ketan.py

Setiap citra dibuat persis seperti yang akan diterima model saat dipakai: potongan persegi
yang berpusat pada objek, lalu diperkecil ke 224 x 224 (Subbab 3.6).

Supaya model tidak menilai dari latar, posisi, ukuran, atau cahaya, kedua kelas dibuat dengan
cara yang sama. Setiap objek menjadi 4 citra:
  - jagung ketan putih: potongan asli dari dataset_olah, ditambah 3 tempelan benih yang sama
    (topeng Otsu) di alas penelitian dan dua latar lain (warna polos atau tekstur DTD).
  - bukan jagung ketan putih: 4 tempelan stiker (2 di alas penelitian, 2 di latar lain).
  Setiap tempelan diputar acak 0-360 derajat, diskalakan acak, dan diberi bayangan, kilap,
  serta variasi kualitas foto (turunkan_kualitas). Versi pertama (25-11-2026) hanya memutar
  stiker bukan, sehingga model belajar bahwa benih yang miring/rebah, kecil, atau terkena
  cahaya keras berarti "bukan" (benih asli di foto uji lapangan ditolak).

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
# Salinan tempelan untuk setiap objek (nama awalan berkas, sumber latar). Bersama potongan asli
# (ketan) atau satu tempelan tambahan di alas penelitian (bukan), tiap objek menjadi 4 citra.
# Stiker lebih kecil dari ini (sisi terpanjang, px) hampir tidak berisi bentuk objek; setelah
# diperbesar ke potongan 224 px hanya menjadi bercak warna buram, sama seperti benih ketan yang
# difoto dari jauh. Stiker seperti itu tidak dipakai.
UKURAN_STIKER_MIN = 32
TEMPELAN = [("alas", "alas_peneliti"), ("latarlain", "lain"), ("latarlain2", "lain")]


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
        if self.rng.random() < 0.4:
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
    """Variasi kualitas foto untuk kedua kelas.

    Meniru foto yang diambil petani di luar protokol penelitian: kamera lebih jauh (resolusi
    objek rendah), cahaya lebih terang/gelap/keras (gamma dan kontras), warna cahaya berbeda,
    derau sensor, dan kompresi JPEG.
    """
    if rng.random() < 0.4:
        faktor = rng.uniform(0.25, 0.7)
        kecil = cv2.resize(citra, None, fx=faktor, fy=faktor, interpolation=cv2.INTER_AREA)
        citra = cv2.resize(kecil, (UKURAN, UKURAN), interpolation=cv2.INTER_LINEAR)
    hasil = citra.astype(np.float32) / 255.0
    hasil = hasil ** rng.uniform(0.65, 1.5)
    hasil = (hasil - hasil.mean()) * rng.uniform(0.75, 1.4) + hasil.mean()
    hasil = hasil * np.float32([rng.uniform(0.9, 1.1) for _ in range(3)]) * 255.0
    hasil += rng.uniform(-15, 15)
    if rng.random() < 0.3:
        hasil += np.random.default_rng(rng.randint(0, 2**31)).normal(0, rng.uniform(2, 7), hasil.shape)
    hasil = np.clip(hasil, 0, 255).astype(np.uint8)
    if rng.random() < 0.3:
        _, data = cv2.imencode(".jpg", hasil, [cv2.IMWRITE_JPEG_QUALITY, rng.randint(40, 90)])
        hasil = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return hasil


def stiker_ketan(path_asli):
    """Benih dari foto penelitian sebagai stiker BGRA (topeng Otsu Subbab 3.6), sama seperti stiker bukan."""
    citra = pp.samakan_lebar(cv2.imread(str(path_asli)))
    _, _, biner = pp.ke_biner(citra)
    kotak = pp.cari_kotak_benih(biner)
    if kotak is None:
        return None
    topeng = np.zeros(biner.shape, np.uint8)
    kontur, _ = cv2.findContours(biner, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cocok = [k for k in kontur if cv2.boundingRect(k) == kotak]
    cv2.drawContours(topeng, cocok, -1, 255, cv2.FILLED)
    x, y, w, h = kotak
    stiker = np.dstack([citra[y:y + h, x:x + w], topeng[y:y + h, x:x + w]])
    # Diperkecil dulu supaya putar/skala berikutnya ringan; sisi terpanjang tetap > 224 px.
    faktor = 400 / max(w, h)
    return cv2.resize(stiker, None, fx=faktor, fy=faktor, interpolation=cv2.INTER_AREA)


def resolusi_seperti_stiker_bukan(stiker, rng):
    """Separuh tempelan ketan diturunkan resolusinya (sisi terpanjang 32-180 px).

    Stiker bukan berasal dari foto publik beresolusi rendah sehingga tampak lebih buram daripada
    benih dari foto 3000 px. Tanpa ini model bisa belajar "tajam = ketan", padahal foto petani
    yang diambil dari jauh juga buram.
    """
    if rng.random() >= 0.5:
        return stiker
    faktor = rng.uniform(UKURAN_STIKER_MIN, 180) / max(stiker.shape[:2])
    return cv2.resize(stiker, None, fx=faktor, fy=faktor, interpolation=cv2.INTER_AREA)


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

    latar = latar.astype(np.float32)
    if rng.random() < 0.5:
        # Bayangan lunak di bawah objek, seperti foto benda nyata di atas alas.
        geser = np.float32([[1, 0, rng.uniform(-8, 8)], [0, 1, rng.uniform(-8, 8)]])
        bayangan = cv2.warpAffine(alfa, geser, (UKURAN, UKURAN))
        bayangan = cv2.GaussianBlur(bayangan, (0, 0), rng.uniform(3, 9))
        latar *= 1 - rng.uniform(0.2, 0.6) * bayangan[..., None]
    objek = objek.astype(np.float32)
    if rng.random() < 0.3:
        # Kilap dari cahaya langsung (lampu/matahari) di satu sisi objek.
        ys, xs = np.nonzero(alfa > 0.5)
        i = rng.randrange(len(xs))
        yy, xx = np.mgrid[0:UKURAN, 0:UKURAN]
        r = rng.uniform(0.08, 0.25) * max(tinggi, lebar)
        kilap = np.exp(-((xx - xs[i]) ** 2 + (yy - ys[i]) ** 2) / (2 * r * r)).astype(np.float32)
        objek += rng.uniform(40, 110) * (kilap * alfa)[..., None]
    objek = np.clip(objek, 0, 255)
    return turunkan_kualitas(tempel(np.clip(latar, 0, 255), objek, alfa), rng)


def bagi_stiker(rng):
    """Kembalikan {bagian: [(kategori, path)]}; almond seluruhnya ke uji_kategori_baru."""
    bagian = {"latih": [], "validasi": [], "uji": [], "uji_kategori_baru": []}
    for folder in sorted((FOLDER_OBJEK / "stiker_bukan").iterdir()):
        if folder.name not in SUMBER:
            continue
        daftar = [p for p in sorted(folder.glob("*.png"))
                  if max(cv2.imread(str(p), cv2.IMREAD_UNCHANGED).shape[:2]) >= UKURAN_STIKER_MIN]
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
                stiker = stiker_ketan(path_asli)
                if stiker is None:
                    continue
                # Perlakuan sama persis dengan stiker bukan (putar, skala, bayangan, kilap, kualitas),
                # supaya posisi benih yang miring/rebah, ukuran, dan cahaya tidak menjadi penanda kelas.
                for jenis_latar, ambil in TEMPELAN:
                    hasil = stiker_di_latar(resolusi_seperti_stiker_bukan(stiker, rng), getattr(latar, ambil)(), rng)
                    if hasil is not None:
                        simpan(bagian, KETAN, f"{jenis_latar}_{path.name}", hasil,
                               f"dataset/{nama_folder_asli[kelas_kelayakan]}/{path_asli.name}", kelas_kelayakan,
                               "alas_penelitian" if ambil == "alas_peneliti" else "lain")
        print(f"{bagian}: kelas {KETAN} selesai")

    # Kelas bukan jagung ketan putih
    for bagian, daftar in bagi_stiker(rng).items():
        for kategori, path in daftar:
            stiker = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            for jenis_latar, ambil in [("asli", "alas_peneliti")] + TEMPELAN:
                hasil = stiker_di_latar(stiker, getattr(latar, ambil)(), rng)
                if hasil is not None:
                    simpan(bagian, BUKAN, f"{jenis_latar}_{path.stem}.png", hasil,
                           f"stiker_bukan/{kategori}/{path.name}", kategori,
                           "alas_penelitian" if ambil == "alas_peneliti" else "lain")
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
