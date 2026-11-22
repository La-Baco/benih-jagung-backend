<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class LoginController extends Controller
{
    public function create()
    {
        return view('auth.login');
    }

    public function store(Request $request)
    {
        $data = $request->validate([
            'email' => ['required', 'email'],
            'password' => ['required'],
        ], [
            'email.required' => 'Email wajib diisi.',
            'email.email' => 'Format email tidak valid.',
            'password.required' => 'Kata sandi wajib diisi.',
        ]);

        if (! Auth::attempt($data)) {
            return back()
                ->withErrors(['email' => 'Login gagal. Email atau kata sandi salah.'])
                ->onlyInput('email');
        }

        // Website hanya untuk admin (BAB III); petani memakai aplikasi Android.
        if (Auth::user()->role !== 'Admin') {
            Auth::logout();

            return back()
                ->withErrors(['email' => 'Akun petani dipakai di aplikasi Android, bukan di website.'])
                ->onlyInput('email');
        }

        $request->session()->regenerate();

        return redirect('/');
    }

    public function destroy(Request $request)
    {
        Auth::logout();
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return redirect()->route('login');
    }
}
