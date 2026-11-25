"""Tahap penyaring objek (4/4): evaluasi model penyaring dan alur tiga tahap.

Bagian A. Model penyaring pada data uji dataset_penyaring (sekali, setelah pelatihan selesai):
          confusion matrix, akurasi, presisi, recall, F1 (kelas positif = jagung ketan putih),
          dirinci per kategori objek dan per jenis latar.
Bagian B. Kategori yang tidak pernah dilatih (almond): berapa persen ditolak sebagai bukan.
Bagian C. Alur lengkap pada 150 foto uji asli penelitian (3000 x 3000): apakah setiap foto tetap
          terdeteksi satu objek, lolos penyaring, dan hasil kelayakannya sama dengan alur lama.
Bagian D. Alur lengkap pada foto susunan di atas alas penelitian: benih uji diganti batu/biji lain
          (kasus "kerikil dinilai Layak"), dan foto berisi benih + dua benda lain sekaligus.
          Hasilnya disimpan sebagai gambar dengan bounding box. Foto ini disusun dari foto
          penelitian: benih ditutup tambalan alas dari sudut foto yang sama (tambalan ini kadang
          tampak sebagai persegi sedikit lebih gelap), lalu stiker objek uji ditempel di atasnya.

    python 20_evaluasi_penyaring.py
"""

import csv
import importlib
import json
import random

import cv2
import keras
import matplotlib.pyplot as plt
import numpy as np

import config
import deteksi_objek as do
import prapemrosesan as pp

evaluasi = importlib.import_module("05_evaluasi")

FOLDER_DATA = config.FOLDER_PROYEK / "dataset_penyaring"
FOLDER_BUKTI = config.FOLDER_BUKTI / "12_penyaring_objek" / "evaluasi"
NAMA_TAMPIL = {"jagung_ketan_putih": "Jagung ketan putih", "bukan_jagung_ketan_putih": "Bukan"}


def baca_daftar():
    with open(FOLDER_DATA / "daftar_citra.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def muat_citra(baris):
    path = FOLDER_DATA / baris["bagian"] / baris["kelas"] / baris["berkas"]
    rgb = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB)
    return rgb.astype(np.float32) / 255.0


def prediksi_bertahap(model, daftar_baris, batch=64):
    hasil = []
    for i in range(0, len(daftar_baris), batch):
        x = np.stack([muat_citra(b) for b in daftar_baris[i:i + batch]])
        hasil.append(model(x, training=False).numpy().ravel())
    return np.concatenate(hasil) if hasil else np.array([])


def gambar_confusion_matrix(m, judul, tujuan):
    matriks = np.array([[m["tp"], m["fn"]], [m["fp"], m["tn"]]])
    fig, ax = plt.subplots(figsize=(5.4, 4.5))
    ax.imshow(matriks, cmap="Blues")
    for (i, j), nilai in np.ndenumerate(matriks):
        ax.text(j, i, str(nilai), ha="center", va="center", fontsize=16,
                color="white" if nilai > matriks.max() / 2 else "black")
    ax.set_xticks([0, 1], ["Prediksi\njagung ketan putih", "Prediksi\nbukan"])
    ax.set_yticks([0, 1], ["Jagung ketan putih", "Bukan"])
    ax.set_ylabel("Label sebenarnya")
    ax.set_title(judul)
    fig.savefig(tujuan, dpi=150, bbox_inches="tight")
    plt.close(fig)


def bagian_a_b(penyaring, daftar):
    uji = [b for b in daftar if b["bagian"] == "uji"]
    label = np.array([config.NAMA_KELAS_PENYARING.index(b["kelas"]) for b in uji])
    peluang = prediksi_bertahap(penyaring, uji)
    m = evaluasi.hitung_metrik(label, peluang)
    gambar_confusion_matrix(m, "Confusion matrix penyaring (data uji)", FOLDER_BUKTI / "confusion_matrix_uji.png")

    rincian = []
    kunci = sorted({(b["kelas"], b["kategori"], b["latar"]) for b in uji})
    for kelas, kategori, latar in kunci:
        idx = [i for i, b in enumerate(uji) if (b["kelas"], b["kategori"], b["latar"]) == (kelas, kategori, latar)]
        benar = int(np.sum(m["prediksi"][idx] == label[idx]))
        rincian.append({"kelas": kelas, "kategori": kategori, "latar": latar, "jumlah": len(idx),
                        "benar": benar, "persen_benar": round(100 * benar / len(idx), 2)})

    salah = [{"berkas": f"{b['kelas']}/{b['berkas']}", "kategori": b["kategori"], "latar": b["latar"],
              "peluang_ketan": round(float(p), 4)}
             for b, p, y, yhat in zip(uji, peluang, label, m["prediksi"]) if y != yhat]

    baru = [b for b in daftar if b["bagian"] == "uji_kategori_baru"]
    p_baru = prediksi_bertahap(penyaring, baru)
    ditolak = int(np.sum(p_baru < 0.5))
    hasil_b = {"kategori": "almond (tidak dipakai saat pelatihan)", "jumlah": len(baru),
               "ditolak_sebagai_bukan": ditolak, "persen_ditolak": round(100 * ditolak / max(len(baru), 1), 2)}

    ringkas = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items() if k != "prediksi"}
    ringkas["jumlah_uji"] = len(uji)
    return ringkas, rincian, salah, hasil_b


def bagian_c(penyaring, kelayakan, sisi):
    """Foto uji asli penelitian melalui alur tiga tahap, dibandingkan dengan alur lama."""
    baris = []
    nama_folder = {v: k for k, v in config.KELAS_ASLI.items()}
    for kelas in ["layak", "tidak_layak"]:
        for path_olah in sorted((config.FOLDER_OLAH / "uji" / kelas).glob("*.png")):
            path = config.FOLDER_DATASET / nama_folder[kelas] / (path_olah.stem + ".jpg")
            citra = pp.samakan_lebar(cv2.imread(str(path)))
            objek = do.analisis(citra, penyaring, kelayakan, sisi)
            lama = pp.proses_citra(citra, sisi)
            p_lama = float(kelayakan(pp.ke_masukan_model(lama)[None], training=False).numpy()[0][0])
            utama = objek[0] if objek else None
            baris.append({
                "berkas": path.name, "label": "Layak" if kelas == "layak" else "Tidak Layak",
                "jumlah_objek": len(objek),
                "jenis": utama["jenis"] if utama else "-",
                "peluang_ketan": utama["peluang_ketan"] if utama else None,
                "prediksi_baru": utama["prediksi"] if utama else "-",
                "prediksi_lama": "Layak" if p_lama >= 0.5 else "Tidak Layak",
                "peluang_layak_baru": utama["peluang_layak"] if utama else None,
                "peluang_layak_lama": round(p_lama, 4),
            })
    n = len(baris)
    ringkas = {
        "jumlah_foto": n,
        "tepat_satu_objek": sum(b["jumlah_objek"] == 1 for b in baris),
        "lolos_penyaring": sum(b["jenis"] == do.KETAN for b in baris),
        "prediksi_sama_dengan_alur_lama": sum(b["prediksi_baru"] == b["prediksi_lama"] for b in baris),
        "benar_alur_lama": sum(b["prediksi_lama"] == b["label"] for b in baris),
        "benar_alur_baru": sum(b["prediksi_baru"] == b["label"] for b in baris),
    }
    return ringkas, baris


def foto_tanpa_benih(citra):
    """Hapus benih dari foto penelitian dengan menutupnya memakai potongan alas dari sudut foto yang sama."""
    _, _, biner = pp.ke_biner(citra)
    x, y, w, h = pp.cari_kotak_benih(biner)
    tepi = 80
    x0, y0, x1, y1 = max(0, x - tepi), max(0, y - tepi), min(citra.shape[1], x + w + tepi), min(citra.shape[0], y + h + tepi)
    tinggi, lebar = y1 - y0, x1 - x0
    hasil = citra.copy()
    for sx, sy in [(0, 0), (citra.shape[1] - lebar, 0), (0, citra.shape[0] - tinggi),
                   (citra.shape[1] - lebar, citra.shape[0] - tinggi)]:
        if sx + lebar <= x0 or sx >= x1 or sy + tinggi <= y0 or sy >= y1:
            tambalan = citra[sy:sy + tinggi, sx:sx + lebar].astype(np.float32)
            alfa = np.zeros((tinggi, lebar), np.float32)
            cv2.rectangle(alfa, (tepi // 2, tepi // 2), (lebar - tepi // 2, tinggi - tepi // 2), 1.0, cv2.FILLED)
            alfa = cv2.GaussianBlur(alfa, (0, 0), tepi / 4)[..., None]
            asal = hasil[y0:y1, x0:x1].astype(np.float32)
            hasil[y0:y1, x0:x1] = (tambalan * alfa + asal * (1 - alfa)).astype(np.uint8)
            return hasil
    return None


def tempel_stiker(citra, stiker, pusat, sisi_panjang, rng):
    stiker = cv2.rotate(stiker, rng.choice([cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE])) \
        if rng.random() < 0.75 else stiker
    skala = sisi_panjang / max(stiker.shape[:2])
    stiker = cv2.resize(stiker, None, fx=skala, fy=skala, interpolation=cv2.INTER_CUBIC)
    tinggi, lebar = stiker.shape[:2]
    x, y = pusat[0] - lebar // 2, pusat[1] - tinggi // 2
    alfa = cv2.GaussianBlur(stiker[..., 3].astype(np.float32) / 255, (5, 5), 0)[..., None]
    area = citra[y:y + tinggi, x:x + lebar].astype(np.float32)
    citra[y:y + tinggi, x:x + lebar] = (stiker[..., :3] * alfa + area * (1 - alfa)).astype(np.uint8)


def bagian_d(penyaring, kelayakan, sisi, daftar):
    """Foto susunan: (1) benih diganti objek lain, (2) benih asli + dua objek lain di sekitarnya."""
    rng = random.Random(config.RANDOM_SEED)
    folder_contoh = FOLDER_BUKTI / "contoh_bounding_box"
    folder_contoh.mkdir(parents=True, exist_ok=True)
    stiker_uji = [b for b in daftar if b["bagian"] in ("uji", "uji_kategori_baru")
                  and b["kelas"] == config.NAMA_KELAS_PENYARING[0] and b["latar"] == "alas_penelitian"]
    nama_folder = {v: k for k, v in config.KELAS_ASLI.items()}
    foto_uji = [(kelas, p) for kelas in ["layak", "tidak_layak"]
                for p in sorted((config.FOLDER_OLAH / "uji" / kelas).glob("*.png"))]

    pengganti, campuran = [], []
    for i, b in enumerate(stiker_uji):
        kelas, path_olah = foto_uji[i % len(foto_uji)]
        citra = pp.samakan_lebar(cv2.imread(str(config.FOLDER_DATASET / nama_folder[kelas] / (path_olah.stem + ".jpg"))))
        kosong = foto_tanpa_benih(citra)
        if kosong is None:
            continue
        stiker = cv2.imread(str(config.FOLDER_PROYEK / "dataset_objek" / b["asal"]), cv2.IMREAD_UNCHANGED)
        tempel_stiker(kosong, stiker, (1500 + rng.randint(-300, 300), 1500 + rng.randint(-300, 300)),
                      rng.randint(500, 1200), rng)
        objek = do.analisis(kosong, penyaring, kelayakan, sisi)
        utama = objek[0] if objek else None
        pengganti.append({"stiker": b["asal"], "kategori": b["kategori"], "jumlah_objek": len(objek),
                          "prediksi": utama["prediksi"] if utama else "tidak terdeteksi",
                          "peluang_ketan": utama["peluang_ketan"] if utama else None})
        if i % 25 == 0:
            cv2.imwrite(str(folder_contoh / f"pengganti_{b['kategori']}_{i:03d}.jpg"),
                        cv2.resize(do.gambar_kotak(kosong, objek), (1000, 1000), interpolation=cv2.INTER_AREA),
                        [cv2.IMWRITE_JPEG_QUALITY, 90])

    # Benih asli di tengah, dua objek lain di pojok kiri atas dan kanan bawah.
    for i in range(0, len(foto_uji), 5):
        kelas, path_olah = foto_uji[i]
        citra = pp.samakan_lebar(cv2.imread(str(config.FOLDER_DATASET / nama_folder[kelas] / (path_olah.stem + ".jpg"))))
        # Hanya kategori yang dilatih; almond (belum pernah dilatih) sudah diukur di B dan D1.
        pilihan = rng.sample([b for b in stiker_uji if b["bagian"] == "uji"], 2)
        for b, pusat in zip(pilihan, [(550, 550), (2450, 2450)]):
            stiker = cv2.imread(str(config.FOLDER_PROYEK / "dataset_objek" / b["asal"]), cv2.IMREAD_UNCHANGED)
            tempel_stiker(citra, stiker, pusat, rng.randint(500, 800), rng)
        objek = do.analisis(citra, penyaring, kelayakan, sisi)
        jenis = [o["jenis"] for o in objek]
        campuran.append({"foto": path_olah.stem, "objek_lain": "+".join(b["kategori"] for b in pilihan),
                         "jumlah_objek": len(objek), "jumlah_ketan": jenis.count(do.KETAN),
                         "jumlah_bukan": jenis.count(do.BUKAN), "hasil": "; ".join(o["prediksi"] for o in objek)})
        if i % 25 == 0:
            cv2.imwrite(str(folder_contoh / f"campuran_{path_olah.stem}.jpg"),
                        cv2.resize(do.gambar_kotak(citra, objek), (1000, 1000), interpolation=cv2.INTER_AREA),
                        [cv2.IMWRITE_JPEG_QUALITY, 90])

    ringkas_pengganti = {"jumlah_foto": len(pengganti),
                         "ditolak_sebagai_bukan": sum(p["prediksi"] == do.BUKAN for p in pengganti),
                         "lolos_sebagai_ketan": sum(p["prediksi"] in ("Layak", "Tidak Layak") for p in pengganti),
                         "tidak_terdeteksi": sum(p["prediksi"] == "tidak terdeteksi" for p in pengganti)}
    per_kategori = {}
    for p in pengganti:
        k = per_kategori.setdefault(p["kategori"], {"jumlah": 0, "ditolak_sebagai_bukan": 0})
        k["jumlah"] += 1
        k["ditolak_sebagai_bukan"] += p["prediksi"] == do.BUKAN
    ringkas_pengganti["per_kategori"] = per_kategori
    ringkas_campuran = {"jumlah_foto": len(campuran),
                        "tiga_objek_terdeteksi": sum(c["jumlah_objek"] == 3 for c in campuran),
                        "tepat_1_ketan_2_bukan": sum(c["jumlah_ketan"] == 1 and c["jumlah_bukan"] == 2 for c in campuran)}
    return ringkas_pengganti, pengganti, ringkas_campuran, campuran


def tulis_csv(path, baris):
    if not baris:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        penulis = csv.DictWriter(f, fieldnames=list(baris[0]))
        penulis.writeheader()
        penulis.writerows(baris)


def main():
    FOLDER_BUKTI.mkdir(parents=True, exist_ok=True)
    penyaring = keras.models.load_model(str(config.FILE_MODEL_PENYARING))
    kelayakan = keras.models.load_model(str(config.FILE_MODEL_AKHIR))
    sisi = json.loads(config.FILE_PRAPEMROSESAN.read_text(encoding="utf-8"))["sisi_potong"]
    daftar = baca_daftar()

    metrik, rincian, salah, kategori_baru = bagian_a_b(penyaring, daftar)
    tulis_csv(FOLDER_BUKTI / "rincian_per_kategori.csv", rincian)
    tulis_csv(FOLDER_BUKTI / "salah_prediksi_uji.csv", salah)
    print("A.", json.dumps(metrik))
    print("B.", json.dumps(kategori_baru))

    ringkas_c, baris_c = bagian_c(penyaring, kelayakan, sisi)
    tulis_csv(FOLDER_BUKTI / "alur_lengkap_foto_uji_penelitian.csv", baris_c)
    print("C.", json.dumps(ringkas_c))

    ringkas_pengganti, pengganti, ringkas_campuran, campuran = bagian_d(penyaring, kelayakan, sisi, daftar)
    tulis_csv(FOLDER_BUKTI / "alur_lengkap_benih_diganti_objek_lain.csv", pengganti)
    tulis_csv(FOLDER_BUKTI / "alur_lengkap_benih_dan_objek_lain.csv", campuran)
    print("D1.", json.dumps(ringkas_pengganti))
    print("D2.", json.dumps(ringkas_campuran))

    hasil = {"A_penyaring_data_uji": metrik, "B_kategori_belum_pernah_dilatih": kategori_baru,
             "C_alur_lengkap_foto_uji_penelitian": ringkas_c,
             "D1_benih_diganti_objek_lain": ringkas_pengganti, "D2_benih_dan_objek_lain": ringkas_campuran}
    (FOLDER_BUKTI / "hasil_evaluasi.json").write_text(json.dumps(hasil, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
