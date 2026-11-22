@extends('layouts.app')

@section('judul', 'Kelola Pengguna')

@section('konten')
    @if ($errors->any())
        <div class="pesan-error">{{ $errors->first() }}</div>
    @endif

    <div class="baris-tombol">
        <a href="{{ route('admin.pengguna.create') }}" class="tombol">Tambah pengguna</a>
    </div>

    <div class="kotak">
        <div class="tabel-wrap">
            <table>
                <thead>
                <tr>
                    <th>Nama</th>
                    <th>Email</th>
                    <th>Peran</th>
                    <th>Aksi</th>
                </tr>
                </thead>
                <tbody>
                @foreach ($pengguna as $item)
                    <tr>
                        <td>{{ $item->nama }}</td>
                        <td>{{ $item->email }}</td>
                        <td>{{ $item->role }}</td>
                        <td>
                            <div class="aksi">
                                <a href="{{ route('admin.pengguna.edit', $item) }}" class="tombol tombol-kecil tombol-garis">Ubah</a>
                                @if ($item->id !== auth()->id())
                                    <form method="POST" action="{{ route('admin.pengguna.destroy', $item) }}"
                                          onsubmit="return confirm('Hapus pengguna {{ $item->nama }} beserta riwayatnya?')">
                                        @csrf
                                        @method('DELETE')
                                        <button type="submit" class="tombol tombol-kecil tombol-hapus">Hapus</button>
                                    </form>
                                @endif
                            </div>
                        </td>
                    </tr>
                @endforeach
                </tbody>
            </table>
        </div>
    </div>
@endsection
