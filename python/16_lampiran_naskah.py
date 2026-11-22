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
            sel.append(f"\\begin{{minipage}}[t]{{{lebar}\\textwidth}}\\centering\n"
                       f"\\fbox{{\\includegraphics[width={isi}\\linewidth]{{gambar/lampiran/{p.name}}}}}\\\\[2pt]\n"
                       f"{{\\footnotesize {keterangan(p.name)}}}\n\\end{{minipage}}")
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


def main():
    bagian = ["% Dibuat otomatis oleh source_code/python/16_lampiran_naskah.py dari folder bukti. Jangan disunting manual.\n"]

    bagian.append("\\lampiran{Hasil Pemeriksaan Lingkungan Pelatihan Model}{lamp:lingkungan}\n"
                  "\\begin{center}\\fbox{\\includegraphics[width=0.92\\textwidth]{gambar/lampiran/log_lingkungan.png}}\\end{center}\n"
                  "\\ketlampiran{Keluaran 01\\_cek\\_lingkungan.py pada laptop pelatihan, 13 November 2026.}")

    isi = ["\\lampiran{Kurva Pelatihan dan \\asing{Confusion Matrix} Data Validasi Setiap Skenario}{lamp:kurva}"]
    for s in config.SKENARIO:
        # kurva dan confusion matrix berdampingan, satu baris per skenario
        isi.append(f"\\par\\Needspace{{6.5\\baselineskip}}\\noindent\\textbf{{Skenario {NAMA_SKENARIO[s]}}}\\par\\nopagebreak\n"
                   f"\\noindent\\begin{{minipage}}[c]{{0.66\\textwidth}}\\includegraphics[width=\\linewidth]{{gambar/lampiran/kurva_{s}.png}}\\end{{minipage}}\\hfill\n"
                   f"\\begin{{minipage}}[c]{{0.31\\textwidth}}\\includegraphics[width=\\linewidth]{{gambar/lampiran/cm_validasi_{s}.png}}\\end{{minipage}}\\par\\vspace{{8pt}}")
    bagian.append("\n".join(isi))

    bagian.append("\\lampiran{Hasil Evaluasi Keempat Skenario}{lamp:evaluasi}\n" + tabel_evaluasi())

    bagian.append("\\lampiran{Perbandingan Augmentasi pada Data Validasi}{lamp:augmentasi}\n"
                  "\\begin{center}\\includegraphics[width=\\textwidth]{gambar/lampiran/perbandingan_augmentasi.png}\\end{center}\n"
                  "\\ketlampiran{Sumber: bukti/tanpa\\_augmentasi/perbandingan\\_augmentasi.png.}")

    android = sorted(FOLDER.glob("android_*.png"))
    bagian.append("\\lampiran{\\asing{Screenshot Black Box Testing} Aplikasi Android}{lamp:android}\n"
                  "Pengujian dijalankan pada OPPO Reno4 (Android 12), 22 November 2026. Bilah status HP dipotong.\n\n"
                  + kisi(android, 3, 0.31, 0.7))

    web = sorted(FOLDER.glob("web_*.png"))
    bagian.append("\\lampiran{\\asing{Screenshot Black Box Testing Website}}{lamp:web}\n"
                  "Pengujian dijalankan pada Microsoft Edge 158, 22 November 2026.\n\n" + kisi(web, 2, 0.48))

    (LATEX / "akhir" / "lampiran.tex").write_text("\n\n".join(bagian) + "\n", encoding="utf-8")
    print("lampiran.tex:", len(android), "android,", len(web), "web")


if __name__ == "__main__":
    main()
