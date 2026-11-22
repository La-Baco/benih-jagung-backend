<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Validation\Rule;

class PenggunaController extends Controller
{
    private $pesan = [
        'nama.required' => 'Nama wajib diisi.',
        'nama.max' => 'Nama maksimal 100 karakter.',
        'email.required' => 'Email wajib diisi.',
        'email.email' => 'Format email tidak valid.',
        'email.max' => 'Email maksimal 100 karakter.',
        'email.unique' => 'Email sudah digunakan.',
        'password.required' => 'Kata sandi wajib diisi.',
        'password.min' => 'Kata sandi minimal 8 karakter.',
        'role.required' => 'Peran wajib dipilih.',
        'role.in' => 'Peran tidak valid.',
    ];

    public function index()
    {
        return view('admin.pengguna.index', [
            'pengguna' => User::orderBy('role')->orderBy('nama')->get(),
        ]);
    }

    public function create()
    {
        return view('admin.pengguna.form', ['pengguna' => new User()]);
    }

    public function store(Request $request)
    {
        $data = $request->validate([
            'nama' => ['required', 'max:100'],
            'email' => ['required', 'email', 'max:100', 'unique:users,email'],
            'password' => ['required', 'min:8'],
            'role' => ['required', 'in:Admin,Petani'],
        ], $this->pesan);

        User::create($data);

        return redirect()->route('admin.pengguna.index')->with('pesan', 'Pengguna berhasil ditambahkan.');
    }

    public function edit(User $pengguna)
    {
        return view('admin.pengguna.form', ['pengguna' => $pengguna]);
    }

    public function update(Request $request, User $pengguna)
    {
        $data = $request->validate([
            'nama' => ['required', 'max:100'],
            'email' => ['required', 'email', 'max:100', Rule::unique('users', 'email')->ignore($pengguna->id)],
            'password' => ['nullable', 'min:8'],
            'role' => ['required', 'in:Admin,Petani'],
        ], $this->pesan);

        // Kata sandi hanya diganti kalau kolomnya diisi.
        if (empty($data['password'])) {
            unset($data['password']);
        }

        $pengguna->update($data);

        return redirect()->route('admin.pengguna.index')->with('pesan', 'Data pengguna berhasil diubah.');
    }

    public function destroy(Request $request, User $pengguna)
    {
        if ($pengguna->id === $request->user()->id) {
            return back()->withErrors(['hapus' => 'Akun yang sedang dipakai tidak dapat dihapus.']);
        }

        Storage::disk('public')->delete($pengguna->riwayat()->pluck('path_gambar')->all());
        $pengguna->delete();

        return redirect()->route('admin.pengguna.index')->with('pesan', 'Pengguna berhasil dihapus.');
    }
}
