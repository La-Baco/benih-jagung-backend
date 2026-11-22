<?php

namespace App\Services;

use App\Exceptions\PrediksiGagal;
use App\Models\RiwayatKlasifikasi;
use App\Models\User;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Http;

// Dipakai halaman web petani dan API aplikasi Flutter, supaya keduanya memanggil Flask
// dan menyimpan riwayat dengan cara yang sama (Gambar 3.10).
class LayananPrediksi
{
    public function klasifikasi(User $pengguna, UploadedFile $berkas): RiwayatKlasifikasi
    {
        // Nama dikirim dengan ekstensi hasil deteksi isi berkas, karena Flask memeriksa ekstensi.
        try {
            $respon = Http::timeout(30)
                ->attach('file', $berkas->get(), 'citra.' . $berkas->extension())
                ->post(config('services.flask.url') . '/predict');
        } catch (ConnectionException) {
            throw new PrediksiGagal('Layanan prediksi tidak tersedia. Coba beberapa saat lagi.', 503);
        }

        if ($respon->json('status') !== 'sukses') {
            throw new PrediksiGagal(
                $respon->json('pesan') ?? 'Layanan prediksi mengalami kesalahan.',
                $respon->serverError() ? 503 : 422,
            );
        }

        return RiwayatKlasifikasi::create([
            'user_id' => $pengguna->id,
            'path_gambar' => $berkas->store('riwayat', 'public'),
            'hasil_prediksi' => $respon->json('prediksi'),
            'skor_kepercayaan' => $respon->json('skor_kepercayaan'),
        ]);
    }
}
