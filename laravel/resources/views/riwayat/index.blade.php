@extends('layouts.app')

@section('judul', 'Riwayat Klasifikasi')

@section('konten')
    @php($admin = auth()->user()->role === 'Admin')

    <div class="kotak">
        <div class="tabel-wrap">
            <table>
                <thead>
                <tr>
                    <th>Waktu</th>
                    @if ($admin)
                        <th>Nama pengguna</th>
                    @endif
                    <th>Citra</th>
                    <th>Hasil prediksi</th>
                    <th>Skor kepercayaan</th>
                </tr>
                </thead>
                <tbody>
                @forelse ($riwayat as $item)
                    <tr>
                        <td>{{ $item->created_at->format('d/m/Y H:i') }}</td>
                        @if ($admin)
                            <td>{{ $item->user->nama }}</td>
                        @endif
                        <td><img src="{{ asset('storage/' . $item->path_gambar) }}" alt="Citra benih"></td>
                        <td class="{{ $item->hasil_prediksi === 'Layak' ? 'hasil-layak' : 'hasil-tidak-layak' }}">{{ $item->hasil_prediksi }}</td>
                        <td>{{ number_format($item->skor_kepercayaan, 2, ',', '.') }}%</td>
                    </tr>
                @empty
                    <tr><td colspan="{{ $admin ? 5 : 4 }}" class="kosong">Belum ada riwayat klasifikasi.</td></tr>
                @endforelse
                </tbody>
            </table>
        </div>

        {{ $riwayat->links('pagination::default') }}
    </div>
@endsection
