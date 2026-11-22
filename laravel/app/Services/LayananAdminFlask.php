<?php

namespace App\Services;

use App\Exceptions\PrediksiGagal;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Http\Client\Response;
use Illuminate\Support\Facades\Http;

// Pemanggil endpoint /admin di Flask (kelola dataset dan pelatihan ulang).
class LayananAdminFlask
{
    private function klien(int $batasWaktu = 20): PendingRequest
    {
        return Http::baseUrl(config('services.flask.url') . '/admin')
            ->withHeaders(['X-Kunci-Layanan' => (string) config('services.flask.kunci')])
            ->acceptJson()
            ->timeout($batasWaktu);
    }

    public function kirim(string $metode, string $alamat, array $data = []): Response
    {
        try {
            return $this->klien()->send($metode, $alamat, $data ? ['json' => $data] : []);
        } catch (ConnectionException) {
            throw new PrediksiGagal('Layanan Flask tidak dapat dihubungi. Pastikan layanan prediksi berjalan.', 503);
        }
    }

    public function ambil(string $alamat, array $query = []): array
    {
        $respon = $this->kirim('GET', $alamat . ($query ? '?' . http_build_query($query) : ''));
        $this->pastikanBerhasil($respon);

        return $respon->json();
    }

    public function unggah(string $alamat, array $daftarBerkas): array
    {
        $klien = $this->klien(120);
        foreach ($daftarBerkas as $berkas) {
            // Nama kolom tanpa [] karena Flask membaca request.files.getlist("gambar").
            $klien->attach('gambar', $berkas->get(), $berkas->getClientOriginalName());
        }

        try {
            $respon = $klien->post($alamat);
        } catch (ConnectionException) {
            throw new PrediksiGagal('Layanan Flask tidak dapat dihubungi. Pastikan layanan prediksi berjalan.', 503);
        }
        $this->pastikanBerhasil($respon);

        return $respon->json();
    }

    // Berkas model dikirim sebagai aliran (stream), jadi model ratusan MB tidak dimuat utuh ke memori PHP.
    public function unggahModel(string $path, string $nama, array $data): array
    {
        $aliran = fopen($path, 'r');
        try {
            $respon = $this->klien(600)->attach('berkas', $aliran, $nama)->post('/model/unggah', $data);
        } catch (ConnectionException) {
            throw new PrediksiGagal('Layanan Flask tidak dapat dihubungi. Pastikan layanan prediksi berjalan.', 503);
        } finally {
            // Ditutup di sini supaya folder unggahan sementara bisa langsung dihapus sesudahnya.
            if (is_resource($aliran)) {
                fclose($aliran);
            }
        }
        $this->pastikanBerhasil($respon);

        return $respon->json();
    }

    // Gambar kecil dataset dan kurva hasil penelitian diteruskan apa adanya ke peramban admin.
    public function gambar(string $alamat)
    {
        try {
            $respon = $this->klien()->accept('image/*')->get($alamat);
        } catch (ConnectionException) {
            abort(503);
        }
        abort_unless($respon->successful(), 404);

        return response($respon->body(), 200, [
            'Content-Type' => $respon->header('Content-Type'),
            'Cache-Control' => 'private, max-age=3600',
        ]);
    }

    public function pastikanBerhasil(Response $respon): void
    {
        if ($respon->json('status') !== 'sukses') {
            throw new PrediksiGagal($respon->json('pesan') ?? 'Layanan Flask mengembalikan galat ' . $respon->status() . '.', $respon->status());
        }
    }
}
