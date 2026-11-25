# Pembaruan 25 November 2026: Deteksi Objek dan Penyaring "Bukan Jagung Ketan Putih"

Dokumen ini berisi dua bagian:

1. Apa yang sudah dikerjakan pada sistem.
2. Apa yang harus dikerjakan penulis (Danur Wenda) di naskah dan data.

---

## Bagian 1. Apa yang sudah dikerjakan

### 1.1 Masalah awal

Kerikil putih, atau benda apa pun yang difoto, tetap dinilai "Layak" atau "Tidak Layak". Penyebabnya, model S3 hanya pernah belajar dari benih jagung ketan putih. Model dengan dua kelas selalu memaksa setiap foto masuk ke salah satu kelas, walaupun yang difoto bukan benih.

Contoh nyata di riwayat server: pada 25 November 2026 pukul 09.25, foto jari di atas papan kayu dinilai **"Tidak Layak 99,99%"**.

### 1.2 Solusi: alur tiga tahap (tanpa YOLO)

YOLO tidak dipakai, supaya penelitian tetap memakai metode yang ada di skripsi (OpenCV dan Custom CNN).

| Tahap | Cara kerja | Keluaran |
|---|---|---|
| 1. Deteksi objek (OpenCV) | Warna alas ditaksir dari tepi foto. Jarak warna setiap piksel ke alas (ruang Lab) di-threshold dengan Otsu, lalu dibersihkan dengan opening dan closing. Setiap kontur yang tidak menyentuh tepi foto menjadi satu objek, dengan bounding box dari `cv2.boundingRect`. Objek yang warnanya terlalu mirip alas (jarak warna < 35) diabaikan | Bounding box setiap objek. Bila tidak ada objek: "Objek tidak terdeteksi" |
| 2. Penyaring (Custom CNN baru) | Arsitektur dan pengaturannya sama dengan S3: 4 blok konvolusi, batch 16, Adam 0,001, early stopping patience 10. Ada dua kelas: jagung ketan putih (1) dan bukan (0), dengan ambang 0,5 | "Jagung Ketan Putih" atau **"Bukan Jagung Ketan Putih"** |
| 3. Kelayakan (model S3 yang sudah ada) | Hanya dijalankan untuk objek yang lolos tahap 2 | "Layak" atau "Tidak Layak" |

Untuk foto satu benih di atas alas penelitian, potongan citra yang masuk ke S3 sama persis dengan prapemrosesan Subbab 3.6. Karena itu **hasil S1–S4 di BAB IV tidak berubah**.

### 1.3 Data untuk model penyaring

| Kelas | Sumber | Jumlah |
|---|---|---|
| Jagung ketan putih | 1.000 citra penelitian, dengan pembagian 70:15:15 yang sama. Setiap citra dipakai dua kali: foto asli di alas penelitian, dan benih yang dipindah ke latar lain (warna polos atau tekstur) | latih 1.400, validasi 300, uji 300 |
| Bukan jagung ketan putih | Dataset publik berlisensi terbuka: batu dan mineral (udayl/rocks, MIT), jagung varietas lain (EfficientMaize, CC BY 4.0), kedelai, padi, gandum, kopi (Project-AgML, CC BY 4.0). Objek dipotong (Otsu + GrabCut), lalu ditempel ke alas penelitian dan ke latar lain | latih 1.400, validasi 302, uji 298 |
| Uji benda yang belum pernah dilatih | Almond (MustafaYL/AlmondVarieties, MIT) | 300 (hanya uji) |

Kedua kelas sengaja muncul di latar yang sama, supaya model tidak bisa membedakan kelas hanya dari latarnya.

### 1.4 Hasil pengujian

| Pengujian | Hasil |
|---|---|
| Pelatihan penyaring | 61 epoch, epoch terbaik 51: val loss 0,0347, val akurasi 98,50%. Sekitar 1 menit per epoch di CPU laptop (lihat catatan durasi di Bagian 2) |
| Data uji penyaring, 598 citra | **Akurasi 98,83%**, presisi 98,35%, recall 99,33%, F1 98,84% (TP 298, FN 2, FP 5, TN 293) |
| Almond, belum pernah dilatih (300) | 75% ditolak sebagai "Bukan" |
| 150 foto uji skripsi lewat alur baru | 150/150 terdeteksi satu objek dan lolos penyaring. Hasil kelayakan **sama persis** dengan alur lama, jadi akurasi tetap 139/150 = 92,67% |
| Benih diganti batu (60 foto) | **Tidak ada yang dinilai Layak/Tidak Layak**: 53 ditolak sebagai "Bukan", 7 tidak terdeteksi |
| Benih diganti benda terlatih lain (149 foto) | 128 ditolak, 19 tidak terdeteksi, 2 lolos sebagai ketan |
| Benih asli + dua benda lain (30 foto) | Benih selalu dikenali, dan tidak ada benda lain yang lolos sebagai ketan. Ketiga objek terdeteksi pada 22/30 foto |
| Server VPS (API asli) | Benih → Layak 99,96%, batu → Bukan Jagung Ketan Putih 99,99%, benih + batu → dua kotak |

### 1.5 Perubahan pada sistem

| Bagian | Perubahan |
|---|---|
| Layanan Flask | `/predict` dan `/deteksi` memakai alur tiga tahap. Respons menambah `jenis` dan `objek` (daftar bounding box beserta hasil per objek). Modul baru `deteksi_objek.py`, model baru `model/model_penyaring.keras` |
| Basis data | Kolom `hasil_prediksi` menerima nilai ketiga, "Bukan Jagung Ketan Putih". Kolom baru `objek` (JSON) menyimpan bounding box. Migrasi sudah berjalan di VPS, dan riwayat lama tetap aman |
| Website | Halaman hasil dan riwayat menggambar kotak di atas foto. Hasil "Bukan" berwarna cokelat, dan dashboard menampilkan jumlah "Bukan jagung ketan putih" |
| Aplikasi Android | Kotak tampil di kartu hasil dan detail riwayat. Mode kamera memberi kotak oranye untuk benda selain jagung ketan putih. APK baru bisa diunduh di https://github.com/La-Baco/benih-jagung-flutter/releases/tag/apk-2026-11-25 |
| Skrip penelitian baru | `17_siapkan_objek_bukan_ketan.py`, `18_bentuk_data_penyaring.py`, `19_latih_penyaring.py`, `20_evaluasi_penyaring.py` |
| Pengujian kode | Laravel 34/34, Flutter 12/12, `flutter analyze` tanpa masalah |

Commit: backend `ebcb71f`, Flutter `f7ad426`, bukti `e8eaa73`. Semua bukti ada di folder `12_penyaring_objek/` (lihat bagian "Tahap penyaring objek" di `README.md`).

---

## Bagian 2. Yang harus dikerjakan penulis

### 2.1 Naskah laporan

Tahap ini **belum ada di naskah**. Bagian yang perlu ditambah atau diubah:

- [ ] **BAB I, Batasan Masalah:** tambahkan bahwa foto diambil di atas alas polos yang kontras dengan objek, dan bahwa sistem menolak objek selain jagung ketan putih hanya untuk jenis benda yang ada di data latih.
- [ ] **BAB III, alur penelitian:** tambahkan tahap deteksi objek dan penyaring sebelum klasifikasi kelayakan. Gambar alur sistem perlu diperbarui dari 2 tahap menjadi 3 tahap.
- [ ] **BAB III, subbab baru "Penyaring Objek":**
  - sumber data kelas "Bukan" beserta lisensinya (tabel di 1.3);
  - cara pembentukan data: potong objek, tempel ke alas penelitian dan latar lain;
  - pembagian data;
  - arsitektur, yang sama dengan S3 (cukup merujuk Tabel 3.6 dan 3.7).
- [ ] **BAB III, perancangan basis data (PDM):** tabel `riwayat_klasifikasi` sekarang punya nilai `hasil_prediksi` ketiga ("Bukan Jagung Ketan Putih") dan kolom `objek` (JSON).
- [ ] **BAB III, Tabel 3.12 (skenario black box):** tambahkan skenario baru, misalnya:
  - unggah foto kerikil → tampil "Bukan Jagung Ketan Putih" dengan kotak;
  - unggah foto alas kosong → tampil "Objek tidak terdeteksi";
  - unggah foto benih + kerikil → dua kotak dengan hasil masing-masing.
- [ ] **BAB IV, subbab baru hasil penyaring:** tabel hasil di 1.4 dan gambar-gambar berikut:
  - kurva pelatihan: `12_penyaring_objek/pelatihan/kurva_akurasi_loss.png`
  - confusion matrix: `12_penyaring_objek/evaluasi/confusion_matrix_uji.png`
  - contoh data latih: `12_penyaring_objek/data/contoh_data_latih_penyaring.png`
  - contoh bounding box: `12_penyaring_objek/evaluasi/contoh_bounding_box/`
  - tampilan riwayat web: `12_penyaring_objek/vps/riwayat_web_bounding_box.png`
- [ ] **BAB IV, hasil black box:** jalankan skenario baru di HP (OPPO Reno4) dan website, ambil tangkapan layarnya, lalu masukkan ke Tabel 4.9 dan Lampiran 5–6.
- [ ] **BAB IV, pembahasan:** jelaskan bahwa hasil S1–S4 tidak berubah (150/150 sama), dan jelaskan kesalahan penyaring (kedelai 4 dari 30, almond 18,7% lolos, biji kopi gelap tidak terdeteksi).
- [ ] **BAB V, Kesimpulan dan Saran:** tambahkan kesimpulan tentang penyaring, lalu saran berikut:
  - menambah foto benda "Bukan" milik sendiri;
  - mencoba model deteksi objek (misalnya YOLO) agar tidak bergantung pada alas polos;
  - verifikasi ahli untuk membedakan jagung putih varietas lain.
- [ ] **Abstrak:** sebutkan tahap penyaring dan akurasinya (98,83%).
- [ ] **Daftar Pustaka:** tambahkan sumber dataset publik (Hugging Face: udayl/rocks, Project-AgML, MustafaYL/AlmondVarieties) dan Describable Textures Dataset (DTD), yang dipakai sebagai latar.

### 2.2 Data dan verifikasi

- [ ] **Sangat disarankan: potret sendiri benda kelas "Bukan"** dengan HP (OPPO Reno4) dan alas yang sama seperti dataset, misalnya:
  - kerikil putih dan kerikil berwarna;
  - jagung kuning dan jagung varietas lain;
  - kacang, beras, dan benda kecil lain.

  Kelas "Bukan" saat ini seluruhnya dari dataset publik. Foto sendiri akan membuat penyaringan kerikil putih jauh lebih kuat. Setelah foto terkumpul, masukkan ke `dataset_objek` lalu jalankan ulang skrip `18`, `19`, dan `20` **di laptop** (bukan di VPS).
- [ ] **Periksa label jagung varietas lain.** Sebagian jagung dari dataset EfficientMaize berwarna putih dan diberi label "Bukan". Ciri pembedanya dengan jagung ketan putih belum diverifikasi ahli.
- [ ] **Periksa `dataset/jenis_kerusakan.csv`.** Kolom `sumber` masih berbunyi "anotasi visual Claude ... belum diverifikasi peneliti". Ini catatan lama yang belum selesai.

### 2.3 Catatan yang perlu diperhatikan

- **Durasi pelatihan penyaring.** `ringkasan.json` mencatat 149,7 menit, tetapi sekitar 94 menit di antaranya saat laptop tertidur di epoch ke-14. Waktu pelatihan sebenarnya sekitar 1 menit per epoch (±55 menit untuk 61 epoch). Jangan tulis 149,7 menit sebagai lama pelatihan tanpa penjelasan.
- **Angka di BAB IV tidak perlu diubah.** Model S3, data uji, dan hasilnya tetap sama.
- **APK baru.** Hapus aplikasi lama di HP lebih dulu, lalu pasang `Cek-Benih-Jagung.apk` yang baru dari https://github.com/La-Baco/benih-jagung-flutter/releases/tag/apk-2026-11-25
- **Pengaturan daya laptop.** Laptop masih diatur "tidak pernah tidur saat dicas". Kembalikan lewat Settings → System → Power bila perlu.
- **Belum dikerjakan:** SMTP untuk e-mail lupa kata sandi belum dipasang di server.

### 2.4 Batasan yang wajib ditulis jujur di laporan

1. **Alas harus polos dan kontras dengan objek.** Objek yang warnanya mirip alas bisa tidak terdeteksi. Contohnya biji kopi gelap di alas abu-abu gelap: 11 dari 19 tidak terdeteksi, tetapi tidak ada yang dinilai Layak.
2. **Benda yang jenisnya tidak pernah ada di data latih masih bisa lolos.** Contohnya almond: 18,7% lolos. Sistem **tidak bisa dijamin** benar untuk "segala bentuk, ukuran, dan warna".
3. **Kelas "Bukan" berasal dari dataset publik**, bukan dari foto peneliti dengan HP dan alas yang sama.
