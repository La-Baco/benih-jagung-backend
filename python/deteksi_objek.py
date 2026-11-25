"""Alur tiga tahap untuk satu foto: deteksi objek, penyaring jenis, lalu kelayakan.

1. Deteksi objek (OpenCV): objek dipisah dari latar dengan ke_biner_beda_latar(), lalu
   setiap kontur yang tidak menyentuh tepi citra menjadi satu objek dengan bounding box
   dari cv2.boundingRect.
2. Penyaring (Custom CNN, 19_latih_penyaring.py): apakah objek itu jagung ketan putih.
   Objek dengan peluang < 0,5 dilaporkan sebagai "Bukan Jagung Ketan Putih" dan tidak
   dinilai kelayakannya. Ini yang mencegah kerikil putih dinilai "Layak".
3. Kelayakan (model penelitian S3): hanya untuk objek yang lolos tahap 2.

Untuk foto satu benih di atas alas penelitian, potongan yang masuk ke model kelayakan sama
dengan prapemrosesan Subbab 3.6: kotak benih diambil dari ke_biner() bila ada kontur Otsu
yang menempati tempat yang sama (IoU >= 0,5). Jadi hasil kelayakan untuk foto seperti itu
tidak berubah dibanding sebelum tahap penyaring ditambahkan.
"""

import math

import cv2
import numpy as np

import config
import prapemrosesan as pp

KETAN = "Jagung Ketan Putih"
BUKAN = "Bukan Jagung Ketan Putih"


def _iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    lebar = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    tinggi = max(0, min(ay + ah, by + bh) - max(ay, by))
    irisan = lebar * tinggi
    return irisan / float(aw * ah + bw * bh - irisan)


def cari_objek(citra, sisi_min=None, sisi_maks=None):
    """Kontur objek (tidak menyentuh tepi) dari yang terluas, paling banyak JUMLAH_MAKS_OBJEK."""
    sisi_min = sisi_min or config.SISI_MIN_OBJEK
    biner, jarak = pp.ke_biner_beda_latar(citra, dengan_jarak=True)
    tinggi, lebar = biner.shape
    # Closing menyatukan potongan satu objek yang terpisah karena sebagian warnanya mirip alas
    # (misalnya batu berbintik abu-abu), supaya satu objek tidak dilaporkan sebagai beberapa kotak.
    ukuran = max(3, round(config.KERNEL_PENUTUP_OBJEK * lebar / config.LEBAR_ACUAN)) | 1
    tertutup = cv2.morphologyEx(biner, cv2.MORPH_CLOSE, np.ones((ukuran, ukuran), np.uint8))
    kontur, _ = cv2.findContours(tertutup, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hasil = []
    for k in kontur:
        x, y, w, h = cv2.boundingRect(k)
        if x == 0 or y == 0 or x + w == lebar or y + h == tinggi:
            continue
        if max(w, h) < sisi_min or (sisi_maks and max(w, h) > sisi_maks):
            continue
        # Objek harus cukup berbeda warna dari alas (lihat config.JARAK_WARNA_MIN_OBJEK).
        topeng = np.zeros((h, w), np.uint8)
        cv2.drawContours(topeng, [k], -1, 255, cv2.FILLED, offset=(-x, -y))
        if np.median(jarak[y:y + h, x:x + w][topeng > 0]) < config.JARAK_WARNA_MIN_OBJEK:
            continue
        hasil.append(k)

    # Kotak yang sebagian besar (>= 70 %) berada di dalam kotak objek lain yang lebih besar
    # adalah bagian objek itu (misalnya bercak di tengah batu), bukan objek tersendiri.
    terpilih = []
    for k in sorted(hasil, key=cv2.contourArea, reverse=True):
        x, y, w, h = cv2.boundingRect(k)
        di_dalam = False
        for j in terpilih:
            bx, by, bw, bh = cv2.boundingRect(j)
            irisan = max(0, min(x + w, bx + bw) - max(x, bx)) * max(0, min(y + h, by + bh) - max(y, by))
            if irisan >= 0.7 * w * h:
                di_dalam = True
                break
        if not di_dalam:
            terpilih.append(k)
    return terpilih[:config.JUMLAH_MAKS_OBJEK], biner


def _kotak_otsu(citra):
    _, _, biner = pp.ke_biner(citra)
    kontur, _ = cv2.findContours(biner, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return [cv2.boundingRect(k) for k in kontur]


def _skor(peluang):
    """Persen kepercayaan dipotong ke bawah 2 desimal (sama seperti /predict sebelumnya)."""
    return math.floor(round(peluang * 100 * 100, 6)) / 100


def analisis(citra, model_penyaring, model_kelayakan, sisi, sisi_min=None, sisi_maks=None):
    """Kembalikan daftar objek: kotak (piksel), jenis, peluang, dan hasil kelayakan.

    `citra` sudah berskala lebar acuan (samakan_lebar atau samakan_skala_frame).
    """
    daftar_kontur, biner = cari_objek(citra, sisi_min, sisi_maks)
    if not daftar_kontur:
        return []

    kotak = [cv2.boundingRect(k) for k in daftar_kontur]
    kotak_otsu = _kotak_otsu(citra)

    # Bila ada lebih dari satu objek, objek lain di dalam potongan ditutup warna latar,
    # karena kedua model dilatih dengan satu objek per potongan.
    if len(daftar_kontur) > 1:
        warna_latar = np.median(citra[::8, ::8][biner[::8, ::8] == 0], axis=0).astype(np.uint8)
        topeng_semua = []
        for k in daftar_kontur:
            topeng = np.zeros(biner.shape, np.uint8)
            cv2.drawContours(topeng, [k], -1, 255, cv2.FILLED)
            topeng_semua.append(cv2.dilate(topeng, np.ones((31, 31), np.uint8)))

    potongan_penyaring, potongan_kelayakan = [], []
    for i, kt in enumerate(kotak):
        bersih = citra
        if len(daftar_kontur) > 1:
            bersih = citra.copy()
            for j, topeng in enumerate(topeng_semua):
                if j != i:
                    bersih[topeng > 0] = warna_latar
        potongan_penyaring.append(pp.ke_masukan_model(pp.ubah_ukuran(pp.potong_persegi(bersih, kt, sisi))))
        # Kotak Otsu dipakai untuk model kelayakan bila menempati tempat yang sama (lihat docstring modul).
        terbaik = max(kotak_otsu, key=lambda o: _iou(o, kt), default=None)
        kt_kelayakan = terbaik if terbaik is not None and _iou(terbaik, kt) >= 0.5 else kt
        potongan_kelayakan.append(pp.ke_masukan_model(pp.ubah_ukuran(pp.potong_persegi(bersih, kt_kelayakan, sisi))))

    peluang_ketan = model_penyaring(np.stack(potongan_penyaring), training=False).numpy().ravel()
    indeks_ketan = [i for i, p in enumerate(peluang_ketan) if p >= 0.5]
    peluang_layak = {}
    if indeks_ketan:
        keluaran = model_kelayakan(np.stack([potongan_kelayakan[i] for i in indeks_ketan]), training=False)
        peluang_layak = dict(zip(indeks_ketan, keluaran.numpy().ravel()))

    hasil = []
    for i, (x, y, w, h) in enumerate(kotak):
        p_ketan = float(peluang_ketan[i])
        objek = {"x": x, "y": y, "w": w, "h": h, "peluang_ketan": round(p_ketan, 4)}
        if i in peluang_layak:
            p = float(peluang_layak[i])
            objek.update(jenis=KETAN, skor_jenis=_skor(p_ketan), peluang_layak=round(p, 4),
                         prediksi="Layak" if p >= 0.5 else "Tidak Layak",
                         skor_kepercayaan=_skor(p if p >= 0.5 else 1 - p))
        else:
            # Persamaan 3-3 diterapkan pada keluaran penyaring: kepercayaan bahwa objek BUKAN jagung ketan putih.
            objek.update(jenis=BUKAN, skor_jenis=_skor(1 - p_ketan), peluang_layak=None,
                         prediksi=BUKAN, skor_kepercayaan=_skor(1 - p_ketan))
        hasil.append(objek)
    return hasil


def gambar_kotak(citra, daftar_objek):
    """Gambar bounding box dan label di atas citra (untuk bukti dan lampiran)."""
    hasil = citra.copy()
    tebal = max(2, citra.shape[1] // 300)
    warna = {"Layak": (60, 160, 40), "Tidak Layak": (40, 40, 200), BUKAN: (20, 140, 230)}
    for o in daftar_objek:
        x, y, w, h = o["x"], o["y"], o["w"], o["h"]
        c = warna[o["prediksi"]]
        cv2.rectangle(hasil, (x, y), (x + w, y + h), c, tebal)
        teks = f"{o['prediksi']} {o['skor_kepercayaan']:.1f}%"
        skala = citra.shape[1] / 1500
        (tw, th), _ = cv2.getTextSize(teks, cv2.FONT_HERSHEY_SIMPLEX, skala, tebal)
        y_teks = y - 10 if y - th - 20 > 0 else y + h + th + 10
        cv2.rectangle(hasil, (x, y_teks - th - 8), (x + tw + 8, y_teks + 6), c, cv2.FILLED)
        cv2.putText(hasil, teks, (x + 4, y_teks), cv2.FONT_HERSHEY_SIMPLEX, skala, (255, 255, 255), tebal)
    return hasil
