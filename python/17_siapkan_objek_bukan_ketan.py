"""Tahap penyaring objek (1/4): mengambil potongan objek "bukan jagung ketan putih" dari dataset publik.

Model kelayakan (S3) hanya pernah melihat benih jagung ketan putih, sehingga benda lain
seperti kerikil putih tetap dinilai "Layak". Tahap penyaring membutuhkan contoh benda
selain jagung ketan putih. Contoh tersebut diambil dari dataset publik berlisensi terbuka
(lihat SUMBER di bawah), bukan dibuat-buat.

Setiap foto sumber dipotong menjadi satu "stiker": objeknya saja, dengan latar dibuang
lewat kanal alfa. Latar dibuang supaya pada tahap berikutnya (18_bentuk_data_penyaring.py)
objek bisa ditempel ke latar alas penelitian. Dengan begitu model tidak bisa membedakan
kelas hanya dari latarnya.

Masukan : <proyek>/dataset_objek/sumber_publik/...   (diunduh dari Hugging Face)
Keluaran: <proyek>/dataset_objek/stiker_bukan/<kategori>/<kategori>_NNNN.png
          <proyek>/dataset_objek/sumber_stiker_bukan.csv
          <proyek>/dataset_objek/latar_peneliti/latar_NNN.jpg  (potongan alas dari foto penelitian)
"""

import csv
import io
import random
from pathlib import Path

import cv2
import numpy as np
import pyarrow.parquet as pq
from PIL import Image

import config
import prapemrosesan as pp

FOLDER_OBJEK = config.FOLDER_PROYEK / "dataset_objek"
FOLDER_SUMBER = FOLDER_OBJEK / "sumber_publik"
FOLDER_STIKER = FOLDER_OBJEK / "stiker_bukan"
FOLDER_LATAR = FOLDER_OBJEK / "latar_peneliti"

# kategori: (dataset asal, lisensi, jumlah maksimum stiker)
SUMBER = {
    "batu":        ("udayl/rocks (rock-classification.zip, igneous-metamorphic-sedimentary-rocks-and-minerals.zip)",
                    "MIT", 400),
    # Hanya biji kuning/oranye (lihat jagung_kuning). Biji jagung putih di dataset ini tidak
    # dipakai: secara visual tidak bisa dibedakan dari jagung ketan putih, dan versi pertama
    # yang memakainya sebagai "bukan" membuat benih ketan asli ikut ditolak.
    "jagung_lain": ("Project-AgML/EfficientMaize_classification (raw), hanya biji kuning/oranye", "CC BY 4.0", 150),
    "kedelai":     ("Project-AgML/soybean_variety_classification (shard 0)", "CC BY 4.0", 100),
    "padi":        ("Project-AgML/rice_grain_variety_classification (raw)", "CC BY 4.0", 130),
    "gandum":      ("Project-AgML/wheat_seed_variety_classification", "CC BY 4.0", 90),
    "kopi":        ("Project-AgML/coffee_bean_quality_classification", "CC BY 4.0", 130),
    # Kategori ini tidak dipakai saat pelatihan; hanya untuk menguji benda yang belum pernah dilihat model.
    "almond":      ("MustafaYL/AlmondVarieties", "MIT", 150),
}
SISI_STIKER_MAKS = 400


def baca_parquet(path):
    tabel = pq.read_table(path, columns=["image"])
    for i, sel in enumerate(tabel.column("image").to_pylist()):
        rgb = np.array(Image.open(io.BytesIO(sel["bytes"])).convert("RGB"))
        yield i, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def kecilkan(citra, sisi_maks):
    skala = sisi_maks / max(citra.shape[:2])
    if skala >= 1:
        return citra
    return cv2.resize(citra, None, fx=skala, fy=skala, interpolation=cv2.INTER_AREA)


def kontur_tidak_di_tepi(biner):
    tinggi, lebar = biner.shape
    kontur, _ = cv2.findContours(biner, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    hasil = []
    for k in kontur:
        x, y, w, h = cv2.boundingRect(k)
        if x > 0 and y > 0 and x + w < lebar and y + h < tinggi:
            hasil.append(k)
    return sorted(hasil, key=cv2.contourArea, reverse=True)


def latar_polos(citra):
    """Foto dianggap berlatar polos bila warna tepi citranya seragam (simpangan baku Lab kecil)."""
    lab = cv2.cvtColor(citra, cv2.COLOR_BGR2LAB).astype(np.float32)
    t = max(4, min(citra.shape[:2]) // 40)
    tepi = np.concatenate([lab[:t].reshape(-1, 3), lab[-t:].reshape(-1, 3),
                           lab[:, :t].reshape(-1, 3), lab[:, -t:].reshape(-1, 3)])
    return float(np.linalg.norm(tepi.std(axis=0))) < 18


def baca(path):
    """cv2.imread gagal membaca nama berkas non-ASCII di Windows, jadi berkas dibaca sebagai byte."""
    return cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)


def rapikan_topeng(citra, kontur):
    """Haluskan batas objek dengan GrabCut supaya sisa latar (bayangan, pinggiran biru) tidak ikut.

    Bagian dalam kontur yang dikikis dianggap pasti objek, daerah sekitar kontur dianggap
    mungkin objek/mungkin latar, dan sisanya pasti latar.
    """
    x, y, w, h = cv2.boundingRect(kontur)
    tepi = max(8, max(w, h) // 5)
    x0, y0 = max(0, x - tepi), max(0, y - tepi)
    x1, y1 = min(citra.shape[1], x + w + tepi), min(citra.shape[0], y + h + tepi)
    potongan = citra[y0:y1, x0:x1]
    dalam = np.zeros(potongan.shape[:2], np.uint8)
    cv2.drawContours(dalam, [kontur], -1, 255, cv2.FILLED, offset=(-x0, -y0))
    inti = cv2.erode(dalam, np.ones((max(3, max(w, h) // 6),) * 2, np.uint8))
    sekitar = cv2.dilate(dalam, np.ones((max(3, max(w, h) // 10),) * 2, np.uint8))
    gc = np.full(dalam.shape, cv2.GC_BGD, np.uint8)
    gc[sekitar > 0] = cv2.GC_PR_BGD
    gc[dalam > 0] = cv2.GC_PR_FGD
    gc[inti > 0] = cv2.GC_FGD
    try:
        cv2.grabCut(potongan, gc, None, np.zeros((1, 65)), np.zeros((1, 65)), 4, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        return None
    topeng = np.where((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

    # Piksel pinggiran yang warnanya masih dekat dengan latar (campuran objek dan latar pada
    # foto beresolusi rendah) dibuang: jarak warnanya ke latar harus minimal separuh jarak
    # warna median objek ke latar. Tanpa ini, pinggiran biru alas dataset jagung ikut
    # menjadi ciri kelas "bukan".
    lab = cv2.cvtColor(potongan, cv2.COLOR_BGR2LAB).astype(np.float32)
    t = max(2, min(potongan.shape[:2]) // 20)
    tepi = np.concatenate([lab[:t].reshape(-1, 3), lab[-t:].reshape(-1, 3),
                           lab[:, :t].reshape(-1, 3), lab[:, -t:].reshape(-1, 3)])
    jarak = np.linalg.norm(lab - np.median(tepi, axis=0), axis=-1)
    if (inti > 0).any():
        topeng[jarak < 0.5 * float(np.median(jarak[inti > 0]))] = 0
    # Latar berwarna kuat (alas biru dataset jagung): bayangan di sekitar objek berwarna
    # sama dengan latar tetapi lebih gelap, jadi dibuang berdasarkan kemiripan hue.
    hsv = cv2.cvtColor(potongan, cv2.COLOR_BGR2HSV)
    tepi_hsv = np.concatenate([hsv[:t].reshape(-1, 3), hsv[-t:].reshape(-1, 3),
                               hsv[:, :t].reshape(-1, 3), hsv[:, -t:].reshape(-1, 3)])
    hue_latar, saturasi_latar = np.median(tepi_hsv[:, 0]), np.median(tepi_hsv[:, 1])
    if saturasi_latar > 50:
        selisih_hue = np.abs(hsv[..., 0].astype(np.int16) - int(hue_latar))
        selisih_hue = np.minimum(selisih_hue, 180 - selisih_hue)
        topeng[(selisih_hue < 15) & (hsv[..., 1] > 30)] = 0
    topeng = cv2.morphologyEx(topeng, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    kontur_baru, _ = cv2.findContours(topeng, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not kontur_baru:
        return None
    terluas = max(kontur_baru, key=cv2.contourArea)
    return potongan, terluas


def stiker_dari_kontur(citra, kontur):
    """Potong objek beserta topengnya; latar di luar kontur dijadikan transparan."""
    hasil = rapikan_topeng(citra, kontur)
    if hasil is None:
        return None
    potongan, kontur = hasil
    x, y, w, h = cv2.boundingRect(kontur)
    # Topeng yang hampir persegi panjang penuh berarti latar ikut terpotong (misalnya alas foto).
    if cv2.contourArea(kontur) > 0.93 * w * h:
        return None
    topeng = np.zeros(potongan.shape[:2], np.uint8)
    cv2.drawContours(topeng, [kontur], -1, 255, cv2.FILLED)
    bgra = cv2.cvtColor(potongan, cv2.COLOR_BGR2BGRA)
    bgra[..., 3] = topeng
    return kecilkan(bgra[y:y + h, x:x + w], SISI_STIKER_MAKS)


def satu_objek(citra, luas_min=0.02, luas_maks=0.7):
    """Ambil objek tunggal dari foto berlatar polos. None bila foto tidak memenuhi syarat."""
    if not latar_polos(citra):
        return None
    kontur = kontur_tidak_di_tepi(pp.ke_biner_beda_latar(citra))
    if not kontur:
        return None
    luas_citra = citra.shape[0] * citra.shape[1]
    utama = kontur[0]
    luas = cv2.contourArea(utama)
    if not luas_min <= luas / luas_citra <= luas_maks:
        return None
    if len(kontur) > 1 and cv2.contourArea(kontur[1]) > 0.15 * luas:
        return None  # lebih dari satu objek besar
    soliditas = luas / max(cv2.contourArea(cv2.convexHull(utama)), 1)
    if soliditas < 0.85:
        return None
    return stiker_dari_kontur(citra, utama)


def banyak_objek(citra, maks):
    """Foto berisi banyak butir terpisah (biji kopi): setiap butir menjadi satu stiker."""
    kontur = kontur_tidak_di_tepi(pp.ke_biner_beda_latar(citra))
    if len(kontur) < 3:
        return []
    median = np.median([cv2.contourArea(k) for k in kontur[:60]])
    hasil = []
    for k in kontur:
        luas = cv2.contourArea(k)
        if 0.6 * median <= luas <= 1.6 * median and luas / cv2.contourArea(cv2.convexHull(k)) > 0.9:
            stiker = stiker_dari_kontur(citra, k)
            if stiker is not None:
                hasil.append(stiker)
        if len(hasil) >= maks:
            break
    return hasil


def daftar_foto_batu():
    for path in sorted((FOLDER_SUMBER / "batuan").rglob("*")):
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            citra = baca(path)
            if citra is not None:
                yield str(path.relative_to(FOLDER_SUMBER)), kecilkan(citra, 800)


def daftar_parquet(folder):
    for path in sorted((FOLDER_SUMBER / folder).glob("*.parquet")):
        for i, citra in baca_parquet(path):
            yield f"{folder}/{path.name}#{i}", kecilkan(citra, 800)


def daftar_almond():
    for path in sorted((FOLDER_SUMBER / "almond").rglob("*")):
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            citra = baca(path)
            if citra is not None:
                yield f"almond/{path.relative_to(FOLDER_SUMBER / 'almond').as_posix()}", kecilkan(citra, 800)


# Median saturasi (HSV OpenCV) biji yang dianggap kuning/oranye. Benih ketan di dataset
# penelitian bersaturasi median 48-125 (persentil 5-95), biji jagung kuning EfficientMaize >= 130.
SATURASI_MIN_JAGUNG_KUNING = 130


def jagung_kuning(stiker):
    piksel = cv2.cvtColor(stiker[..., :3], cv2.COLOR_BGR2HSV)[stiker[..., 3] > 127]
    return len(piksel) > 0 and np.median(piksel[:, 1]) >= SATURASI_MIN_JAGUNG_KUNING


SYARAT_KATEGORI = {"jagung_lain": jagung_kuning}


def kumpulkan(kategori, sumber, maks, rng, satu_per_foto=True, peluang=1.0):
    """Ambil stiker dari foto yang lolos syarat, lalu pilih acak sebanyak `maks`.

    Untuk dataset yang sangat besar hanya sebagian foto (dipilih acak dengan `peluang`)
    yang diperiksa, karena GrabCut lambat dan jumlah yang dibutuhkan jauh lebih sedikit.
    """
    kandidat = []
    for asal, citra in sumber:
        if rng.random() >= peluang:
            continue
        if satu_per_foto:
            stiker = satu_objek(citra)
            if stiker is not None and SYARAT_KATEGORI.get(kategori, lambda _: True)(stiker):
                kandidat.append((asal, stiker))
        else:
            for j, stiker in enumerate(banyak_objek(citra, 3)):
                kandidat.append((f"{asal}#butir{j}", stiker))
    print(f"{kategori}: {len(kandidat)} stiker lolos syarat")
    rng.shuffle(kandidat)
    return kandidat[:maks]


def siapkan_latar_peneliti(jumlah=300):
    """Potongan alas dari foto penelitian (tanpa benih) untuk latar tempelan.

    Potongan S x S (1.330 px) yang utuh tanpa benih hampir tidak pernah ada, karena benih
    berada di tengah foto 3.000 px. Karena itu diambil satu sudut berukuran S/2 x S/2 yang
    tidak bersentuhan dengan kotak benih (kotak dilebarkan 100 px), lalu dicerminkan 2 x 2
    menjadi S x S. Skala tekstur alas tetap sama dengan potongan asli. Disimpan 448 x 448,
    dua kali ukuran masukan model.
    """
    FOLDER_LATAR.mkdir(parents=True, exist_ok=True)
    for lama in FOLDER_LATAR.glob("*.jpg"):
        lama.unlink()
    setengah = 1330 // 2
    daftar = sorted(config.FOLDER_DATASET.glob("*/*.jpg"))
    rng = random.Random(config.RANDOM_SEED)
    rng.shuffle(daftar)
    n = 0
    for path in daftar:
        citra = pp.samakan_lebar(cv2.imread(str(path)))
        _, _, biner = pp.ke_biner(citra)
        kotak = pp.cari_kotak_benih(biner)
        if kotak is None:
            continue
        bx, by, bw, bh = kotak
        tinggi, lebar = citra.shape[:2]
        sudut = [(0, 0), (lebar - setengah, 0), (0, tinggi - setengah), (lebar - setengah, tinggi - setengah)]
        rng.shuffle(sudut)
        for x, y in sudut:
            bersinggungan = (x < bx + bw + 100 and bx - 100 < x + setengah
                             and y < by + bh + 100 and by - 100 < y + setengah)
            if not bersinggungan:
                p = citra[y:y + setengah, x:x + setengah]
                ubin = np.vstack([np.hstack([p, p[:, ::-1]]), np.hstack([p[::-1], p[::-1, ::-1]])])
                potongan = cv2.resize(ubin, (448, 448), interpolation=cv2.INTER_AREA)
                cv2.imwrite(str(FOLDER_LATAR / f"latar_{n:03d}.jpg"), potongan, [cv2.IMWRITE_JPEG_QUALITY, 95])
                n += 1
                break
        if n >= jumlah:
            break
    print(f"latar alas penelitian: {n} potongan")


def main():
    import sys
    # Bisa dibatasi ke beberapa kategori: python 17_siapkan_objek_bukan_ketan.py jagung_lain kedelai
    if sys.argv[1:] == ["latar"]:
        siapkan_latar_peneliti()
        return
    pilihan = set(sys.argv[1:]) or set(SUMBER)
    # (pembaca, satu objek per foto, peluang foto diperiksa)
    pembaca = {
        "batu": (daftar_foto_batu(), True, 0.5),
        "jagung_lain": (daftar_parquet("jagung_lain"), True, 1.0),
        "kedelai": (daftar_parquet("kedelai"), True, 1.0),
        "padi": (daftar_parquet("padi"), True, 0.1),
        "gandum": (daftar_parquet("gandum"), True, 1.0),
        "kopi": (daftar_parquet("kopi"), False, 1.0),
        "almond": (daftar_almond(), True, 0.6),
    }

    baris = []
    path_csv = FOLDER_OBJEK / "sumber_stiker_bukan.csv"
    if path_csv.exists() and pilihan != set(SUMBER):
        with open(path_csv, encoding="utf-8") as f:
            baris = [b for b in csv.DictReader(f) if b["kategori"] not in pilihan]
    for kategori, (sumber, satu, peluang) in pembaca.items():
        if kategori not in pilihan:
            continue
        rng = random.Random(f"{config.RANDOM_SEED}-{kategori}")
        dataset, lisensi, maks = SUMBER[kategori]
        folder = FOLDER_STIKER / kategori
        folder.mkdir(parents=True, exist_ok=True)
        for lama in folder.glob("*.png"):
            lama.unlink()
        for n, (asal, stiker) in enumerate(kumpulkan(kategori, sumber, maks, rng, satu, peluang), 1):
            nama = f"{kategori}_{n:04d}.png"
            cv2.imwrite(str(folder / nama), stiker)
            baris.append({"kategori": kategori, "berkas": nama, "dataset": dataset,
                          "lisensi": lisensi, "asal": asal})

    with open(FOLDER_OBJEK / "sumber_stiker_bukan.csv", "w", newline="", encoding="utf-8") as f:
        penulis = csv.DictWriter(f, fieldnames=["kategori", "berkas", "dataset", "lisensi", "asal"])
        penulis.writeheader()
        penulis.writerows(baris)
    print(f"total stiker: {len(baris)}")

    siapkan_latar_peneliti()


if __name__ == "__main__":
    main()
