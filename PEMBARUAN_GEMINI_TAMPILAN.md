# Pembaruan 27 November 2026: Validasi Objek Gemini dan Tampilan Sesuai Rancangan (Model S3)

Dokumen ini menggantikan isi `PEMBARUAN_PENYARING_OBJEK.md` untuk sistem yang berjalan sekarang. Penyaring Custom CNN di dokumen itu sudah tidak dipakai, tetapi kode dan buktinya tetap disimpan sebagai arsip.

## 1. Yang berubah

| Bagian | Sebelum | Sekarang |
|---|---|---|
| Model kelayakan di server | S3 | **Tetap S3** (keputusan peneliti 27 November 2026, setelah sempat diganti S1 pada hari yang sama): akurasi uji 92,67%, F1 0,929, FP 8 |
| Aturan pemilihan model (`11_evaluasi_semua_skenario.py`) | Loss uji terendah | Tetap loss uji terendah (bila selisih < 0,01, parameter lebih sedikit) |
| Pemeriksaan "bukan jagung" | Custom CNN penyaring + kelas ketiga "Bukan Jagung Ketan Putih" | **Gemini API** (model `gemini-3.5-flash-lite`, API key milik Danur). Foto tanpa biji jagung ditolak dengan pesan, tidak disimpan ke riwayat |
| Kelas hasil | Layak, Tidak Layak, Bukan Jagung Ketan Putih | **Layak dan Tidak Layak saja** (sesuai Batasan Masalah no. 2) |
| Aplikasi Android | Tab Periksa, Kamera langsung, Riwayat | **Beranda, Klasifikasi, Riwayat, Akun**, sesuai Gambar 3.14–3.16. Mode kamera langsung dihapus |

## 2. Cara kerja satu foto

1. OpenCV menemukan objek di foto dan membuat bounding box.
2. Semua objek dipotong, diberi nomor, lalu dikirim ke Gemini dalam **satu gambar**, jadi satu foto memakai satu kuota. Gemini hanya menjawab "biji jagung atau bukan" untuk setiap nomor.
3. Objek yang bukan biji jagung tidak dinilai. Bila tidak ada satu pun biji jagung, aplikasi menampilkan *"Objek pada foto tidak dikenali sebagai biji jagung…"*.
4. Biji jagung dinilai model S3: Layak atau Tidak Layak, beserta skor kepercayaan.
5. Bila Gemini tidak bisa dihubungi atau kuotanya habis, muncul pesan *"Pemeriksaan objek sedang tidak tersedia"*.

## 3. Hasil pengujian

| Uji | Hasil |
|---|---|
| 150 foto uji penelitian lewat layanan | Hasil sama dengan evaluasi S3 (150/150), benar 139/150 = 92,67% |
| Kerikil saja (2 foto, 4 kerikil) di server | Ditolak sebagai bukan biji jagung |
| 2 kerikil + 2 benih (1 foto) | Kerikil diabaikan, kedua benih dinilai |
| Benih asli (5 foto) | Diterima dan dinilai |
| Waktu per foto di server | 2,3–3,2 detik (panggilan pertama sekitar 6–8 detik) |
| Uji lewat API publik (akun sementara, sudah dihapus) | Kerikil → 422, benih → 201, ringkasan riwayat benar |
| Laravel | 34/34 tes lolos |
| Flutter | `flutter analyze` bersih, 14/14 tes lolos, tampilan dicek di emulator |

Bukti tersimpan di:
- `05_evaluasi/analisis_ulang_4_skenario/` (perbandingan S1–S4: overfitting, kalibrasi, ketahanan);
- `05_evaluasi/semua_skenario/salah_prediksi_s3.jpg`;
- `13_validasi_gemini/`.

## 4. APK

Unduh di https://github.com/La-Baco/benih-jagung-flutter/releases/tag/apk-2026-11-27. Hapus dulu aplikasi lama di HP sebelum memasang.

## 5. Yang perlu dikerjakan penulis di naskah

- [ ] **BAB I, Batasan:** tambahkan bahwa foto yang objeknya bukan biji jagung ditolak oleh validasi masukan (Gemini API), dan bahwa validasi ini tidak bisa menjamin semua benda lain tertolak.
- [ ] **BAB III, Subbab 3.11:** model sistem tetap S3 (loss uji terendah). Catatan: aturan ini memakai data uji untuk memilih, sedangkan proposal memakai loss validasi (yang akan memilih S2). Siapkan jawaban bila penguji menanyakannya.
- [ ] **BAB III, arsitektur sistem dan flowchart:** tambahkan Gemini API sebagai validasi masukan sebelum model CNN. Tambahkan juga Gemini di Tabel 3.9 (nama model `gemini-3.5-flash-lite`).
- [ ] **BAB III, Tabel 3.12:** tambahkan skenario black box "unggah foto kerikil → muncul pesan bukan biji jagung".
- [ ] **BAB IV:** model terpilih tetap S3. Tabel analisis ulang S1–S4 bisa dipakai di pembahasan overfitting.
- [ ] **BAB III, Tabel 3.1/3.4.3:** periksa ulang `dataset/jenis_kerusakan.csv`. Isinya anotasi Claude dan belum diverifikasi.
- [ ] **Keamanan:** API key Gemini sempat ditulis di chat. Setelah sidang, sebaiknya buat key baru di AI Studio, lalu ganti baris `GEMINI_API_KEY` di `/opt/skripsi-danur/kode/deploy/.env.produksi`.

## 6. Repo

- Backend: https://github.com/La-Baco/benih-jagung-backend (commit `c2bfe68`).
- Aplikasi: https://github.com/La-Baco/benih-jagung-flutter (commit `0727b63`).
- Bukti: repo privat `adhfry/benih-jagung-bukti`. Danur sudah diundang sebagai collaborator dengan akses tulis; undangannya perlu diterima di https://github.com/adhfry/benih-jagung-bukti/invitations.

Untuk mengambil versi terbaru: `git pull` di setiap folder repo.
