#!/bin/sh
# Dijalankan saat kontainer Laravel dimulai di VPS.
set -e

# Folder storage berupa volume, jadi isinya bisa kosong saat pertama kali dipasang.
mkdir -p storage/app/public/riwayat storage/framework/cache/data storage/framework/sessions \
    storage/framework/views storage/logs
chown -R www-data:www-data storage

php artisan migrate --force --seed
php artisan config:cache
php artisan route:cache
php artisan view:cache

exec apache2-foreground
