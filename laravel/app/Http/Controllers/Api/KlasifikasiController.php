<?php

namespace App\Http\Controllers\Api;

use App\Exceptions\PrediksiGagal;
use App\Http\Controllers\Controller;
use App\Http\Requests\UnggahCitraRequest;
use App\Models\RiwayatKlasifikasi;
use App\Services\LayananPrediksi;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;

class KlasifikasiController extends Controller
{
    public function store(UnggahCitraRequest $request, LayananPrediksi $layanan)
    {
        try {
            $riwayat = $layanan->klasifikasi($request->user(), $request->file('gambar'));
        } catch (PrediksiGagal $e) {
            return response()->json(['message' => $e->getMessage()], $e->kodeHttp);
        }

        return response()->json(['data' => $this->format($riwayat)], 201);
    }

    // Mode kamera: frame tidak disimpan ke riwayat karena dikirim terus-menerus selama kamera terbuka.
    public function deteksi(Request $request)
    {
        $request->validate([
            'frame' => ['required', 'file', 'mimes:jpg,jpeg', 'max:4096'],
        ], [
            'frame.required' => 'Frame kamera wajib dikirim.',
            'frame.mimes' => 'Frame kamera harus berformat JPEG.',
            'frame.max' => 'Ukuran frame maksimal 4 MB.',
        ]);

        try {
            $respon = Http::timeout(20)
                ->attach('file', $request->file('frame')->get(), 'frame.jpg')
                ->post(config('services.flask.url') . '/deteksi');
        } catch (ConnectionException) {
            return response()->json(['message' => 'Layanan prediksi tidak tersedia. Coba beberapa saat lagi.'], 503);
        }

        if ($respon->json('status') !== 'sukses') {
            return response()->json(['message' => $respon->json('pesan') ?? 'Layanan prediksi mengalami kesalahan.'], 503);
        }

        return response()->json(['benih' => $respon->json('benih')]);
    }

    public function index(Request $request)
    {
        $riwayat = RiwayatKlasifikasi::where('user_id', $request->user()->id)->latest('id')->paginate(15);

        return response()->json([
            'data' => $riwayat->getCollection()->map(fn ($item) => $this->format($item)),
            'halaman' => $riwayat->currentPage(),
            'halaman_terakhir' => $riwayat->lastPage(),
            'total' => $riwayat->total(),
        ]);
    }

    public function gambar(Request $request, RiwayatKlasifikasi $riwayat)
    {
        // Foto benih milik petani lain tidak boleh terbuka walau id-nya ditebak.
        abort_if($riwayat->user_id !== $request->user()->id, 404);

        return Storage::disk('public')->response($riwayat->path_gambar);
    }

    private function format(RiwayatKlasifikasi $riwayat): array
    {
        return [
            'id' => $riwayat->id,
            'hasil_prediksi' => $riwayat->hasil_prediksi,
            'skor_kepercayaan' => (float) $riwayat->skor_kepercayaan,
            'waktu' => $riwayat->created_at->toIso8601String(),
            'url_gambar' => route('api.riwayat.gambar', $riwayat),
        ];
    }
}
