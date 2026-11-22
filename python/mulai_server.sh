#!/bin/sh
# Dijalankan saat kontainer Flask dimulai di VPS.
set -e

mkdir -p /data/dataset/layak_tanam /data/dataset/tidak_layak_tanam /data/model

# Saat pertama kali dipasang, layanan memakai model penelitian (S2) yang ikut di dalam image.
if [ ! -f /data/model/model_akhir.keras ]; then
    cp /app/model/model_akhir.keras /app/model/prapemrosesan.json /data/model/
fi

# Satu worker saja: model dimuat sekali, dan status pelatihan dipantau dari proses yang sama.
exec gunicorn --workers 1 --threads 4 --timeout 180 --bind 0.0.0.0:5000 app:app
