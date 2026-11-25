# Pembaruan 25 November 2026: Deteksi Objek dan Penyaring "Bukan Jagung Ketan Putih"

Dokumen ini berisi dua bagian:

1. Apa yang sudah dikerjakan pada sistem, termasuk perbaikan versi 2 setelah uji lapangan.
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
| 2. Penyaring (Custom CNN baru) | Arsitektur dan pengaturannya sama dengan S3: 4 blok konvolusi, batch 16, Adam 0,001, early stopping patience 10. Ada dua kelas: jagung ketan putih (1) dan bukan (0), dengan ambang 0,5. Peluangnya adalah rata-rata dari potongan yang diputar 0°, 90°, 180°, dan 270° | "Jagung Ketan Putih" atau **"Bukan Jagung Ketan Putih"** |
| 3. Kelayakan (model S3 yang sudah ada) | Hanya dijalankan untuk objek yang lolos tahap 2 | "Layak" atau "Tidak Layak" |

Untuk foto satu benih di atas alas penelitian, potongan citra yang masuk ke S3 sama persis dengan prapemrosesan Subbab 3.6. Karena itu **hasil S1–S4 di BAB IV tidak berubah**.

Ukuran potongan: objek berukuran 504–1230 px pada lebar 3000 px (rentang benih di dataset) dipotong dengan S = 1330 px, sama seperti Subbab 3.6. Objek di luar rentang itu, misalnya benih yang difoto dari jauh, dipotong dengan S yang disesuaikan agar objek tampil seukuran median benih dataset (785 px).

### 1.3 Data untuk model penyaring (versi 2)

| Kelas | Sumber | Jumlah |
|---|---|---|
| Jagung ketan putih | 1.000 citra penelitian, dengan pembagian 70:15:15 yang sama. Setiap benih dipakai 4 kali: potongan asli, lalu 3 tempelan benih yang sama (diputar acak, ukuran acak) di alas penelitian dan di latar lain | latih 2.800, validasi 600, uji 600 |
| Bukan jagung ketan putih | Dataset publik berlisensi terbuka: batu dan mineral (udayl/rocks, MIT), **jagung kuning/oranye** (EfficientMaize, CC BY 4.0), kedelai, padi, gandum, kopi (Project-AgML, CC BY 4.0). Objek dipotong (Otsu + GrabCut), lalu ditempel 4 kali (2 di alas penelitian, 2 di latar lain) | latih 2.652, validasi 572, uji 556 |
| Uji benda yang belum pernah dilatih | Almond (MustafaYL/AlmondVarieties, MIT) | 600 citra dari 150 almond (hanya uji) |

Kedua kelas dibuat dengan cara yang sama persis. Setiap tempelan diberi variasi putaran, ukuran, bayangan, kilap, gamma dan kontras, warna cahaya, keburaman (seperti difoto dari jauh), dan kompresi JPEG. Dengan begitu model tidak bisa membedakan kelas dari latar, posisi, ukuran, atau cahaya.

### 1.4 Hasil pengujian (versi 2)

| Pengujian | Hasil |
|---|---|
| Pelatihan penyaring | 50 epoch, epoch terbaik 40: val loss 0,0531, val akurasi 98,55%. Lama pelatihan 66,8 menit di CPU laptop |
| Data uji penyaring, 1.156 citra | **Akurasi 97,84%**, presisi 97,84%, recall 98,00%, F1 97,92% (TP 588, FN 12, FP 13, TN 543) |
| Almond, belum pernah dilatih (600) | 63,5% ditolak sebagai "Bukan" |
| 150 foto uji skripsi lewat alur baru | 150/150 terdeteksi satu objek dan lolos penyaring. Hasil kelayakan **sama persis** dengan alur lama, jadi akurasi tetap 139/150 = 92,67% |
| Benih diganti batu (118 foto) | **Tidak ada yang dinilai Layak/Tidak Layak**: 114 ditolak sebagai "Bukan", 4 tidak terdeteksi |
| Benih diganti benda terlatih lain (160 foto) | **Tidak ada yang lolos sebagai ketan**: 141 ditolak, 19 tidak terdeteksi (17 biji kopi gelap, 2 padi) |
| Benih diganti almond (300 foto) | 193 ditolak, 107 lolos sebagai ketan (35,7%) |
| Benih asli + dua benda lain (30 foto) | Benih selalu dikenali (30/30), dan tidak ada benda lain yang lolos sebagai ketan. Ketiga objek terdeteksi terpisah pada 22/30 foto |
| **Foto uji lapangan** (8 foto pengguna, 13 objek) | **12/13 objek benar jenisnya**: 6/6 kerikil ditolak dan 6/7 benih dikenali (versi 1: 3/7 benih). Lihat 1.6 |
| Server VPS (API asli) | Foto lapangan menghasilkan keluaran yang sama dengan di laptop. Contoh: foto 2 kerikil + 2 benih menghasilkan 4 kotak dengan jenis yang benar |

### 1.5 Perubahan pada sistem

| Bagian | Perubahan |
|---|---|
| Layanan Flask | `/predict` dan `/deteksi` memakai alur tiga tahap. Respons menambah `jenis` dan `objek` (daftar bounding box beserta hasil per objek). Modul baru `deteksi_objek.py`, model baru `model/model_penyaring.keras` |
| Basis data | Kolom `hasil_prediksi` menerima nilai ketiga, "Bukan Jagung Ketan Putih". Kolom baru `objek` (JSON) menyimpan bounding box. Migrasi sudah berjalan di VPS, dan riwayat lama tetap aman |
| Website | Halaman hasil dan riwayat menggambar kotak di atas foto. Hasil "Bukan" berwarna cokelat, dan dashboard menampilkan jumlah "Bukan jagung ketan putih" |
| Aplikasi Android | Kotak tampil di kartu hasil dan detail riwayat. Mode kamera memberi kotak oranye untuk benda selain jagung ketan putih. APK bisa diunduh di https://github.com/La-Baco/benih-jagung-flutter/releases/tag/apk-2026-11-25 (versi 2 tidak mengubah aplikasi, jadi APK ini tetap berlaku) |
| Skrip penelitian baru | `17_siapkan_objek_bukan_ketan.py`, `18_bentuk_data_penyaring.py`, `19_latih_penyaring.py`, `20_evaluasi_penyaring.py` |
| Pengujian kode | Laravel 34/34, Flutter 12/12, `flutter analyze` tanpa masalah. Uji endpoint Flask (`skrip_pengujian/uji_flask_penyaring.py`) lolos semua untuk versi 2 |

Commit versi 1: backend `ebcb71f`, Flutter `f7ad426`, bukti `e8eaa73`. Commit versi 2: backend `409a350`. Semua bukti ada di folder `12_penyaring_objek/` (lihat bagian "Tahap penyaring objek" di `README.md`).

### 1.6 Perbaikan versi 2: benih asli ditolak pada uji lapangan

**Yang terjadi.** Pengguna mencoba aplikasi dengan foto nyata di atas kain hitam, termasuk satu foto berisi 2 kerikil + 1 benih layak + 1 benih tidak layak. Semua kerikil benar ditolak (99,99%). Namun benih asli yang difoto **dari jauh** juga dinilai "Bukan Jagung Ketan Putih". Benih yang difoto dekat tetap dikenali.

**Penyebab** (ditemukan dari foto riwayat 139–146 di server):

1. **Data "bukan" bertentangan dengan data ketan.** Dataset EfficientMaize yang dipakai sebagai "jagung lain" berisi banyak biji jagung putih yang sangat kecil (median 35 px) dan buram. Saturasi warnanya (median 77) sama dengan benih ketan layak (78). Model diajari bahwa "biji putih yang buram = bukan", padahal benih ketan yang difoto dari jauh tampak persis seperti itu.
2. **Perlakuan tidak setara.** Pada versi 1, stiker "bukan" diputar dan diskalakan acak, sedangkan benih ketan selalu tegak dengan ukuran asli. Model belajar bahwa objek yang miring, rebah, atau kecil berarti "bukan".
3. **Ukuran potongan tetap.** Benih yang difoto jauh hanya mengisi sekitar seperlima potongan, ukuran yang tidak pernah dilihat model.

**Perbaikan:**

- Jagung lain hanya diisi biji kuning/oranye (saturasi ≥ 130). Biji jagung putih biasa dikeluarkan karena secara visual tidak bisa dibedakan dari jagung ketan putih.
- Benih ketan diperlakukan sama dengan objek "bukan", ditambah variasi cahaya dan kualitas foto untuk kedua kelas.
- Stiker yang lebih kecil dari 32 px dibuang.
- Potongan disesuaikan dengan ukuran objek (lihat 1.2).
- Peluang penyaring diambil dari rata-rata 4 putaran.

**Hasil pada foto uji lapangan** (`12_penyaring_objek/foto_uji_lapangan/`, `evaluasi/alur_lengkap_foto_uji_lapangan.csv`):

| Foto | Isi | Versi 1 | Versi 2 |
|---|---|---|---|
| 139, 140 | 1 dan 3 kerikil | semua "Bukan" | semua "Bukan" |
| 141 | 2 kerikil + 2 benih | semua "Bukan" | kerikil "Bukan", **kedua benih dikenali** |
| 142 | 1 benih, sangat jauh | "Bukan" | masih "Bukan" (peluang ketan 0,04) |
| 143, 144, 145 | 1 benih, dekat | dikenali | dikenali |
| 146 | 1 benih, jauh dan miring | "Bukan" | **dikenali** |

Foto-foto ini dipakai untuk menemukan masalah, tetapi **tidak dipakai untuk melatih model**. Label kerikil/benih di `label.csv` ditentukan dari pengamatan visual dan perlu dikonfirmasi penulis.

**Yang dikorbankan:** akurasi data uji turun sedikit (98,83% → 97,84%), dan almond yang lolos naik (18,7% → 35,7%). Penyaring sekarang lebih mudah menerima biji krem yang bentuknya mirip benih.

### 1.7 Temuan penting: model kelayakan S3 terpengaruh alas

Di foto uji lapangan, semua benih yang difoto di atas kain hitam atau dari jauh mendapat peluang layak **0,00**. Akibatnya kedua benih di foto 141 dinilai "Tidak Layak", padahal salah satunya layak.

Untuk mengujinya, empat benih dataset dipindah (memakai topeng Otsu) ke 100 potongan alas penelitian yang berbeda-beda. Skripnya `skrip_pengujian/uji_s3_ganti_latar.py`, hasilnya `12_penyaring_objek/temuan_s3_ganti_latar.txt`.

| Benih | Hasil di foto asli | Dinilai Layak setelah dipindah ke 100 potongan alas | Korelasi kecerahan alas dengan peluang layak |
|---|---|---|---|
| layak_004 | 1,00 | 84 | −0,36 |
| layak_041 | 1,00 | 86 | −0,38 |
| tidak_layak_004 | 0,98 | 68 | −0,56 |
| tidak_layak_041 | 0,20 | 82 | −0,43 |

Artinya, untuk benih yang sama persis, keputusan S3 bisa berubah hanya karena potongan alasnya berbeda. Alas yang lebih gelap cenderung menaikkan peluang layak. Model S3 ikut memakai warna dan tekstur alas sebagai petunjuk.

Catatan: uji ini memakai tempelan dengan topeng Otsu, jadi tepi benih bisa sedikit berbeda dari foto asli. Hasilnya menunjukkan **arah** pengaruh alas, bukan besaran pastinya.

Akibat praktisnya: **hasil Layak/Tidak Layak hanya bisa dipercaya untuk foto yang dibuat persis seperti foto penelitian**, yaitu alas yang sama, jarak yang sama, dan cahaya yang sama. Ini tidak bisa diperbaiki tanpa melatih ulang model kelayakan, yang akan mengubah hasil BAB IV. Keputusan ini ada di tangan penulis (lihat 2.5).

---

## Bagian 2. Yang harus dikerjakan penulis

### 2.1 Naskah laporan

Tahap ini **belum ada di naskah**. Bagian yang perlu ditambah atau diubah:

- [ ] **BAB I, Batasan Masalah:** tambahkan bahwa foto diambil di atas alas polos yang kontras dengan objek, dan bahwa sistem menolak objek selain jagung ketan putih hanya untuk jenis benda yang ada di data latih.
- [ ] **BAB III, alur penelitian:** tambahkan tahap deteksi objek dan penyaring sebelum klasifikasi kelayakan. Gambar alur sistem perlu diperbarui dari 2 tahap menjadi 3 tahap.
- [ ] **BAB III, subbab baru "Penyaring Objek":**
  - sumber data kelas "Bukan" beserta lisensinya (tabel di 1.3);
  - cara pembentukan data: potong objek, tempel ke alas penelitian dan latar lain, variasi yang sama untuk kedua kelas;
  - pembagian data;
  - arsitektur, yang sama dengan S3 (cukup merujuk Tabel 3.6 dan 3.7);
  - rata-rata 4 putaran saat prediksi dan penyesuaian ukuran potongan (1.2).
- [ ] **BAB III, perancangan basis data (PDM):** tabel `riwayat_klasifikasi` sekarang punya nilai `hasil_prediksi` ketiga ("Bukan Jagung Ketan Putih") dan kolom `objek` (JSON).
- [ ] **BAB III, Tabel 3.12 (skenario black box):** tambahkan skenario baru, misalnya:
  - unggah foto kerikil → tampil "Bukan Jagung Ketan Putih" dengan kotak;
  - unggah foto alas kosong → tampil "Objek tidak terdeteksi";
  - unggah foto benih + kerikil → beberapa kotak dengan hasil masing-masing.
- [ ] **BAB IV, subbab baru hasil penyaring:** tabel hasil di 1.4 dan gambar-gambar berikut:
  - kurva pelatihan: `12_penyaring_objek/pelatihan/kurva_akurasi_loss.png`
  - confusion matrix: `12_penyaring_objek/evaluasi/confusion_matrix_uji.png`
  - contoh data latih: `12_penyaring_objek/data/contoh_data_latih_penyaring.png`
  - contoh bounding box: `12_penyaring_objek/evaluasi/contoh_bounding_box/` (termasuk `lapangan_*.jpg`)
  - tampilan riwayat web: `12_penyaring_objek/vps/riwayat_web_bounding_box.png`
- [ ] **BAB IV, hasil black box:** jalankan skenario baru di HP (OPPO Reno4) dan website, ambil tangkapan layarnya, lalu masukkan ke Tabel 4.9 dan Lampiran 5–6.
- [ ] **BAB IV, pembahasan:**
  - hasil S1–S4 tidak berubah (150/150 sama);
  - kesalahan penyaring: biji kopi gelap tidak terdeteksi, almond 35,7% lolos, benih foto 142 masih ditolak;
  - temuan uji lapangan dan perbaikannya (1.6);
  - pengaruh alas pada S3 (1.7).
- [ ] **BAB V, Kesimpulan dan Saran:** tambahkan kesimpulan tentang penyaring, lalu saran berikut:
  - menambah foto benda "Bukan" milik sendiri;
  - menambah foto benih ketan dari berbagai jarak, alas, dan cahaya;
  - melatih model kelayakan dengan alas dan cahaya yang beragam;
  - mencoba model deteksi objek (misalnya YOLO) agar tidak bergantung pada alas polos.
- [ ] **Abstrak:** sebutkan tahap penyaring dan akurasinya (97,84%).
- [ ] **Daftar Pustaka:** tambahkan sumber dataset publik (Hugging Face: udayl/rocks, Project-AgML, MustafaYL/AlmondVarieties) dan Describable Textures Dataset (DTD), yang dipakai sebagai latar.

### 2.2 Data dan verifikasi

- [ ] **Sangat disarankan: potret sendiri** dengan HP (OPPO Reno4):
  - **benda kelas "Bukan"**: kerikil putih dan berwarna, jagung kuning, kacang, beras, dan benda kecil lain;
  - **benih ketan putih di luar protokol**: difoto dari berbagai jarak, di alas lain (kain, kertas, meja), dengan cahaya lampu atau matahari, dan posisi rebah atau miring.

  Saat ini benih ketan di data latih hanya berasal dari foto penelitian, dan kelas "Bukan" seluruhnya dari dataset publik. Foto sendiri akan membuat penyaring jauh lebih kuat di lapangan. Setelah foto terkumpul, masukkan ke `dataset_objek`, lalu jalankan ulang skrip `18`, `19`, dan `20` **di laptop** (bukan di VPS).
- [ ] **Konfirmasi label foto uji lapangan** di `12_penyaring_objek/foto_uji_lapangan/label.csv` (kerikil atau benih), dan bila tahu, tambahkan kelayakan setiap benih.
- [ ] **Periksa `dataset/jenis_kerusakan.csv`.** Kolom `sumber` masih berbunyi "anotasi visual Claude ... belum diverifikasi peneliti". Ini catatan lama yang belum selesai.

### 2.3 Catatan yang perlu diperhatikan

- **Durasi pelatihan penyaring versi 2:** 66,8 menit (50 epoch, CPU). Angka versi 1 (149,7 menit, termasuk ±94 menit laptop tertidur) tidak berlaku lagi.
- **Angka di BAB IV tidak perlu diubah.** Model S3, data uji, dan hasilnya tetap sama.
- **APK tidak berubah** pada versi 2. Bila belum memasang APK baru, hapus aplikasi lama lebih dulu, lalu pasang dari https://github.com/La-Baco/benih-jagung-flutter/releases/tag/apk-2026-11-25
- **Pengaturan daya laptop.** Laptop masih diatur "tidak pernah tidur saat dicas". Kembalikan lewat Settings → System → Power bila perlu.
- **Belum dikerjakan:** SMTP untuk e-mail lupa kata sandi belum dipasang di server.

### 2.4 Batasan yang wajib ditulis jujur di laporan

1. **Alas harus polos dan kontras dengan objek.** Objek yang warnanya mirip alas bisa tidak terdeteksi. Contohnya biji kopi gelap di alas abu-abu gelap: 17 dari 36 tidak terdeteksi, tetapi tidak ada yang dinilai Layak.
2. **Benda yang jenisnya tidak pernah ada di data latih masih bisa lolos.** Contohnya almond: 35,7% lolos. Sistem **tidak bisa dijamin** benar untuk "segala bentuk, ukuran, dan warna".
3. **Jagung putih biasa tidak bisa dibedakan dari jagung ketan putih** hanya dari foto, sehingga tidak dipakai sebagai contoh "Bukan".
4. **Kelas "Bukan" berasal dari dataset publik**, bukan dari foto peneliti dengan HP dan alas yang sama.
5. **Hasil kelayakan (S3) hanya andal untuk foto sesuai protokol penelitian.** Pada alas, jarak, atau cahaya lain, S3 cenderung menilai semua benih "Tidak Layak" (1.7).

### 2.5 Keputusan yang perlu diambil penulis

Model S3 terpengaruh alas (1.7). Ada tiga pilihan:

1. **Biarkan S3, tulis sebagai batasan** (paling aman untuk sidang, karena hasil BAB IV tidak berubah). Aplikasi bisa diberi petunjuk "foto di atas alas penelitian dari jarak ±… cm".
2. **Latih model kelayakan baru** dengan augmentasi alas dan cahaya (benih ditempel ke berbagai latar, seperti penyaring). Hasil BAB IV harus ditulis ulang, dan perbandingan S1–S4 perlu diulang.
3. **Kumpulkan foto benih layak dan tidak layak di berbagai alas dan cahaya**, lalu latih ulang. Ini paling kuat, tetapi butuh pengambilan data baru.
