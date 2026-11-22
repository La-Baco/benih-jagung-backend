@extends('auth.kerangka')
@section('judul', 'Kata sandi tersimpan')
@section('isi')
    <div class="pesan-sukses" role="status">Kata sandi baru sudah tersimpan.</div>
    <p class="keterangan-form">Admin dapat masuk ke website dengan kata sandi baru. Petani dapat masuk kembali melalui aplikasi Android.</p>
    <p class="tautan-tengah"><a href="{{ route('login') }}">Ke halaman login website</a></p>
@endsection
