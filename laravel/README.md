# Aplikasi web dan API Laravel

Aplikasi web untuk admin dan petani, sekaligus API untuk aplikasi Android. Dibangun dengan Laravel 12 dan MySQL. Prediksi tidak dikerjakan di sini; setiap foto diteruskan ke layanan Flask. Model yang dipakai Flask dilatih di perangkat pengembang, bukan di server.

## Fitur per peran

| Peran | Halaman | Isi |
|---|---|---|
| Admin | Dashboard | Jumlah pengguna dan hasil klasifikasi |
| Admin | Pengguna | Tambah, ubah, dan hapus akun. Tidak ada pendaftaran mandiri |
| Admin | Dataset | Isi kelas Layak dan Tidak Layak, tambah foto dengan progress bar, hapus foto tambahan, unduh foto tambahan (.zip) |
| Admin | Model | Unggah model `.keras` hasil latihan di laptop (bertahap, bisa dijeda dan dilanjutkan), pilih model aktif, kembali ke model penelitian, tabel hasil S1-S4 |
| Admin | Riwayat | Klasifikasi seluruh pengguna |
| Petani | Dashboard, Klasifikasi, Riwayat | Unggah foto satu benih, lihat hasil dan skor, riwayat sendiri |

## Struktur

| Bagian | Berkas |
|---|---|
| Rute web | `routes/web.php` |
| Rute API | `routes/api.php` |
| Controller web | `app/Http/Controllers` (Login, Dashboard, Klasifikasi, Riwayat, Pengguna) |
| Controller admin | `app/Http/Controllers/Admin` (Dataset, Model, Unggahan) |
| Controller API | `app/Http/Controllers/Api` (Sesi, Klasifikasi) |
| Pemanggil Flask | `app/Services/LayananPrediksi.php` (prediksi), `app/Services/LayananAdminFlask.php` (dataset dan model) |
| Unggahan bertahap | `app/Services/UnggahanBertahap.php`, `public/js/unggah-bertahap.js` |
| Validasi foto | `app/Http/Requests/UnggahCitraRequest.php` (JPEG/PNG, maksimal 10 MB) |
| Pembatas peran | `app/Http/Middleware/CekRole.php` |
| Tampilan | `resources/views`, `public/css/app.css`, huruf Plus Jakarta Sans di `public/fonts` |
| Basis data | `database/migrations`: `users` dan `riwayat_klasifikasi` (PDM Gambar 3.13), ditambah `personal_access_tokens` untuk token aplikasi |
| Akun awal | `database/seeders/DatabaseSeeder.php` |
| Pengujian | `tests/Feature` |
| Image Docker | `Dockerfile`, `mulai_server.sh` |

## API untuk aplikasi Android

Alamatnya `https://api.skripsi-danur.synvorateknologiindonesia.web.id/api`. Semua jawaban berupa JSON, dan pesan galat ditulis dalam bahasa Indonesia di kolom `message`.

| Metode dan alamat | Kegunaan |
|---|---|
| `POST /masuk` (`email`, `password`, `perangkat`) | Login petani; mengembalikan token tanpa masa berlaku. Akun admin ditolak (403) |
| `GET /saya` | Data pengguna dari token |
| `POST /keluar` | Menghapus token |
| `POST /klasifikasi` (form `gambar`) | Klasifikasi satu foto lalu simpan ke riwayat |
| `POST /deteksi` (form `frame`, JPEG) | Mode kamera; tidak disimpan ke riwayat |
| `GET /riwayat?page=n` | Riwayat milik petani, 15 per halaman |
| `GET /riwayat/{id}/gambar` | Foto riwayat; hanya bisa diambil pemiliknya |

Token dikirim lewat header `Authorization: Bearer <token>`.

## Unggahan model bertahap

1. `POST /admin/unggahan` dengan nama, ukuran, dan sidik berkas. Server membuat sesi, atau mengembalikan sesi lama bila berkasnya sama.
2. `POST /admin/unggahan/{id}/{indeks}` untuk setiap potongan 4 MB, dikirim lewat 3 jalur sekaligus. Header `X-Sha256` dicocokkan di server, dan potongan ditulis langsung ke posisinya.
3. `GET /admin/unggahan/{id}` menunjukkan potongan yang sudah diterima. Data ini dipakai untuk melanjutkan setelah halaman dimuat ulang.
4. `POST /admin/model` meneruskan berkas lengkap ke Flask sebagai aliran, lalu folder unggahan dihapus.

Unggahan yang tidak disentuh lebih dari sehari dibersihkan otomatis.

## Menjalankan dan menguji di laptop

```
composer install
copy .env.example .env
php artisan key:generate
php artisan migrate --seed
php artisan storage:link
php artisan serve
php artisan test
```

Akun awal: `admin@benih.test` dan `petani@benih.test`, kata sandi `12345678`. Langkah lengkap ada di `CARA-PENGGUNAAN.md` bagian 3.
