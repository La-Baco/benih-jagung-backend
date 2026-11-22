<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class RiwayatKlasifikasi extends Model
{
    protected $table = 'riwayat_klasifikasi';

    // PDM hanya memiliki created_at.
    const UPDATED_AT = null;

    protected $fillable = [
        'user_id',
        'path_gambar',
        'hasil_prediksi',
        'skor_kepercayaan',
    ];

    protected $casts = [
        'skor_kepercayaan' => 'decimal:2',
        'created_at' => 'datetime',
    ];

    public function user()
    {
        return $this->belongsTo(User::class);
    }
}
