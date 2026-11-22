@extends('layouts.app')

@section('judul', 'Dataset Citra Benih')

@section('konten')
    @if ($galat)
        <div class="pesan-error" role="alert">{{ $galat }}</div>
    @else
        @if ($errors->any())
            <div class="pesan-error" role="alert">{{ $errors->first() }}</div>
        @elseif (request('galat') === 'ukuran')
            <div class="pesan-error" role="alert">Total unggahan terlalu besar. Kirim foto dalam beberapa kali unggah.</div>
        @endif

        @if (session('ditolak'))
            <div class="pesan-error" role="alert">
                {{ count(session('ditolak')) }} foto ditolak:
                <ul>
                    @foreach (session('ditolak') as $item)
                        <li>{{ $item['nama'] }}: {{ $item['alasan'] }}</li>
                    @endforeach
                </ul>
            </div>
        @endif

        <div class="ringkasan">
            @foreach ($ringkasan as $item)
                <div class="kotak">
                    <div class="label">Kelas {{ $item['label'] }}</div>
                    <div class="angka">{{ $item['jumlah'] }}</div>
                    <div class="catatan">
                        {{ $item['jumlah'] - $item['tambahan'] }} citra penelitian
                        @if ($item['tambahan'] > 0)
                            + {{ $item['tambahan'] }} tambahan
                        @endif
                    </div>
                </div>
            @endforeach
        </div>

        <nav class="tab" aria-label="Pilih kelas">
            @foreach ($ringkasan as $item)
                <a href="{{ route('admin.dataset.index', ['kelas' => $item['folder']]) }}"
                   @if ($item['folder'] === $kelas) class="aktif" aria-current="page" @endif>
                    {{ $item['label'] }}
                </a>
            @endforeach
        </nav>

        @php($labelKelas = collect($ringkasan)->firstWhere('folder', $kelas)['label'])

        <div class="kotak">
            <h2>Tambah foto ke kelas {{ $labelKelas }}</h2>
            <form method="POST" action="{{ route('admin.dataset.store', $kelas) }}" enctype="multipart/form-data" id="form-dataset">
                @csrf
                <label for="gambar">Foto benih (JPEG atau PNG, maksimal 20 foto, masing-masing maksimal 10 MB)</label>
                <input type="file" id="gambar" name="gambar[]" accept="image/jpeg,image/png" multiple required class="isian-berkas">
                <div class="pesan-error" id="galat-dataset" role="alert" hidden></div>
                <div id="kemajuan-dataset" class="kemajuan" hidden>
                    <progress id="batang-dataset" max="100" value="0" aria-describedby="status-dataset">0%</progress>
                    <p id="status-dataset" class="status-unggah" role="status" aria-live="polite"></p>
                </div>
                <button type="submit" class="tombol" id="tombol-unggah" data-label="Tambahkan ke kelas {{ $labelKelas }}">Tambahkan ke kelas {{ $labelKelas }}</button>
            </form>
            <p class="catatan">
                Ambil foto dengan protokol yang sama dengan penelitian: satu butir benih di atas alas hitam, difoto tegak lurus dari atas.
                Foto yang benihnya tidak terdeteksi atau sama persis dengan foto yang sudah ada akan ditolak.
                Server tidak melatih ulang model; unduh foto tambahan untuk dilatih di laptop.
            </p>
            @if (collect($ringkasan)->sum('tambahan') > 0)
                <a href="{{ route('admin.dataset.unduh') }}" class="tombol tombol-garis">Unduh {{ collect($ringkasan)->sum('tambahan') }} foto tambahan (.zip)</a>
            @endif
        </div>

        <div class="kotak">
            <h2>Isi kelas {{ $labelKelas }} ({{ $isi['total'] }} foto, terbaru di depan)</h2>

            @if ($isi['total'] === 0)
                <p class="kosong">Belum ada foto di kelas ini.</p>
            @else
                <ul class="galeri">
                    @foreach ($isi['berkas'] as $item)
                        <li>
                            <img src="{{ route('admin.dataset.gambar', [$kelas, $item['nama']]) }}"
                                 alt="Foto {{ $item['nama'] }}" width="240" height="180" loading="lazy">
                            <span class="nama-berkas">{{ $item['nama'] }}</span>
                            @if ($item['data_penelitian'])
                                <span class="catatan">Data penelitian</span>
                            @else
                                <form method="POST" action="{{ route('admin.dataset.destroy', [$kelas, $item['nama']]) }}"
                                      onsubmit="return confirm('Hapus {{ $item['nama'] }} dari dataset?')">
                                    @csrf
                                    @method('DELETE')
                                    <button type="submit" class="tombol tombol-kecil tombol-hapus">Hapus</button>
                                </form>
                            @endif
                        </li>
                    @endforeach
                </ul>

                <nav class="halaman-nav" aria-label="Halaman dataset">
                    @if ($isi['halaman'] > 1)
                        <a class="tombol tombol-kecil tombol-garis" href="{{ route('admin.dataset.index', ['kelas' => $kelas, 'halaman' => $isi['halaman'] - 1]) }}">Sebelumnya</a>
                    @endif
                    <span>Halaman {{ $isi['halaman'] }} dari {{ $halamanTerakhir }}</span>
                    @if ($isi['halaman'] < $halamanTerakhir)
                        <a class="tombol tombol-kecil tombol-garis" href="{{ route('admin.dataset.index', ['kelas' => $kelas, 'halaman' => $isi['halaman'] + 1]) }}">Berikutnya</a>
                    @endif
                </nav>
            @endif
        </div>

        <script src="{{ asset('js/unggah-dataset.js') }}" defer></script>
    @endif
@endsection
