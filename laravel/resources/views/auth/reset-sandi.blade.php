@extends('auth.kerangka')
@section('judul', 'Atur ulang kata sandi')
@section('isi')
    <h2 class="judul-form">Atur ulang kata sandi</h2>
    <form method="POST" action="{{ route('password.update') }}">
        @csrf
        <input type="hidden" name="token" value="{{ $token }}">
        <label for="email">Email</label>
        <input type="email" id="email" name="email" value="{{ old('email', $email) }}" autocomplete="username" required>

        @include('auth._sandi', ['id' => 'password', 'label' => 'Kata sandi baru', 'isiOtomatis' => 'new-password'])
        @include('auth._sandi', ['id' => 'password_confirmation', 'label' => 'Konfirmasi kata sandi baru', 'isiOtomatis' => 'new-password'])

        <button type="submit" class="tombol">Simpan kata sandi</button>
    </form>
@endsection
