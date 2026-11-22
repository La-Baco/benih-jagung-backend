<?php

namespace App\Http\Controllers;

use App\Exceptions\PrediksiGagal;
use App\Http\Requests\UnggahCitraRequest;
use App\Models\RiwayatKlasifikasi;
use App\Services\LayananPrediksi;

class KlasifikasiController extends Controller
{
    public function create()
    {
        $hasil = null;
        if (session('hasil_id')) {
            $hasil = RiwayatKlasifikasi::find(session('hasil_id'));
        }

        return view('petani.klasifikasi', ['hasil' => $hasil]);
    }

    public function store(UnggahCitraRequest $request, LayananPrediksi $layanan)
    {
        try {
            $riwayat = $layanan->klasifikasi($request->user(), $request->file('gambar'));
        } catch (PrediksiGagal $e) {
            return back()->withErrors(['gambar' => $e->getMessage()]);
        }

        // Di HP kartu hasil berada di bawah form, jadi halaman langsung diarahkan ke kartu itu.
        return redirect()->to(route('klasifikasi') . '#hasil')->with('hasil_id', $riwayat->id);
    }
}
