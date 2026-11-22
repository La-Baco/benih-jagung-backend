<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    // Aplikasi tidak menyediakan pendaftaran mandiri, jadi akun admin pertama dibuat di sini.
    // Kata sandi awal kedua akun ditetapkan peneliti: 12345678.
    // firstOrCreate dipakai karena seeder dijalankan setiap kontainer VPS dimulai; akun yang
    // sudah ada (termasuk kata sandi yang sudah diganti) tidak disentuh.
    public function run(): void
    {
        User::firstOrCreate(['email' => 'admin@benih.test'], [
            'nama' => 'Administrator',
            'password' => '12345678',
            'role' => 'Admin',
        ]);

        User::firstOrCreate(['email' => 'petani@benih.test'], [
            'nama' => 'Petani Contoh',
            'password' => '12345678',
            'role' => 'Petani',
        ]);
    }
}
