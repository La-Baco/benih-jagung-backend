"""Fungsi prapemrosesan citra (Subbab 3.6).

Modul ini dipakai saat membentuk dataset dan di layanan Flask, jadi citra
unggahan diproses dengan langkah yang sama persis seperti citra latih.
"""

import cv2
import numpy as np

import config


def samakan_lebar(citra):
    """Ubah lebar citra ke LEBAR_ACUAN supaya ukuran piksel benih sebanding.

    Citra dataset sudah 3000 piksel, jadi fungsi ini hanya berpengaruh pada
    unggahan dengan resolusi berbeda.
    """
    tinggi, lebar = citra.shape[:2]
    if lebar == config.LEBAR_ACUAN:
        return citra
    skala = config.LEBAR_ACUAN / lebar
    return cv2.resize(citra, (config.LEBAR_ACUAN, round(tinggi * skala)), interpolation=cv2.INTER_AREA)


def ke_biner(citra_bgr):
    abu = cv2.cvtColor(citra_bgr, cv2.COLOR_BGR2GRAY)
    ambang, biner = cv2.threshold(abu, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Opening memutus garis tipis serat alas yang ikut putih dan menempel ke benih.
    kernel = np.ones((config.KERNEL_OPENING, config.KERNEL_OPENING), np.uint8)
    biner = cv2.morphologyEx(biner, cv2.MORPH_OPEN, kernel)
    return abu, ambang, biner


def cari_kotak_benih(biner):
    """Kembalikan (x, y, w, h) kontur benih, atau None bila tidak ditemukan.

    Kontur yang menyentuh tepi citra dilewati karena benih selalu diletakkan
    di tengah (Tabel 3.3), sedangkan area terang akibat pantulan cahaya pada
    alas biasanya melebar sampai tepi.
    """
    tinggi, lebar = biner.shape
    kontur, _ = cv2.findContours(biner, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    kandidat = []
    for k in kontur:
        x, y, w, h = cv2.boundingRect(k)
        if x == 0 or y == 0 or x + w == lebar or y + h == tinggi:
            continue
        kandidat.append(k)

    if not kandidat:
        return None
    terluas = max(kandidat, key=cv2.contourArea)
    return cv2.boundingRect(terluas)


def cari_semua_kontur_benih(biner):
    """Semua kontur yang ukurannya masuk akal sebagai satu butir benih (mode kamera).

    Dipakai saat beberapa benih difoto sekaligus. Batas ukuran diambil dari
    rentang max(w, h) benih di dataset (504-1230 px pada lebar 3000 px), jadi
    kotoran kecil dan benih yang saling menempel tidak dianggap satu benih.
    """
    tinggi, lebar = biner.shape
    kontur, _ = cv2.findContours(biner, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    hasil = []
    for k in kontur:
        x, y, w, h = cv2.boundingRect(k)
        if x == 0 or y == 0 or x + w == lebar or y + h == tinggi:
            continue
        if config.SISI_MIN_DETEKSI <= max(w, h) <= config.SISI_MAKS_DETEKSI:
            hasil.append(k)
    return hasil


def mirip_benih(citra_hsv, kontur):
    """Saring kontur yang bukan benih di mode kamera, misalnya benda berwarna atau kertas putih.

    Warna rata-rata di dalam kontur harus dalam rentang warna benih dataset, dan
    cincin selebar 30 px di sekelilingnya harus gelap seperti alas hitam.
    """
    x, y, w, h = cv2.boundingRect(kontur)
    tepi = 31
    x0, y0 = max(0, x - tepi), max(0, y - tepi)
    x1, y1 = min(citra_hsv.shape[1], x + w + tepi), min(citra_hsv.shape[0], y + h + tepi)
    potongan = citra_hsv[y0:y1, x0:x1]

    topeng = np.zeros(potongan.shape[:2], np.uint8)
    cv2.drawContours(topeng, [kontur], -1, 255, cv2.FILLED, offset=(-x0, -y0))
    cincin = (cv2.dilate(topeng, np.ones((61, 61), np.uint8)) > 0) & (topeng == 0)

    hue, saturasi, value = [float(potongan[..., i][topeng > 0].mean()) for i in range(3)]
    value_alas = float(potongan[..., 2][cincin].mean())
    return (config.HUE_BENIH[0] <= hue <= config.HUE_BENIH[1]
            and config.SATURASI_BENIH[0] <= saturasi <= config.SATURASI_BENIH[1]
            and value >= config.VALUE_MIN_BENIH
            and value_alas <= config.VALUE_MAKS_ALAS)


def potong_persegi(citra_bgr, kotak, sisi):
    """Potong persegi berukuran sisi x sisi yang berpusat di tengah kotak benih."""
    x, y, w, h = kotak
    pusat_x = x + w // 2
    pusat_y = y + h // 2
    kiri = pusat_x - sisi // 2
    atas = pusat_y - sisi // 2

    # Kalau benih dekat tepi, citra diberi bingkai dulu supaya potongan tetap utuh.
    tinggi, lebar = citra_bgr.shape[:2]
    tambah = max(0, -kiri, -atas, kiri + sisi - lebar, atas + sisi - tinggi)
    if tambah > 0:
        citra_bgr = cv2.copyMakeBorder(citra_bgr, tambah, tambah, tambah, tambah, cv2.BORDER_REPLICATE)
        kiri += tambah
        atas += tambah

    return citra_bgr[atas:atas + sisi, kiri:kiri + sisi]


def ubah_ukuran(potongan):
    return cv2.resize(potongan, (config.UKURAN_CITRA, config.UKURAN_CITRA), interpolation=cv2.INTER_AREA)


def proses_citra(citra_bgr, sisi):
    """Citra mentah -> potongan benih 224 x 224 (masih BGR, nilai 0-255)."""
    citra_bgr = samakan_lebar(citra_bgr)
    _, _, biner = ke_biner(citra_bgr)
    kotak = cari_kotak_benih(biner)
    if kotak is None:
        return None
    return ubah_ukuran(potong_persegi(citra_bgr, kotak, sisi))


def ke_masukan_model(potongan_bgr):
    """Ubah ke RGB lalu normalisasi x/255 (Persamaan 2-5).

    Saat pelatihan, PNG hasil prapemrosesan dibaca Keras sebagai RGB dan
    dinormalisasi dengan Rescaling(1/255), jadi hasilnya sama dengan fungsi ini.
    """
    rgb = cv2.cvtColor(potongan_bgr, cv2.COLOR_BGR2RGB)
    return rgb.astype(np.float32) / 255.0
