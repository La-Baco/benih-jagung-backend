<?php

namespace App\Http\Controllers;

use App\Models\RiwayatKlasifikasi;
use App\Models\User;
use Illuminate\Http\Request;

class DashboardController extends Controller
{
    public function petani(Request $request)
    {
        $riwayat = RiwayatKlasifikasi::where('user_id', $request->user()->id);

        return view('petani.dashboard', [
            'jumlah' => (clone $riwayat)->count(),
            'jumlahLayak' => (clone $riwayat)->where('hasil_prediksi', 'Layak')->count(),
            'jumlahTidakLayak' => (clone $riwayat)->where('hasil_prediksi', 'Tidak Layak')->count(),
            'jumlahBukan' => (clone $riwayat)->where('hasil_prediksi', RiwayatKlasifikasi::BUKAN_KETAN)->count(),
            'terakhir' => (clone $riwayat)->latest()->take(5)->get(),
        ]);
    }

    public function admin()
    {
        return view('admin.dashboard', [
            'jumlahPengguna' => User::count(),
            'jumlah' => RiwayatKlasifikasi::count(),
            'jumlahLayak' => RiwayatKlasifikasi::where('hasil_prediksi', 'Layak')->count(),
            'jumlahTidakLayak' => RiwayatKlasifikasi::where('hasil_prediksi', 'Tidak Layak')->count(),
            'jumlahBukan' => RiwayatKlasifikasi::where('hasil_prediksi', RiwayatKlasifikasi::BUKAN_KETAN)->count(),
        ]);
    }
}
