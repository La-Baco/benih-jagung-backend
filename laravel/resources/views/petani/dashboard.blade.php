@extends('layouts.app')

@section('judul', 'Dashboard')

@section('konten')
    <div class="ringkasan">
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

    <div class="kotak">
        <h2>Klasifikasi terakhir</h2>
        <div class="tabel-wrap">
            <table>
                <thead>
                <tr>
                    <th>Waktu</th>
                    <th>Citra</th>
                    <th>Hasil prediksi</th>
                    <th>Skor kepercayaan</th>
                </tr>
                </thead>
                <tbody>
                @forelse ($terakhir as $item)
                    <tr>
                        <td>{{ $item->created_at->format('d/m/Y H:i') }}</td>
                        <td><img src="{{ asset('storage/' . $item->path_gambar) }}" alt="Citra benih"></td>
                        <td class="{{ $item->hasil_prediksi === 'Layak' ? 'hasil-layak' : 'hasil-tidak-layak' }}">{{ $item->hasil_prediksi }}</td>
                        <td>{{ number_format($item->skor_kepercayaan, 2, ',', '.') }}%</td>
                    </tr>
                @empty
                    <tr><td colspan="4" class="kosong">Belum ada klasifikasi.</td></tr>
                @endforelse
                </tbody>
            </table>
        </div>
        <div class="baris-tombol" style="margin: 16px 0 0">
            <a href="{{ route('klasifikasi') }}" class="tombol">Klasifikasi citra baru</a>
        </div>
    </div>
@endsection
