@extends('layouts.app')

@section('judul', 'Dashboard')

@section('konten')
    <div class="ringkasan">
        <div class="kotak">
            <div class="label">Jumlah pengguna</div>
            <div class="angka">{{ $jumlahPengguna }}</div>
        </div>
        <div class="kotak">
            <div class="label">Jumlah klasifikasi</div>
            <div class="angka">{{ $jumlah }}</div>
        </div>
        <div class="kotak">
            <div class="label">Hasil layak</div>
            <div class="angka">{{ $jumlahLayak }}</div>
        </div>
        <div class="kotak">
            <div class="label">Hasil tidak layak</div>
            <div class="angka">{{ $jumlahTidakLayak }}</div>
        </div>
    </div>

    <div class="baris-tombol">
        <a href="{{ route('admin.pengguna.index') }}" class="tombol">Kelola pengguna</a>
        <a href="{{ route('riwayat') }}" class="tombol tombol-garis">Lihat riwayat seluruh pengguna</a>
    </div>
@endsection
