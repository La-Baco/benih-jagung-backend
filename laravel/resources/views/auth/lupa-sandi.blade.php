@extends('auth.kerangka')
@section('judul', 'Lupa kata sandi')
@section('isi')
    <h2 class="judul-form">Lupa kata sandi</h2>
    <p class="keterangan-form">Masukkan email akun Anda. Tautan untuk mengatur ulang kata sandi akan dikirim ke email tersebut.</p>
    <form method="POST" action="{{ route('password.email') }}">
        @csrf
        <label for="email">Email</label>
        <input type="email" id="email" name="email" value="{{ old('email') }}" autocomplete="username" required autofocus>
        <button type="submit" class="tombol">Kirim tautan</button>
    </form>
    <p class="tautan-tengah"><a href="{{ route('login') }}">Kembali ke halaman login</a></p>
@endsection
