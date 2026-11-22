"""Tahap 6: pembagian dataset 70:15:15 secara acak berstrata (Subbab 3.7).

Setiap kelas diacak terpisah dengan random seed 42, lalu dibagi menjadi
350 latih, 75 validasi, dan 75 uji. Satu berkas mewakili satu butir benih,
jadi pengecekan di akhir memastikan tidak ada berkas yang sama di dua bagian.
"""

import csv
import hashlib
import random
import shutil

import config

FOLDER_BUKTI = config.FOLDER_BUKTI / "03_pembagian_dataset"
FOLDER_SEMUA = config.FOLDER_OLAH / "semua"
BAGIAN = list(config.PROPORSI_BAGIAN)


def md5(path):
    return hashlib.md5(path.read_bytes()).hexdigest()


def bagi_per_kelas(kelas):
    berkas = sorted(p.name for p in (FOLDER_SEMUA / kelas).glob("*.png"))
    random.Random(config.RANDOM_SEED).shuffle(berkas)

    # Validasi dan uji dibulatkan, sisanya masuk data latih, jadi tidak ada citra yang tertinggal.
    jumlah_per_bagian = {
        "validasi": round(len(berkas) * config.PROPORSI_BAGIAN["validasi"]),
        "uji": round(len(berkas) * config.PROPORSI_BAGIAN["uji"]),
    }
    jumlah_per_bagian = {"latih": len(berkas) - sum(jumlah_per_bagian.values()), **jumlah_per_bagian}

    hasil = {}
    mulai = 0
    for bagian, jumlah in jumlah_per_bagian.items():
        hasil[bagian] = sorted(berkas[mulai:mulai + jumlah])
        mulai += jumlah
    return hasil


def cek_kebocoran(pembagian):
    baris = []
    aman = True

    for i, a in enumerate(BAGIAN):
        for b in BAGIAN[i + 1:]:
            sama = set(pembagian[a]) & set(pembagian[b])
            baris.append(f"Nama berkas sama di {a} dan {b}: {len(sama)}")
            aman = aman and not sama

    # Cek isi berkas asli juga, untuk memastikan tidak ada foto yang tersimpan dua kali.
    hash_asli = {}
    for folder in config.KELAS_ASLI:
        for path in (config.FOLDER_DATASET / folder).glob("*.jpg"):
            hash_asli.setdefault(md5(path), []).append(path.name)
    kembar = [nama for nama in hash_asli.values() if len(nama) > 1]
    baris.append(f"Citra asli dengan isi identik: {len(kembar)}")
    aman = aman and not kembar
    for nama in kembar:
        baris.append("  " + ", ".join(nama))

    baris.append("HASIL: aman, tidak ada benih yang muncul di lebih dari satu bagian" if aman
                 else "HASIL: ADA KEBOCORAN, periksa daftar di atas")
    return "\n".join(baris)


def main():
    FOLDER_BUKTI.mkdir(parents=True, exist_ok=True)

    for bagian in BAGIAN:
        if (config.FOLDER_OLAH / bagian).exists():
            shutil.rmtree(config.FOLDER_OLAH / bagian)

    semua_baris = []
    pembagian = {b: [] for b in BAGIAN}
    for kelas in config.NAMA_KELAS:
        label = config.NAMA_KELAS.index(kelas)
        for bagian, daftar in bagi_per_kelas(kelas).items():
            tujuan = config.FOLDER_OLAH / bagian / kelas
            tujuan.mkdir(parents=True, exist_ok=True)
            for nama in daftar:
                shutil.copy2(FOLDER_SEMUA / kelas / nama, tujuan / nama)
                semua_baris.append({"berkas": nama, "kelas": kelas, "label": label, "bagian": bagian})
                pembagian[bagian].append(nama)

    with open(FOLDER_BUKTI / "pembagian_dataset.csv", "w", newline="", encoding="utf-8") as f:
        penulis = csv.DictWriter(f, fieldnames=["berkas", "kelas", "label", "bagian"])
        penulis.writeheader()
        penulis.writerows(semua_baris)

    tabel = [f"{'Bagian':<10}{'Layak':>8}{'Tidak layak':>13}{'Total':>8}"]
    for bagian in BAGIAN:
        layak = len(list((config.FOLDER_OLAH / bagian / "layak").glob("*.png")))
        tidak = len(list((config.FOLDER_OLAH / bagian / "tidak_layak").glob("*.png")))
        tabel.append(f"{bagian:<10}{layak:>8}{tidak:>13}{layak + tidak:>8}")
    tabel.append(f"random seed = {config.RANDOM_SEED}")

    laporan = "\n".join(tabel) + "\n\n" + cek_kebocoran(pembagian)
    print(laporan)
    (FOLDER_BUKTI / "cek_pembagian.txt").write_text(laporan + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
