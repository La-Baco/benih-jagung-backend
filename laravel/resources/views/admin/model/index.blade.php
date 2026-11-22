@extends('layouts.app')

@section('judul', 'Model Klasifikasi')

@php($persen = fn ($nilai) => number_format($nilai * 100, 2, ',', '.') . '%')

@section('konten')
    @if ($galat)
        <div class="pesan-error" role="alert">{{ $galat }}</div>
    @else
        @if ($errors->any())
            <div class="pesan-error" role="alert">{{ $errors->first() }}</div>
        @endif

        @php($aktif = $data['model_aktif'])
        @php($perangkat = $data['penelitian']['perangkat'] ?? [])
        <div class="pesan-info" role="note">
            <strong>Model dilatih di perangkat pengembang, bukan di server ini.</strong>
            Server VPS hanya menjalankan prediksi (layanan Flask). VPS ini dipakai bersama layanan lain, jadi pelatihan tidak dijalankan di sini.
            @if ($perangkat)
                Model penelitian S3 dilatih di laptop peneliti: {{ $perangkat['Prosesor'] ?? '-' }}, RAM {{ str_replace('.', ',', $perangkat['RAM'] ?? '-') }},
                {{ $perangkat['Sistem operasi'] ?? '-' }}, TensorFlow {{ $perangkat['TensorFlow'] ?? '-' }}, GPU {{ $perangkat['GPU'] ?? '-' }},
                {{ $data['penelitian']['epoch'] }} epoch dalam {{ number_format($data['penelitian']['durasi_menit'], 1, ',', '.') }} menit.
            @endif
            Model yang diunggah lewat halaman ini juga harus dilatih di perangkat pengembang; server tidak dapat memeriksa di mana sebuah model dilatih.
        </div>

        <div class="kotak">
            <h2>Model yang dipakai layanan prediksi</h2>
            <p class="model-aktif">{{ $aktif['nama'] ?? 'Model penelitian S3' }}</p>
            @if ($aktif['sumber'] === 'penelitian')
                <p class="catatan">Model S3 dari skripsi (selisih latih-uji terkecil, BAB IV), dilatih di laptop peneliti.</p>
            @else
                <p class="catatan">Model unggahan, dipakai sejak {{ $aktif['diaktifkan'] }}.</p>
                <form method="POST" action="{{ route('admin.model.aktifkan') }}">
                    @csrf
                    <input type="hidden" name="sumber" value="penelitian">
                    <button type="submit" class="tombol tombol-garis">Kembali ke model penelitian</button>
                </form>
            @endif
        </div>

        <div class="dua-kolom">
            <div class="kotak">
                <h2>Unggah model dari laptop</h2>

                @foreach ($tertunda as $item)
                    <div class="pesan-info" role="status">
                        Unggahan <strong>{{ $item['nama'] }}</strong> berhenti di {{ $item['persen'] }}%.
                        Pilih berkas yang sama di bawah untuk melanjutkan dari situ.
                    </div>
                @endforeach

                <noscript><div class="pesan-error">Unggahan model membutuhkan JavaScript.</div></noscript>

                <form method="POST" action="{{ route('admin.model.store') }}" id="form-model"
                      data-alamat-unggahan="{{ url('/admin/unggahan') }}">
                    @csrf
                    <input type="hidden" name="unggahan_id" id="unggahan_id">

                    <label for="berkas">Berkas model (.keras, maksimal 400 MB)</label>
                    <input type="file" id="berkas" accept=".keras" class="isian-berkas">

                    <label for="keterangan">Keterangan</label>
                    <input type="text" id="keterangan" name="keterangan" maxlength="200" required
                           value="{{ old('keterangan') }}" placeholder="Contoh: S3 latih ulang Des 2026">

                    <label for="sisi_potong">Nilai S (sisi potong, piksel)</label>
                    <input type="number" id="sisi_potong" name="sisi_potong" min="224" max="3000" required
                           value="{{ old('sisi_potong', $data['sisi_potong_aktif']) }}" aria-describedby="petunjuk-s">
                    <p class="catatan" id="petunjuk-s">Ambil dari <code>model/prapemrosesan.json</code> hasil <code>02_prapemrosesan_dataset.py</code> di laptop. Model penelitian memakai 1.330.</p>

                    <div class="pesan-error" id="galat-unggah" role="alert" hidden></div>

                    <div id="kemajuan" class="kemajuan" hidden>
                        <progress id="batang-unggah" max="100" value="0" aria-describedby="rincian-unggah">0%</progress>
                        <p id="status-unggah" class="status-unggah" role="status" aria-live="polite"></p>
                        <p id="rincian-unggah" class="catatan"></p>
                        <div class="baris-tombol">
                            <button type="button" class="tombol tombol-garis tombol-kecil" id="tombol-jeda" disabled>Jeda</button>
                            <button type="button" class="tombol tombol-hapus tombol-kecil" id="tombol-batal" disabled>Batalkan</button>
                        </div>
                    </div>

                    <button type="submit" class="tombol" id="tombol-simpan">Unggah dan periksa model</button>
                </form>
            </div>

            <div class="kotak">
                <h2>Cara menyiapkan model</h2>
                <ol class="langkah">
                    <li>Di laptop, latih dengan <code>04_latih.py</code> lalu pilih model dengan <code>05_evaluasi.py</code>. Hasilnya <code>model/model_akhir.keras</code>.</li>
                    <li>Foto tambahan dari menu Dataset bisa diunduh sebagai .zip untuk ikut dilatih.</li>
                    <li>Unggah berkasnya di sini. Server hanya memeriksa model dapat dimuat, menerima citra 224 x 224 x 3, dan mengeluarkan satu peluang 0-1; server tidak melatih ulang.</li>
                    <li>Model lama tetap dipakai sampai Anda menekan "Pakai model ini".</li>
                </ol>
                <p class="catatan">Unggahan dikirim per potongan 4 MB lewat tiga jalur sekaligus. Bila halaman dimuat ulang atau koneksi putus, potongan yang sudah selesai terkirim tidak hilang.</p>
            </div>
        </div>

        <div class="kotak">
            <h2>Model yang sudah diunggah</h2>
            @if (! $data['bisa_ganti_model'])
                <p class="catatan">Layanan ini berjalan dengan folder model penelitian, jadi tombol "Pakai model ini" dinonaktifkan agar model skripsi tidak tertimpa.</p>
            @endif
            <div class="tabel-wrap">
                <table>
                    <thead>
                    <tr>
                        <th>Diunggah</th>
                        <th>Keterangan</th>
                        <th>Berkas</th>
                        <th>Parameter</th>
                        <th>Ukuran</th>
                        <th>S</th>
                        <th>Aksi</th>
                    </tr>
                    </thead>
                    <tbody>
                    @forelse ($data['unggahan'] as $item)
                        <tr>
                            <td>{{ $item['diunggah'] }}{{ $item['oleh'] ? ' oleh ' . $item['oleh'] : '' }}</td>
                            <td>{{ $item['keterangan'] }}</td>
                            <td class="nama-berkas">{{ $item['nama_berkas'] }}</td>
                            <td>{{ number_format($item['jumlah_parameter'], 0, ',', '.') }}</td>
                            <td>{{ number_format($item['ukuran_mb'], 1, ',', '.') }} MB</td>
                            <td>{{ number_format($item['sisi_potong'], 0, ',', '.') }}</td>
                            <td>
                                <div class="aksi">
                                    @if ($aktif['sumber'] === $item['id'])
                                        <span class="catatan">Sedang dipakai</span>
                                    @else
                                        @if ($data['bisa_ganti_model'])
                                            <form method="POST" action="{{ route('admin.model.aktifkan') }}"
                                                  onsubmit="return confirm('Ganti model layanan prediksi dengan model ini?')">
                                                @csrf
                                                <input type="hidden" name="sumber" value="{{ $item['id'] }}">
                                                <button type="submit" class="tombol tombol-kecil">Pakai model ini</button>
                                            </form>
                                        @endif
                                        <form method="POST" action="{{ route('admin.model.destroy', $item['id']) }}"
                                              onsubmit="return confirm('Hapus model ini dari server?')">
                                            @csrf
                                            @method('DELETE')
                                            <button type="submit" class="tombol tombol-kecil tombol-hapus">Hapus</button>
                                        </form>
                                    @endif
                                </div>
                            </td>
                        </tr>
                    @empty
                        <tr><td colspan="7" class="kosong">Belum ada model yang diunggah. Layanan memakai model penelitian.</td></tr>
                    @endforelse
                    </tbody>
                </table>
            </div>
        </div>

        @if ($data['penelitian'])
            @php($penelitian = $data['penelitian'])
            <div class="kotak">
                <h2>Hasil penelitian (dilatih di laptop peneliti, BAB IV)</h2>
                <div class="tabel-wrap">
                    <table>
                        <thead>
                        <tr>
                            <th>Skenario</th>
                            <th>Blok</th>
                            <th>Batch</th>
                            <th>Parameter</th>
                            <th>Epoch</th>
                            <th>Epoch terbaik</th>
                            <th>Loss validasi</th>
                            <th>Akurasi validasi</th>
                            <th>F1 validasi</th>
                            <th>Kurva</th>
                        </tr>
                        </thead>
                        <tbody>
                        @foreach ($penelitian['skenario'] as $item)
                            <tr @if ($item['skenario'] === $penelitian['terpilih']) class="baris-terpilih" @endif>
                                <td>{{ strtoupper($item['skenario']) }}{{ $item['skenario'] === $penelitian['terpilih'] ? ' (model akhir)' : '' }}</td>
                                <td>{{ $item['jumlah_blok'] }}</td>
                                <td>{{ $item['ukuran_batch'] }}</td>
                                <td>{{ number_format($item['jumlah_parameter'], 0, ',', '.') }}</td>
                                <td>{{ $item['epoch_dijalankan'] }}</td>
                                <td>{{ $item['epoch_terbaik'] }}</td>
                                <td>{{ number_format($item['val_loss'], 4, ',', '.') }}</td>
                                <td>{{ $persen($item['val_akurasi']) }}</td>
                                <td>{{ $persen($item['val_f1']) }}</td>
                                <td><a href="{{ route('admin.model.kurva-penelitian', $item['skenario']) }}">Lihat</a></td>
                            </tr>
                        @endforeach
                        </tbody>
                    </table>
                </div>
                @php($uji = $penelitian['uji'])
                <p>
                    Data uji {{ strtoupper($penelitian['terpilih']) }} ({{ $uji['jumlah'] }} citra):
                    akurasi {{ $persen($uji['akurasi']) }}, presisi {{ $persen($uji['presisi']) }},
                    recall {{ $persen($uji['recall']) }}, F1-score {{ $persen($uji['f1']) }}
                    (TP {{ $uji['tp'] }}, FN {{ $uji['fn'] }}, FP {{ $uji['fp'] }}, TN {{ $uji['tn'] }}).
                </p>
            </div>
        @endif

        <script src="{{ asset('js/unggah-bertahap.js') }}" defer></script>
    @endif
@endsection
