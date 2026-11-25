<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class RiwayatKlasifikasi extends Model
{
    protected $table = 'riwayat_klasifikasi';

    // PDM hanya memiliki created_at.
    const UPDATED_AT = null;

    // Nilai hasil_prediksi untuk objek yang ditolak tahap penyaring (misalnya kerikil).
    const BUKAN_KETAN = 'Bukan Jagung Ketan Putih';

    protected $fillable = [
        'user_id',
        'path_gambar',
        'hasil_prediksi',
        'skor_kepercayaan',
        'objek',
    ];

    protected $casts = [
        'skor_kepercayaan' => 'decimal:2',
        // Daftar objek hasil deteksi: x, y, w, h (0-1 terhadap ukuran foto), jenis, prediksi, skor.
        'objek' => 'array',
        'created_at' => 'datetime',
    ];

    // Kelas CSS untuk warna hasil di tabel dan halaman hasil.
    public function kelasCss(): string
    {
        return match ($this->hasil_prediksi) {
            'Layak' => 'hasil-layak',
            'Tidak Layak' => 'hasil-tidak-layak',
            default => 'hasil-bukan',
        };
    }

    public function user()
    {
        return $this->belongsTo(User::class);
    }
}
