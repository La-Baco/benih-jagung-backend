@extends('layouts.app')

@section('judul', 'Klasifikasi Citra Benih')

@section('konten')
    <div class="dua-kolom">
        <div class="kotak">
            <h2>Unggah citra benih</h2>

            @if ($errors->any())
                <div class="pesan-error">{{ $errors->first() }}</div>
            @elseif (request('galat') === 'ukuran')
                <div class="pesan-error">Ukuran berkas terlalu besar. Unggah foto maksimal 10 MB.</div>
            @endif
            <div class="pesan-error" id="pesan-ukuran" role="alert" hidden>Ukuran berkas terlalu besar. Unggah foto maksimal 10 MB.</div>

            <form method="POST" action="{{ route('klasifikasi') }}" enctype="multipart/form-data" id="form-klasifikasi">
                @csrf
                <label class="area-unggah" for="gambar">
                    Pilih berkas citra (JPEG atau PNG)
                    <input type="file" id="gambar" name="gambar" accept="image/jpeg,image/png">
                    <img id="pratinjau" alt="Pratinjau citra">
                </label>
                <button type="submit" class="tombol" id="tombol-kirim">Klasifikasikan</button>
            </form>

            <div class="petunjuk">
                <strong>Petunjuk:</strong>
                <ol>
                    <li>Satu butir benih di atas alas polos (warnanya berbeda dari benih).</li>
                    <li>Foto tegak lurus dari atas.</li>
                    <li>Tanpa lampu kilat.</li>
                </ol>
            </div>
        </div>

        <div class="kotak" id="hasil">
            <h2>Hasil klasifikasi</h2>

            @if ($hasil)
                @include('riwayat._gambar', ['item' => $hasil, 'kecil' => false])
                <p class="kelas-hasil {{ $hasil->kelasCss() }}">
                    {{ $hasil->hasil_prediksi }}
                </p>
                <div>Skor kepercayaan: {{ number_format($hasil->skor_kepercayaan, 2, ',', '.') }}%</div>
                <div class="batang"><div style="width: {{ $hasil->skor_kepercayaan }}%"></div></div>
            @else
                <p class="catatan">Hasil akan tampil di sini setelah citra diklasifikasikan.</p>
            @endif

            <p class="catatan">Sebelum dinilai kelayakannya, sistem memeriksa dulu apakah objek di foto adalah jagung ketan putih. Kerikil atau benda lain ditandai "Bukan Jagung Ketan Putih".</p>
            <p class="catatan">Hasil didasarkan pada tampilan fisik benih dan tidak menggantikan uji daya berkecambah.</p>
            <p class="catatan">Model dilatih di perangkat pengembang (laptop peneliti); server hanya menjalankan prediksi.</p>
        </div>
    </div>

    <script>
        const BATAS_UKURAN = 10 * 1024 * 1024;
        const input = document.getElementById('gambar');
        const pratinjau = document.getElementById('pratinjau');
        const pesanUkuran = document.getElementById('pesan-ukuran');

        function terlaluBesar() {
            return input.files.length > 0 && input.files[0].size > BATAS_UKURAN;
        }

        input.addEventListener('change', function () {
            pesanUkuran.hidden = !terlaluBesar();
            if (input.files.length > 0 && !terlaluBesar()) {
                pratinjau.src = URL.createObjectURL(input.files[0]);
                pratinjau.style.display = 'block';
            } else {
                pratinjau.style.display = 'none';
            }
        });

        document.getElementById('form-klasifikasi').addEventListener('submit', function (event) {
            // Foto di atas 10 MB tidak dikirim, supaya petani tidak menunggu unggahan yang pasti ditolak.
            if (terlaluBesar()) {
                event.preventDefault();
                pesanUkuran.hidden = false;
                return;
            }
            const tombol = document.getElementById('tombol-kirim');
            tombol.disabled = true;
            tombol.textContent = 'Memproses...';
        });
    </script>
@endsection
