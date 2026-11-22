@extends('layouts.app')

@php($baru = ! $pengguna->exists)

@section('judul', $baru ? 'Tambah Pengguna' : 'Ubah Pengguna')

@section('konten')
    <div class="kotak" style="max-width: 520px">
        @if ($errors->any())
            <div class="pesan-error">
                <ul>
                    @foreach ($errors->all() as $error)
                        <li>{{ $error }}</li>
                    @endforeach
                </ul>
            </div>
        @endif

        <form method="POST" action="{{ $baru ? route('admin.pengguna.store') : route('admin.pengguna.update', $pengguna) }}">
            @csrf
            @unless ($baru)
                @method('PUT')
            @endunless

            <label for="nama">Nama</label>
            <input type="text" id="nama" name="nama" value="{{ old('nama', $pengguna->nama) }}">

            <label for="email">Email</label>
            <input type="email" id="email" name="email" value="{{ old('email', $pengguna->email) }}">

            <label for="password">Kata sandi{{ $baru ? '' : ' (kosongkan jika tidak diganti)' }}</label>
            <input type="password" id="password" name="password" autocomplete="new-password">

            <label for="role">Peran</label>
            <select id="role" name="role">
                @foreach (['Petani', 'Admin'] as $peran)
                    <option value="{{ $peran }}" @selected(old('role', $pengguna->role) === $peran)>{{ $peran }}</option>
                @endforeach
            </select>

            <div class="baris-tombol">
                <button type="submit" class="tombol">{{ $baru ? 'Simpan pengguna' : 'Simpan perubahan' }}</button>
                <a href="{{ route('admin.pengguna.index') }}" class="tombol tombol-garis">Batal</a>
            </div>
        </form>
    </div>
@endsection
