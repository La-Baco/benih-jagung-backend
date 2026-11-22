<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Password;

class SesiController extends Controller
{
    public function masuk(Request $request)
    {
        $data = $request->validate([
            'email' => ['required', 'email'],
            'password' => ['required'],
            'perangkat' => ['nullable', 'string', 'max:100'],
        ], [
            'email.required' => 'Email wajib diisi.',
            'email.email' => 'Format email tidak valid.',
            'password.required' => 'Kata sandi wajib diisi.',
        ]);

        $pengguna = User::where('email', $data['email'])->first();
        if (! $pengguna || ! Hash::check($data['password'], $pengguna->password)) {
            return response()->json(['message' => 'Login gagal. Email atau kata sandi salah.'], 401);
        }

        // Aplikasi HP hanya untuk petani. Pengelolaan pengguna, dataset, dan pelatihan ada di aplikasi web.
        if ($pengguna->role !== 'Petani') {
            return response()->json(['message' => 'Akun admin dipakai di aplikasi web, bukan di aplikasi HP.'], 403);
        }

        // Token tidak punya masa berlaku (config/sanctum.php), jadi petani cukup login sekali
        // sampai menekan Keluar.
        $token = $pengguna->createToken($data['perangkat'] ?? 'aplikasi-hp')->plainTextToken;

        return response()->json([
            'token' => $token,
            'pengguna' => $this->dataPengguna($pengguna),
        ]);
    }

    // Registrasi mandiri hanya untuk petani. Akun admin dibuat lewat seeder atau oleh admin.
    public function daftar(Request $request)
    {
        $data = $request->validate([
            'nama' => ['required', 'string', 'max:100'],
            'email' => ['required', 'email', 'max:100', 'unique:users,email'],
            'password' => ['required', 'min:8', 'confirmed'],
            'perangkat' => ['nullable', 'string', 'max:100'],
        ], [
            'nama.required' => 'Nama wajib diisi.',
            'nama.max' => 'Nama maksimal 100 karakter.',
            'email.required' => 'Email wajib diisi.',
            'email.email' => 'Format email tidak valid.',
            'email.max' => 'Email maksimal 100 karakter.',
            'email.unique' => 'Email sudah terdaftar.',
            'password.required' => 'Kata sandi wajib diisi.',
            'password.min' => 'Kata sandi minimal 8 karakter.',
            'password.confirmed' => 'Konfirmasi kata sandi tidak sama.',
        ]);

        $pengguna = User::create([
            'nama' => $data['nama'],
            'email' => $data['email'],
            'password' => $data['password'],
            'role' => 'Petani',
        ]);
        $token = $pengguna->createToken($data['perangkat'] ?? 'aplikasi-hp')->plainTextToken;

        return response()->json([
            'token' => $token,
            'pengguna' => $this->dataPengguna($pengguna),
        ], 201);
    }

    public function lupaSandi(Request $request)
    {
        $request->validate(['email' => ['required', 'email']], [
            'email.required' => 'Email wajib diisi.',
            'email.email' => 'Format email tidak valid.',
        ]);

        $status = Password::sendResetLink($request->only('email'));

        return match ($status) {
            Password::RESET_LINK_SENT => response()->json(['message' => 'Tautan atur ulang kata sandi sudah dikirim ke email Anda.']),
            Password::INVALID_USER => response()->json(['message' => 'Email tidak terdaftar.'], 422),
            Password::RESET_THROTTLED => response()->json(['message' => 'Tautan baru saja dikirim. Tunggu satu menit lalu coba lagi.'], 429),
            default => response()->json(['message' => 'Tautan gagal dikirim. Coba lagi beberapa saat.'], 500),
        };
    }

    public function saya(Request $request)
    {
        return response()->json(['pengguna' => $this->dataPengguna($request->user())]);
    }

    public function keluar(Request $request)
    {
        $request->user()->currentAccessToken()->delete();

        return response()->json(['message' => 'Berhasil keluar.']);
    }

    private function dataPengguna(User $pengguna): array
    {
        return ['id' => $pengguna->id, 'nama' => $pengguna->nama, 'email' => $pengguna->email];
    }
}
