<?php

namespace App\Http\Controllers;

use App\Models\RiwayatKlasifikasi;
use Illuminate\Http\Request;

class RiwayatController extends Controller
{
    public function index(Request $request)
    {
        $query = RiwayatKlasifikasi::with('user')->latest();

        // Petani hanya melihat riwayat miliknya, admin melihat seluruh pengguna.
        if ($request->user()->role === 'Petani') {
            $query->where('user_id', $request->user()->id);
        }

        return view('riwayat.index', [
            'riwayat' => $query->paginate(10),
        ]);
    }
}
