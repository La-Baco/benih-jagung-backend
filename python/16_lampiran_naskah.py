"""Menyusun akhir/lampiran.tex naskah LaTeX dari berkas di folder bukti (lihat 15_gambar_naskah_besar.py).

Argumen: folder latex naskah (berisi gambar/lampiran).
"""

import csv
import re
import sys
from pathlib import Path

import config

LATEX = Path(sys.argv[1])
FOLDER = LATEX / "gambar" / "lampiran"
BUKTI = config.FOLDER_BUKTI

NAMA_SKENARIO = {"s1": "S1 (3 blok, \\asing{batch} 16)", "s2": "S2 (3 blok, \\asing{batch} 32)",
                 "s3": "S3 (4 blok, \\asing{batch} 16)", "s4": "S4 (4 blok, \\asing{batch} 32)"}
# screenshot tampilan baru (27 Nov 2026, folder "gambar aplikasi new") yang langkahnya sama dengan skenario lama
PEMBARUAN = {"android_01a_registrasi_isian.png": "hp2_registrasi.png", "android_03a_login_isian.png": "hp2_login.png",
             "android_03b_login_beranda.png": "hp2_beranda.png", "android_06a_tautan_terkirim.png": "hp2_lupa_sandi.png",
             "android_10_riwayat_petani.png": "hp2_riwayat.png"}
ASING = {"login", "logout", "website", "black", "box", "dashboard", "email", "png", "jpeg", "webp", "reset"}


def keterangan(nama):
    """'android_07b_galeri_jpeg_hasil.png' -> 'Skenario 7: galeri jpeg hasil'"""
    m = re.match(r"(?:android|web)_(\d+)([a-z]?)_(.+)\.png", nama)
    no, bagian, isi = int(m.group(1)), m.group(2), m.group(3).replace("_", " ")
    kata = []
    for k in isi.split():
        if k == "email":
            k = "e-mail"
        kata.append(f"\\asing{{{k}}}" if k in ASING or k == "e-mail" else k)
    return f"Skenario {no}{bagian}: " + " ".join(kata)


def kisi(berkas, kolom, lebar, isi=0.95):
    baris = []
    for i in range(0, len(berkas), kolom):
        sel = []
        for p in berkas[i:i + kolom]:
            baru = PEMBARUAN.get(p.name)
            gambar = f"gambar/hasil/{baru}" if baru else f"gambar/lampiran/{p.name}"
            tanda = "*" if baru else ""
            sel.append(f"\\begin{{minipage}}[t]{{{lebar}\\textwidth}}\\centering\n"
                       f"\\fbox{{\\includegraphics[width={isi}\\linewidth]{{{gambar}}}}}\\\\[2pt]\n"
                       f"{{\\footnotesize {keterangan(p.name)}{tanda}}}\n\\end{{minipage}}")
        # jarak tetap antarbaris (lingkungan center menambah jarak besar di atas dan bawah)
        baris.append("\\par\\noindent{\\centering\n" + "\\hfill\n".join(sel) + "\n\\par}\\vspace{6pt}")
    return "\n".join(baris)


def tabel_evaluasi():
    with open(BUKTI / "05_evaluasi" / "semua_skenario" / "evaluasi_semua_skenario.csv", encoding="utf-8") as f:
        data = list(csv.DictReader(f))
    label = [("jumlah_parameter", "Jumlah parameter"), ("epoch_terbaik", "\\asing{Epoch} terbaik"),
             ("akurasi_latih", "Akurasi latih"), ("loss_latih", "\\asing{Loss} latih"),
             ("akurasi_validasi", "Akurasi validasi"), ("loss_validasi", "\\asing{Loss} validasi"),
             ("uji_tp", "TP uji"), ("uji_fn", "FN uji"), ("uji_fp", "FP uji"), ("uji_tn", "TN uji"),
             ("akurasi_uji", "Akurasi uji"), ("presisi_uji", "Presisi uji"), ("recall_uji", "\\asing{Recall} uji"),
             ("f1_uji", "F1-\\asing{score} uji"), ("loss_uji", "\\asing{Loss} uji"),
             ("ece_uji", "\\asing{Expected calibration error} uji"), ("skor_rata_uji", "Rata-rata skor kepercayaan uji"),
             ("uji_skor_tampil_99_99", "Citra uji dengan skor tampil 99,99\\%"),
             ("uji_salah_dengan_skor_95", "Salah prediksi dengan skor $\\geq$ 95\\%"),
             ("selisih_akurasi_latih_uji", "Selisih akurasi latih dan uji"),
             ("rasio_loss_uji_latih", "Rasio \\asing{loss} uji terhadap latih")]
    baris = []
    for kunci, nama in label:
        nilai = []
        for d in data:
            v = d[kunci]
            if kunci == "jumlah_parameter":
                v = f"{int(v):,}".replace(",", ".")
            else:
                v = v.replace(".", ",")
            nilai.append(v)
        baris.append(f"{nama} & " + " & ".join(nilai) + " \\\\ \\hline")
    kepala = "\\rowcolor{abuheader}\\textbf{Ukuran} & \\textbf{S1} & \\textbf{S2} & \\textbf{S3} & \\textbf{S4} \\\\ \\hline"
    return ("{\\setlength{\\tabcolsep}{4bp}\\isitabel\n\\begin{longtable}{|L{134bp}|>{\\centering\\arraybackslash}p{56bp}|"
            ">{\\centering\\arraybackslash}p{56bp}|>{\\centering\\arraybackslash}p{56bp}|>{\\centering\\arraybackslash}p{56bp}|}\n"
            "\\hline\n" + kepala + "\n\\endfirsthead\n\\hline\n" + kepala + "\n\\endhead\n" + "\n".join(baris) +
            "\n\\end{longtable}}\n\\ketlampiran{Sumber: bukti/05\\_evaluasi/semua\\_skenario/evaluasi\\_semua\\_skenario.csv. "
            "Nilai akurasi, presisi, \\asing{recall}, dan F1 ditulis sebagai proporsi (1 = 100\\%).}")


def log_pelatihan():
    """Ringkas log terminal 04_latih.py: satu baris per epoch, angka tidak diubah.
    Peringatan TensorFlow, tabel ringkasan model, dan path penyimpanan dibuang."""
    isi = ["Log berikut diambil dari keluaran terminal \\texttt{04\\_latih.py} (berkas "
           "\\texttt{bukti/04\\_pelatihan/s1--s4/log\\_04\\_latih\\_s*.txt}). Setiap baris memuat nomor \\asing{epoch}, "
           "akurasi dan \\asing{loss} data latih, akurasi dan \\asing{loss} data validasi, serta keterangan apakah "
           "\\asing{loss} validasi membaik. Peringatan TensorFlow dan lokasi penyimpanan model tidak ditampilkan.\n"]
    for s in config.SKENARIO:
        baris = open(BUKTI / "04_pelatihan" / s / f"log_04_latih_{s}.txt", encoding="utf-8", errors="replace").read().splitlines()
        mulai = next((b for b in baris if b.startswith("Mulai:")), "")
        selesai = next((b for b in baris if b.startswith("Selesai:")), "")
        param = next((b.strip() for b in baris if "Total params" in b), "")
        keluar, epoch, catatan = [], None, ""
        for b in baris:
            m = re.match(r"Epoch (\d+)/(\d+)$", b.strip())
            if m:
                epoch = f"{int(m.group(1)):>3}/{m.group(2)}"
                catatan = ""
                continue
            m = re.match(r"Epoch \d+: (val_loss improved from \S+ to [\d.]+|val_loss did not improve from [\d.]+)", b.strip())
            if m:
                catatan = m.group(1).replace("val_loss improved from", "membaik").replace(" to ", " -> ") \
                    .replace("val_loss did not improve from", "tetap")
                continue
            m = re.search(r"accuracy: ([\d.]+) - loss: ([\d.]+) - val_accuracy: ([\d.]+) - val_loss: ([\d.]+)", b)
            if m and epoch:
                keluar.append(f"Epoch {epoch}  acc {m.group(1)}  loss {m.group(2)}  val_acc {m.group(3)}  "
                              f"val_loss {m.group(4)}  ({catatan})")
                epoch = None
                continue
            if "Restoring model weights" in b or "early stopping" in b:
                keluar.append(b.strip())
        isi.append(f"\\par\\Needspace{{6\\baselineskip}}\\noindent\\textbf{{Skenario {NAMA_SKENARIO[s]}}}\\par\\nopagebreak\n"
                   "{\\fontsize{8bp}{9.6bp}\\selectfont\\begin{verbatim}\n"
                   + "\n".join([mulai, param] + keluar + [selesai])
                   + "\n\\end{verbatim}}")
    return "\n".join(isi)


def main():
    bagian = ["% Dibuat otomatis oleh source_code/python/16_lampiran_naskah.py dari folder bukti. Jangan disunting manual.\n"]

    bagian.append("\\lampiran{Hasil Pemeriksaan Lingkungan Pelatihan Model}{lamp:lingkungan}\n"
                  "\\begin{center}\\fbox{\\includegraphics[width=0.92\\textwidth]{gambar/lampiran/log_lingkungan.png}}\\end{center}\n"
                  "\\ketlampiran{Keluaran 01\\_cek\\_lingkungan.py pada laptop pelatihan, 13 November 2026.}")

    isi = ["\\lampiran{Kurva Pelatihan dan \\asing{Confusion Matrix} Data Uji Setiap Skenario}{lamp:kurva}"]
    for s in config.SKENARIO:
        # kurva dan confusion matrix berdampingan, satu baris per skenario
        isi.append(f"\\par\\Needspace{{6.5\\baselineskip}}\\noindent\\textbf{{Skenario {NAMA_SKENARIO[s]}}}\\par\\nopagebreak\n"
                   f"\\noindent\\begin{{minipage}}[c]{{0.66\\textwidth}}\\includegraphics[width=\\linewidth]{{gambar/lampiran/kurva_{s}.png}}\\end{{minipage}}\\hfill\n"
                   f"\\begin{{minipage}}[c]{{0.31\\textwidth}}\\includegraphics[width=\\linewidth]{{gambar/lampiran/cm_uji_{s}.png}}\\end{{minipage}}\\par\\vspace{{8pt}}")
    bagian.append("\n".join(isi))

    bagian.append("\\lampiran{Log Pelatihan Setiap Skenario}{lamp:logpelatihan}\n" + log_pelatihan())

    bagian.append("\\lampiran{Hasil Evaluasi Keempat Skenario}{lamp:evaluasi}\n" + tabel_evaluasi())

    bagian.append("\\lampiran{Perbandingan Augmentasi pada Data Validasi}{lamp:augmentasi}\n"
                  "\\begin{center}\\includegraphics[width=\\textwidth]{gambar/lampiran/perbandingan_augmentasi.png}\\end{center}\n"
                  "\\ketlampiran{Sumber: bukti/tanpa\\_augmentasi/perbandingan\\_augmentasi.png.}")

    # hanya screenshot tampilan baru (27 Nov 2026, folder "gambar aplikasi new"); screenshot tampilan lama dibuang
    android = [("hp2_registrasi.png", "Skenario 1: registrasi"), ("hp2_login.png", "Skenario 3: \\asing{login}"),
               ("hp2_beranda.png", "Skenario 3: beranda setelah \\asing{login}"),
               ("hp2_lupa_sandi.png", "Skenario 6: tautan lupa kata sandi terkirim"),
               ("hp2_hasil_layak.png", "Skenario 7: hasil klasifikasi layak"),
               ("hp2_hasil_tidak_layak.png", "Skenario 7: hasil klasifikasi tidak layak"),
               ("hp2_riwayat.png", "Skenario 10: riwayat petani"), ("hp2_akun.png", "Skenario 11: halaman akun")]
    sel = [f"\\begin{{minipage}}[t]{{0.235\\textwidth}}\\centering\n"
           f"\\fbox{{\\includegraphics[width=0.94\\linewidth]{{gambar/hasil/{b}}}}}\\\\[2pt]\n"
           f"{{\\footnotesize {k}}}\n\\end{{minipage}}" for b, k in android]
    kisi_hp = "\n".join("\\par\\noindent{\\centering\n" + "\\hfill\n".join(sel[i:i + 4]) + "\n\\par}\\vspace{6pt}"
                        for i in range(0, len(sel), 4))
    bagian.append("\\lampiran{\\asing{Screenshot Black Box Testing} Aplikasi Android}{lamp:android}\n"
                  "Pengujian dijalankan pada OPPO Reno4 (Android 12) dengan tampilan aplikasi yang diperbarui pada "
                  "27 November 2026. Bilah status HP dipotong.\n\n" + kisi_hp)

    web = sorted(FOLDER.glob("web_*.png"))
    bagian.append("\\lampiran{\\asing{Screenshot Black Box Testing Website}}{lamp:web}\n"
                  "Pengujian dijalankan pada Microsoft Edge 158, 22 November 2026.\n\n" + kisi(web, 2, 0.48))

    (LATEX / "akhir" / "lampiran.tex").write_text("\n\n".join(bagian) + "\n", encoding="utf-8")
    print("lampiran.tex:", len(android), "android,", len(web), "web")


if __name__ == "__main__":
    main()
