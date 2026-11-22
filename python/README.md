# Model CNN dan layanan prediksi Flask

Folder ini berisi dua hal:

1. **Skrip penelitian** `01` sampai `10`, yang dijalankan di laptop peneliti untuk menghasilkan model dan bukti BAB IV.
2. **Layanan prediksi Flask** (`app.py`, `admin.py`), yang dipanggil aplikasi Laravel. Layanan ini hanya menjalankan prediksi. Pelatihan tidak pernah dijalankan di server.

> **Model dilatih di perangkat pengembang.** Model penelitian S2 dilatih di laptop peneliti dengan spesifikasi berikut (dicatat oleh `01_cek_lingkungan.py`):
> - Intel Core i7-1355U, RAM 15,7 GB, Windows 11
> - TensorFlow 2.21.0, di CPU (tanpa GPU)
> - 70 epoch dalam 17,9 menit
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
| `10_cek_mode_kamera.py` | Mode kamera `/deteksi` harus memberi kelas sama dengan `/predict`; saringan warna diuji | `bukti/08_mode_kamera` |

Semua angka penting (learning rate, epoch, patience, skenario, ukuran citra, batas deteksi) hanya ada di `config.py`.

## Modul

| Berkas | Isi |
|---|---|
| `config.py` | Semua parameter dan lokasi folder. Lokasi bisa diganti lewat variabel lingkungan `FOLDER_PROYEK`, `FOLDER_BUKTI`, `FOLDER_MODEL`, `FOLDER_HASIL_PENELITIAN` (dipakai di VPS) |
| `prapemrosesan.py` | Fungsi prapemrosesan yang sama untuk dataset dan layanan Flask, ditambah `cari_semua_kontur_benih` dan `mirip_benih` untuk mode kamera |
| `model_aktif.py` | Model dan nilai S yang sedang dipakai; bisa diganti tanpa mematikan layanan |
| `app.py` | Layanan prediksi |
| `admin.py` | Endpoint admin (dataset dan model unggahan), hanya dengan header `X-Kunci-Layanan` |

## Endpoint layanan

| Metode dan alamat | Kegunaan | Keluaran |
|---|---|---|
| `GET /` | Cek layanan | `status`, model aktif, keterangan bahwa model dilatih di perangkat pengembang |
| `POST /predict` (form `file`) | Klasifikasi satu benih (Tabel 3.13) | `{"status":"sukses","prediksi":"Layak","skor_kepercayaan":97.31}` |
| `POST /deteksi` (form `file`) | Mode kamera: beberapa benih dalam satu frame (**mode percobaan**, di luar Batasan no. 4) | daftar `benih` berisi `x, y, w, h` (0-1), `peluang_layak`, `prediksi` |
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
