<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Services\UnggahanBertahap;
use Illuminate\Http\Request;

// Endpoint untuk skrip public/js/unggah-bertahap.js.
class UnggahanController extends Controller
{
    public function __construct(private UnggahanBertahap $unggahan)
    {
    }

    public function mulai(Request $request)
    {
        $data = $request->validate([
            'nama' => ['required', 'string', 'max:200', 'ends_with:.keras'],
            'ukuran' => ['required', 'integer', 'min:1', 'max:' . UnggahanBertahap::UKURAN_MAKS],
            'sidik' => ['required', 'string', 'size:64', 'alpha_num'],
        ], [
            'nama.ends_with' => 'Pilih berkas model berformat .keras.',
            'ukuran.max' => 'Ukuran model maksimal 400 MB.',
        ]);

        return response()->json($this->unggahan->mulai($request->user()->id, $data['nama'], (int) $data['ukuran'], $data['sidik']));
    }

    public function status(Request $request, string $id)
    {
        $info = $this->unggahan->info($id, $request->user()->id);
        abort_if($info === null, 404);

        return response()->json($info);
    }

    public function potongan(Request $request, string $id, int $indeks)
    {
        $info = $this->unggahan->info($id, $request->user()->id);
        abort_if($info === null, 404);
        abort_unless($indeks >= 0 && $indeks < $info['jumlah_potongan'], 422, 'Nomor potongan tidak valid.');

        $isi = $request->getContent();
        if (strlen($isi) !== $this->unggahan->ukuranPotongan($info, $indeks)) {
            return response()->json(['message' => 'Ukuran potongan tidak sesuai. Potongan akan dikirim ulang.'], 422);
        }
        // Isi potongan dicocokkan dengan SHA-256 dari browser, supaya potongan yang rusak di jalan tidak tersimpan.
        if (! hash_equals(hash('sha256', $isi), strtolower((string) $request->header('X-Sha256')))) {
            return response()->json(['message' => 'Isi potongan rusak saat dikirim. Potongan akan dikirim ulang.'], 422);
        }

        $info = $this->unggahan->simpanPotongan($info, $indeks, $isi);

        return response()->json(['diterima' => count($info['diterima']), 'jumlah_potongan' => $info['jumlah_potongan']]);
    }

    public function batal(Request $request, string $id)
    {
        abort_if($this->unggahan->info($id, $request->user()->id) === null, 404);
        $this->unggahan->hapus($id);

        return response()->json(['message' => 'Unggahan dibatalkan.']);
    }
}
