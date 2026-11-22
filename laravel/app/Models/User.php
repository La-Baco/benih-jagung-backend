<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Laravel\Sanctum\HasApiTokens;

class User extends Authenticatable
{
    // HasApiTokens dipakai login aplikasi Flutter (token disimpan di tabel personal_access_tokens).
    // Notifiable dipakai untuk mengirim email tautan atur ulang kata sandi.
    use HasApiTokens, HasFactory, Notifiable;

    protected $fillable = [
        'nama',
        'email',
        'password',
        'role',
    ];

    protected $hidden = [
        'password',
    ];

    protected function casts(): array
    {
        return [
            'password' => 'hashed',
        ];
    }

    public function riwayat()
    {
        return $this->hasMany(RiwayatKlasifikasi::class);
    }
}
