<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Password;

// Lupa kata sandi lewat tautan email. Halaman atur ulang dipakai admin dan juga petani
// yang meminta tautan dari aplikasi Android.
class LupaSandiController extends Controller
{
    public function create()
    {
        return view('auth.lupa-sandi');
    }

    public function store(Request $request)
    {
        $request->validate(['email' => ['required', 'email']], [
            'email.required' => 'Email wajib diisi.',
            'email.email' => 'Format email tidak valid.',
        ]);

        $status = Password::sendResetLink($request->only('email'));

        return match ($status) {
            Password::RESET_LINK_SENT => back()->with('pesan', 'Tautan atur ulang kata sandi sudah dikirim ke email Anda.'),
            Password::INVALID_USER => back()->withErrors(['email' => 'Email tidak terdaftar.'])->onlyInput('email'),
            Password::RESET_THROTTLED => back()->withErrors(['email' => 'Tautan baru saja dikirim. Tunggu satu menit lalu coba lagi.'])->onlyInput('email'),
            default => back()->withErrors(['email' => 'Tautan gagal dikirim. Coba lagi beberapa saat.'])->onlyInput('email'),
        };
    }

    public function edit(Request $request, string $token)
    {
        return view('auth.reset-sandi', ['token' => $token, 'email' => $request->query('email')]);
    }

    public function update(Request $request)
    {
        $data = $request->validate([
            'token' => ['required'],
            'email' => ['required', 'email'],
            'password' => ['required', 'min:8', 'confirmed'],
        ], [
            'email.required' => 'Email wajib diisi.',
            'email.email' => 'Format email tidak valid.',
            'password.required' => 'Kata sandi baru wajib diisi.',
            'password.min' => 'Kata sandi minimal 8 karakter.',
            'password.confirmed' => 'Konfirmasi kata sandi tidak sama.',
        ]);

        $status = Password::reset($data, function ($pengguna, string $sandiBaru) {
            $pengguna->forceFill(['password' => $sandiBaru])->save();
            // Token aplikasi Android yang lama dicabut, jadi HP lain harus masuk dengan sandi baru.
            $pengguna->tokens()->delete();
        });

        if ($status === Password::PASSWORD_RESET) {
            return redirect()->route('password.selesai');
        }

        $pesan = $status === Password::INVALID_USER
            ? 'Email tidak terdaftar.'
            : 'Tautan tidak berlaku atau sudah kedaluwarsa. Minta tautan baru.';

        return back()->withErrors(['email' => $pesan])->onlyInput('email');
    }

    public function selesai()
    {
        return view('auth.reset-selesai');
    }
}
