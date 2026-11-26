<?php

namespace App\Http\Controllers\Admin;

use App\Exceptions\PrediksiGagal;
use App\Http\Controllers\Controller;
use App\Services\LayananAdminFlask;
use App\Services\UnggahanBertahap;
use Illuminate\Http\Request;

// Model dilatih di laptop peneliti, lalu berkas .keras diunggah di sini. VPS dipakai bersama
// layanan lain, jadi server tidak menjalankan pelatihan.
class ModelController extends Controller
{
    public function __construct(private LayananAdminFlask $flask, private UnggahanBertahap $unggahan)
    {
    }

    public function index(Request $request)
    {
        try {
            $data = $this->flask->ambil('/model');
        } catch (PrediksiGagal $e) {
            return view('admin.model.index', ['galat' => $e->getMessage()]);
        }

        // Unggahan yang belum selesai ditampilkan supaya admin bisa melanjutkannya setelah halaman dimuat ulang.
        $tertunda = array_map(fn ($info) => [
            'id' => $info['id'],
            'nama' => $info['nama'],
            'ukuran' => $info['ukuran'],
            'persen' => (int) floor(count($info['diterima']) / $info['jumlah_potongan'] * 100),
        ], $this->unggahan->milik($request->user()->id));

        return view('admin.model.index', ['galat' => null, 'data' => $data, 'tertunda' => $tertunda]);
    }

    public function store(Request $request)
    {
        $data = $request->validate([
            'unggahan_id' => ['required', 'uuid'],
            'keterangan' => ['required', 'string', 'max:200'],
            'sisi_potong' => ['required', 'integer', 'between:224,3000'],
        ], [
            'unggahan_id.required' => 'Pilih berkas model dan tunggu sampai unggahan selesai.',
            'keterangan.required' => 'Keterangan model wajib diisi, misalnya "S1 dilatih ulang 1 Desember 2026".',
            'sisi_potong.required' => 'Nilai S wajib diisi.',
            'sisi_potong.between' => 'Nilai S harus 224-3000 piksel.',
        ]);

        $info = $this->unggahan->info($data['unggahan_id'], $request->user()->id);
        if ($info === null || ! $this->unggahan->lengkap($info)) {
            return back()->withInput()->withErrors(['unggahan_id' => 'Unggahan belum lengkap. Pilih berkas yang sama untuk melanjutkan.']);
        }

        try {
            $hasil = $this->flask->unggahModel($this->unggahan->pathBerkas($info['id']), $info['nama'], [
                'sisi_potong' => $data['sisi_potong'],
                'keterangan' => $data['keterangan'],
                'oleh' => $request->user()->nama,
            ]);
        } catch (PrediksiGagal $e) {
            // Berkas yang ditolak Flask (bukan model yang sesuai) dihapus, karena mengunggah ulang berkas yang sama akan ditolak lagi.
            if ($e->kodeHttp === 422 || $e->kodeHttp === 400) {
                $this->unggahan->hapus($info['id']);
            }

            return back()->withInput()->withErrors(['unggahan_id' => $e->getMessage()]);
        }

        $this->unggahan->hapus($info['id']);

        return redirect()->route('admin.model.index')
            ->with('pesan', "Model \"{$hasil['model']['keterangan']}\" tersimpan ({$hasil['model']['ukuran_mb']} MB). Tekan \"Pakai model ini\" untuk memakainya.");
    }

    public function aktifkan(Request $request)
    {
        $sumber = (string) $request->input('sumber');

        try {
            $respon = $this->flask->kirim('POST', '/model/aktif', ['sumber' => $sumber]);
            $this->flask->pastikanBerhasil($respon);
        } catch (PrediksiGagal $e) {
            return back()->withErrors(['model' => $e->getMessage()]);
        }

        return redirect()->route('admin.model.index')
            ->with('pesan', 'Layanan prediksi sekarang memakai ' . $respon->json('model_aktif.nama') . '.');
    }

    public function destroy(string $id)
    {
        try {
            $this->flask->pastikanBerhasil($this->flask->kirim('DELETE', "/model/{$id}"));
        } catch (PrediksiGagal $e) {
            return back()->withErrors(['model' => $e->getMessage()]);
        }

        return back()->with('pesan', 'Model dihapus dari server.');
    }

    public function kurvaPenelitian(string $skenario)
    {
        return $this->flask->gambar("/penelitian/{$skenario}/kurva");
    }
}
