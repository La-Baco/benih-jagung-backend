# Model CNN dan layanan prediksi Flask

Folder ini berisi dua hal:

1. **Skrip penelitian** `01` sampai `20`, yang dijalankan di laptop peneliti untuk menghasilkan model dan bukti BAB IV.
2. **Layanan prediksi Flask** (`app.py`, `admin.py`), yang dipanggil aplikasi Laravel. Layanan ini hanya menjalankan prediksi. Pelatihan tidak pernah dijalankan di server.

> **Model dilatih di perangkat pengembang.** Model yang dipakai sistem adalah S1 (`model/model_akhir.keras`, dipilih `11_evaluasi_semua_skenario.py`; disimpan ulang tanpa state optimizer sehingga 49 MB, bobot dan keluarannya identik dengan `bukti/04_pelatihan/s1/model_s1.keras`). Model ini dilatih di laptop peneliti dengan spesifikasi berikut (dicatat oleh `01_cek_lingkungan.py`):
> - Intel Core i7-1355U, RAM 15,7 GB, Windows 11
> - TensorFlow 2.21.0, di CPU (tanpa GPU)
> - 27 epoch dalam 5,8 menit
>
> Server VPS dipakai bersama layanan lain, jadi server hanya memuat model `.keras` yang sudah jadi.

## Versi

| Paket | Laptop (`requirements.txt`) | VPS (`requirements-server.txt`) |
|---|---|---|
| Python | 3.10.6 | 3.10.6 (image `python:3.10.6-slim`) |
| TensorFlow / Keras | 2.21.0 / 3.12.4 | sama |
| OpenCV | `opencv-python==5.0.0.93` | `opencv-python-headless==5.0.0.93` (tanpa modul jendela) |
| Flask | 3.1.3 | 3.1.3 + gunicorn 23.0.0 |
| Matplotlib | 3.10.9 | 3.10.9 |

`requirements-gpu.txt` dipakai bila ingin melatih dengan GPU NVIDIA lewat WSL2 (lihat `CARA-PENGGUNAAN.md` bagian 4.1).

## Skrip penelitian (dijalankan berurutan di laptop)

| Skrip | Tahap (BAB III) | Hasil |
|---|---|---|
| `01_cek_lingkungan.py` | Mencatat perangkat lunak dan perangkat keras | `bukti/01_lingkungan` |
| `02_prapemrosesan_dataset.py` | Tahap 5: grayscale, Otsu, opening 21x21, kontur, potong persegi S = 1.330 px, ubah ke 224 x 224 | `dataset_olah/semua`, `model/prapemrosesan.json`, `bukti/02_prapemrosesan` |
| `03_bagi_dataset.py` | Tahap 6: bagi 70:15:15 per kelas, seed 42, cek kebocoran | `dataset_olah/latih`, `validasi`, `uji`, `bukti/03_pembagian_dataset` |
| `04_latih.py s1` ... `s4` | Tahap 7: latih satu skenario (Tabel 3.8), augmentasi flip dan rotasi 0/90/180/270. `--tanpa-augmentasi` untuk run pembanding | `bukti/04_pelatihan/sX`, `bukti/augmentasi` |
| `05_evaluasi.py` | Tahap 8: bandingkan 4 skenario di data validasi, pilih loss validasi terendah, uji sekali pada data uji | `bukti/05_evaluasi`, `model/model_akhir.keras` |
| `06_cek_konsistensi.py` | Prapemrosesan Flask harus sama dengan data latih (selisih piksel 0) | `bukti/06_layanan_flask` |
| `07_lembar_salah_prediksi.py` | Lembar citra FP/FN dan sebaran per jenis kerusakan | `bukti/05_evaluasi` |
| `08_bandingkan_augmentasi.py` | Bandingkan run dengan dan tanpa augmentasi | `bukti/tanpa_augmentasi` |
| `10_cek_mode_kamera.py` | Mode kamera `/deteksi` harus memberi kelas sama dengan `/predict`. Bagian saringan warna (`mirip_benih`) adalah bukti versi sebelum tahap penyaring; `/deteksi` sekarang menilai semua objek tanpa validasi Gemini | `bukti/08_mode_kamera` |
| `11_evaluasi_semua_skenario.py` | Evaluasi S1-S4 pada data latih, validasi, dan uji; memilih model sistem: akurasi uji tertinggi, lalu F1, lalu FP paling sedikit (sebelum 27 November 2026: loss uji terendah, yang memilih S3). Hasil saat ini: S1 | `bukti/05_evaluasi/semua_skenario` |
| `12_black_box_web.py` | Black box website, skenario 12-21 (Selenium, Edge) | `bukti/10_black_box/web` |
| `13_hp.py` | Alat bantu black box aplikasi Android lewat ADB | `bukti/10_black_box/android` |
| `14_gambar_bab4.py` | Gambar dan tabel BAB IV dari hasil yang sudah ada (tanpa melatih ulang) | `bukti/05_evaluasi/semua_skenario` |
| `15_gambar_naskah_besar.py` | Menata ulang gambar BAB IV dan lampiran supaya terbaca saat dicetak | folder gambar naskah LaTeX |
| `16_lampiran_naskah.py` | Menyusun `lampiran.tex` naskah dari folder bukti | folder naskah LaTeX |
| `17_siapkan_objek_bukan_ketan.py` | **Arsip** (dijalankan di commit 409a350, tidak dipakai layanan lagi). Penyaring objek (1/4): memotong objek "bukan jagung ketan putih" (batu, jagung lain, kedelai, padi, gandum, kopi, almond) dari dataset publik, dan potongan alas dari foto penelitian | `dataset_objek/stiker_bukan`, `dataset_objek/latar_peneliti` |
| `18_bentuk_data_penyaring.py` | **Arsip** (dijalankan di commit 409a350, tidak dipakai layanan lagi). Penyaring objek (2/4): citra 224 x 224 dua kelas; kedua kelas muncul di alas penelitian dan di latar lain | `dataset_penyaring` |
| `19_latih_penyaring.py` | **Arsip** (dijalankan di commit 409a350, tidak dipakai layanan lagi). Penyaring objek (3/4): latih Custom CNN dengan arsitektur dan pengaturan S3 | `bukti/12_penyaring_objek/pelatihan`, `model/model_penyaring.keras` |
| `20_evaluasi_penyaring.py` | **Arsip** (dijalankan di commit 409a350, tidak dipakai layanan lagi). Penyaring objek (4/4): uji sekali pada data uji, kategori yang belum pernah dilatih, 150 foto uji penelitian lewat alur lengkap, dan foto susunan (benih diganti batu, benih + benda lain) | `bukti/12_penyaring_objek/evaluasi` |

Semua angka penting (learning rate, epoch, patience, skenario, ukuran citra, batas deteksi) hanya ada di `config.py`.

## Modul

| Berkas | Isi |
|---|---|
| `config.py` | Semua parameter dan lokasi folder. Lokasi bisa diganti lewat variabel lingkungan `FOLDER_PROYEK`, `FOLDER_BUKTI`, `FOLDER_MODEL`, `FOLDER_HASIL_PENELITIAN` (dipakai di VPS) |
| `prapemrosesan.py` | Fungsi prapemrosesan yang sama untuk dataset dan layanan Flask, ditambah `ke_biner_beda_latar` untuk deteksi objek (objek lebih terang, lebih gelap, atau berbeda warna dari alas polos) |
| `deteksi_objek.py` | Alur satu foto: deteksi objek dan bounding box (OpenCV), validasi jenis objek (opsional), kelayakan (model sistem) |
| `pemeriksa_gemini.py` | Validasi jenis objek lewat Gemini API: semua objek dikirim dalam satu gambar kisi bernomor, jawabannya biji jagung atau bukan |
| `model_aktif.py` | Model kelayakan dan nilai S yang sedang dipakai (bisa diganti tanpa mematikan layanan) |
| `app.py` | Layanan prediksi |
| `admin.py` | Endpoint admin (dataset dan model unggahan), hanya dengan header `X-Kunci-Layanan` |

## Endpoint layanan

| Metode dan alamat | Kegunaan | Keluaran |
|---|---|---|
| `GET /` | Cek layanan | `status`, model aktif, keterangan bahwa model dilatih di perangkat pengembang |
| `POST /predict` (form `file`) | Klasifikasi satu foto (Tabel 3.13). Hasil utama dari objek biji jagung terbesar; `prediksi` hanya `Layak` atau `Tidak Layak`. Foto tanpa biji jagung: 422; validasi Gemini tidak tersedia: 503 | `{"status":"sukses","prediksi":"Layak","skor_kepercayaan":97.31,"jenis":"Jagung Ketan Putih","objek":[...]}` |
| `POST /deteksi` (form `file`) | Mode kamera: beberapa objek dalam satu frame (**mode percobaan**, di luar Batasan no. 4) | daftar `benih`, isinya sama dengan `objek` di `/predict` |
| `GET /admin/dataset` | Jumlah citra per kelas | |
| `GET /admin/dataset/<kelas>?halaman=n` | Daftar berkas, 24 per halaman | |
| `GET /admin/dataset/<kelas>/<nama>/kecil` | Gambar kecil 240 px | JPEG |
| `POST /admin/dataset/<kelas>` (form `gambar`, boleh banyak) | Tambah foto; ditolak bila benih tidak terdeteksi atau foto kembar (MD5) | `disimpan`, `ditolak` |
| `DELETE /admin/dataset/<kelas>/<nama>` | Hapus foto tambahan (citra 1-500 dilindungi) | |
| `GET /admin/dataset/tambahan.zip` | Unduh foto tambahan untuk dilatih di laptop | ZIP |
| `GET /admin/model` | Model aktif, model unggahan, hasil penelitian, perangkat pelatihan | |
| `POST /admin/model/unggah` (form `berkas`, `sisi_potong`, `keterangan`) | Simpan model `.keras`; diperiksa bisa dimuat, masukan 224x224x3, keluaran 1 peluang 0-1 | |
| `POST /admin/model/aktif` (`{"sumber": id atau "penelitian"}`) | Ganti model yang dipakai | |
| `DELETE /admin/model/<id>` | Hapus model unggahan yang tidak sedang dipakai | |

Setiap isi `objek` berisi `x, y, w, h` (0-1 terhadap ukuran foto), `jenis`, `peluang_ketan`, `skor_jenis`, `peluang_layak` (kosong bila bukan jagung ketan putih), `prediksi`, dan `skor_kepercayaan`.

### Alur satu foto

1. **Deteksi objek (OpenCV).** Warna alas ditaksir dari tepi foto, jarak warna tiap piksel ke alas di-threshold dengan Otsu, lalu dibersihkan dengan opening. Setiap kontur yang tidak menyentuh tepi foto menjadi satu objek, dan `cv2.boundingRect` memberi bounding box-nya. Syaratnya alas polos; pada alas bermotif, kontur bisa gagal.
2. **Validasi jenis objek (Gemini API, hanya di `/predict`).** Semua objek dipotong, diberi nomor, dan dikirim dalam satu gambar ke Gemini (`config.GEMINI_MODEL`, temperatur 0, jawaban JSON). Gemini hanya menjawab apakah setiap objek adalah biji jagung; ia tidak menilai kelayakan dan bukan bagian dari model penelitian. Objek yang bukan biji jagung tidak dinilai. Bila tidak ada satu pun biji jagung, `/predict` mengembalikan 422 "Objek pada foto tidak dikenali sebagai biji jagung" (seperti citra tidak valid), jadi keluaran sistem tetap dua kelas. Bila Gemini tidak bisa dihubungi atau kuota habis: 503. Bila `GEMINI_API_KEY` kosong, tahap ini dilewati.
3. **Kelayakan (model sistem S1).** Hanya untuk objek biji jagung. Untuk foto satu benih di atas alas penelitian, potongannya sama dengan prapemrosesan Subbab 3.6, sehingga hasil 150 foto uji sama dengan evaluasi BAB IV (diuji: 150/150 sama).

`/deteksi` (mode kamera) tidak memakai Gemini, karena frame dikirim terus-menerus dan akan menghabiskan kuota.

Ukuran potongan (`deteksi_objek.sisi_potong`): objek berukuran 504-1230 px (pada lebar 3000 px, rentang benih di dataset) dipotong dengan S tetap seperti Subbab 3.6. Objek di luar rentang itu, misalnya benih yang difoto dari jauh, dipotong dengan S yang disesuaikan agar objek tampil seukuran median benih dataset (785 px).

Batasan yang sudah diukur (`bukti/05_evaluasi/analisis_ulang_4_skenario`): keempat model S1-S4 hanya dilatih dengan foto di atas alas penelitian. Bila benih yang sama dipindah ke alas lain, hasilnya berubah pada 97-100% benih. Hasil kelayakan hanya bisa dipercaya untuk foto yang dibuat sesuai protokol Tabel 3.2.

## Menjalankan di laptop

```
cd source_code\python
py -3.10 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Layanan berjalan di `http://127.0.0.1:5000`. Untuk endpoint `/admin`, jalankan dulu `set KUNCI_LAYANAN=<teks acak>` dengan nilai yang sama seperti `FLASK_KUNCI_LAYANAN` di `.env` Laravel. Di laptop, penggantian model sengaja ditolak supaya model skripsi di `model/` tidak tertimpa.

## Di VPS

Dijalankan sebagai kontainer Docker (`Dockerfile`, `mulai_server.sh`):

- Satu worker gunicorn dengan 4 thread.
- TensorFlow dibatasi 2 thread, kontainer dibatasi 2,5 CPU.
- Data ada di volume `/data`:
  - `dataset`
  - `model` (model aktif)
  - `model_unggahan`
  - `hasil_penelitian` (ringkasan dari `bukti/`)

Langkah pemasangan ada di `source_code/deploy/README.md`.
