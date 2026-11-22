@extends('auth.kerangka')
@section('judul', 'Login')
@section('isi')
    <form method="POST" action="{{ url('/login') }}">
        @csrf
        <label for="email">Email</label>
        <input type="email" id="email" name="email" value="{{ old('email') }}" autocomplete="username" required autofocus>

        @include('auth._sandi', ['id' => 'password', 'label' => 'Kata sandi', 'isiOtomatis' => 'current-password'])

        <p class="tautan-kanan"><a href="{{ route('password.request') }}">Lupa kata sandi?</a></p>

        <button type="submit" class="tombol">Masuk</button>
    </form>
@endsection
