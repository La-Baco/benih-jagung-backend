<?php

namespace App\Http\Controllers\Admin;

use App\Exceptions\PrediksiGagal;
use App\Http\Controllers\Controller;
use App\Services\LayananAdminFlask;
use Illuminate\Http\Request;

class DatasetController extends Controller
{
    public function __construct(private LayananAdminFlask $flask)
    {
    }

    public function index(Request $request)
    {
        $kelas = $request->query('kelas', 'layak_tanam');
        abort_unless(in_array($kelas, ['layak_tanam', 'tidak_layak_tanam'], true), 404);

        try {
            $ringkasan = $this->flask->ambil('/dataset')['kelas'];
            $isi = $this->flask->ambil("/dataset/{$kelas}", ['halaman' => max(1, (int) $request->query('halaman', 1))]);
        } catch (PrediksiGagal $e) {
            return view('admin.dataset.index', ['galat' => $e->getMessage(), 'kelas' => $kelas]);
        }

        return view('admin.dataset.index', [
            'galat' => null,
            'kelas' => $kelas,
            'ringkasan' => $ringkasan,
            'isi' => $isi,
            'halamanTerakhir' => max(1, (int) ceil($isi['total'] / $isi['per_halaman'])),
        ]);
    }

    public function store(Request $request, string $kelas)
    {
        $request->validate([
            'gambar' => ['required', 'array', 'max:20'],
            'gambar.*' => ['file', 'mimes:jpg,jpeg,png', 'max:10240'],
        ], [
            'gambar.required' => 'Pilih minimal satu foto.',
            'gambar.max' => 'Maksimal 20 foto dalam satu kali unggah.',
            'gambar.*.file' => 'Ada berkas yang tidak valid.',
            'gambar.*.mimes' => 'Semua berkas harus berformat JPEG atau PNG.',
            'gambar.*.max' => 'Ukuran setiap foto maksimal 10 MB.',
            'gambar.*.uploaded' => 'Ada foto yang gagal diunggah. Periksa ukurannya (maksimal 10 MB).',
        ]);

        try {
            $hasil = $this->flask->unggah("/dataset/{$kelas}", $request->file('gambar'));
        } catch (PrediksiGagal $e) {
            if ($request->wantsJson()) {
                return response()->json(['message' => $e->getMessage()], 503);
            }

            return back()->withErrors(['gambar' => $e->getMessage()]);
        }

        $pesan = count($hasil['disimpan']) . ' foto ditambahkan ke dataset.';
        if ($hasil['disimpan']) {
            $pesan .= ' Nama berkas: ' . implode(', ', $hasil['disimpan']) . '.';
        }
        session()->flash('pesan', $pesan);
        session()->flash('ditolak', $hasil['ditolak']);
        $tujuan = route('admin.dataset.index', ['kelas' => $kelas]);

        // Formulir dikirim lewat skrip (supaya ada progress bar); skrip lalu membuka alamat ini.
        if ($request->wantsJson()) {
            return response()->json(['alamat' => $tujuan]);
        }

        return redirect()->to($tujuan);
    }

    public function unduhTambahan()
    {
        try {
            $respon = $this->flask->kirim('GET', '/dataset/tambahan.zip');
        } catch (PrediksiGagal $e) {
            return back()->withErrors(['gambar' => $e->getMessage()]);
        }
        abort_unless($respon->successful(), 503);

        return response($respon->body(), 200, [
            'Content-Type' => 'application/zip',
            'Content-Disposition' => $respon->header('Content-Disposition'),
        ]);
    }

    public function destroy(string $kelas, string $nama)
    {
        try {
            $this->flask->pastikanBerhasil($this->flask->kirim('DELETE', "/dataset/{$kelas}/{$nama}"));
        } catch (PrediksiGagal $e) {
            return back()->withErrors(['gambar' => $e->getMessage()]);
        }

        return back()->with('pesan', "{$nama} dihapus dari dataset.");
    }

    public function gambar(string $kelas, string $nama)
    {
        return $this->flask->gambar("/dataset/{$kelas}/{$nama}/kecil");
    }
}
