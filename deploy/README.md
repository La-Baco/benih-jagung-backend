# Pemasangan di VPS

Berkas di folder ini memasang sistem di VPS Ubuntu 24.04 yang sudah memiliki Docker, nginx, dan certbot. VPS yang dipakai sekarang (76.13.196.43) dipakai bersama sekitar 40 situs lain, jadi semuanya dibuat terpisah di `/opt/skripsi-danur` dan tidak mengubah paket server.

| Berkas | Isi |
|---|---|
| `docker-compose.yml` | Tiga kontainer: `db` (MySQL 8.4), `flask` (layanan prediksi), `web` (Laravel PHP 8.3 + Apache) |
| `nginx-skripsi-danur.conf` | Dua domain diteruskan ke `127.0.0.1:8091`. Domain API hanya melayani `/api/` dan `/up` |
| `.env.produksi.contoh` | Kata sandi database, kunci layanan, dan lokasi folder data |
| `.env.laravel.contoh` | Pengaturan Laravel produksi (APP_KEY, APP_URL, sesi) |

## Susunan di server

```
/opt/skripsi-danur/
├── kode/            python, laravel, deploy (salinan source_code)
├── data/            volume layanan Flask (pemilik uid 10001)
│   ├── dataset/              1.000 citra penelitian + foto tambahan admin
│   ├── dataset_terhapus/     foto tambahan yang dihapus admin (bisa dikembalikan)
│   ├── model/                model yang sedang dipakai
│   ├── model_unggahan/       model .keras yang diunggah admin
│   └── hasil_penelitian/     ringkasan bukti/ untuk tabel di halaman Model
└── storage/         storage Laravel (foto riwayat, sesi, log, unggahan bertahap)
```

Hanya kontainer `web` yang dibuka, dan itu pun ke `127.0.0.1:8091`. Flask dan MySQL hanya bisa dihubungi dari jaringan internal Docker. **Server tidak melatih model.** Model dilatih di perangkat pengembang lalu diunggah lewat menu Model.

## Memasang dari awal

Langkah lengkapnya ada di `CARA-PENGGUNAAN.md` bagian 7. Ringkasnya:

1. Salin `python`, `laravel`, dan `deploy` ke `/opt/skripsi-danur/kode/`, tanpa `venv` dan `vendor`.
2. Salin dataset dan ringkasan hasil penelitian ke `/opt/skripsi-danur/data/`.
3. Buat `.env.produksi` dan `.env.laravel` dari berkas contoh, lalu isi kata sandi acak.
4. `sudo chown -R 10001:10001 /opt/skripsi-danur/data`
5. `sudo docker compose --env-file .env.produksi up -d --build`
6. Pasang konfigurasi nginx, lalu `sudo nginx -t && sudo systemctl reload nginx`.
7. Jalankan certbot untuk kedua domain.

## Perintah harian

Jalankan di `/opt/skripsi-danur/kode/deploy`:

| Keperluan | Perintah |
|---|---|
| Status | `sudo docker compose --env-file .env.produksi ps` |
| Log | `sudo docker compose --env-file .env.produksi logs -f flask` (atau `web`) |
| Pasang kode baru | salin kode, lalu `sudo docker compose --env-file .env.produksi up -d --build` |
| Hentikan (data tetap) | `sudo docker compose --env-file .env.produksi down` |
| Cadangkan database | `sudo docker compose --env-file .env.produksi exec db mysqldump -ubenih -p klasifikasi_benih > cadangan.sql` |
