{{-- Foto dengan bounding box setiap objek yang terdeteksi (kolom objek, koordinat 0-1). --}}
<div class="{{ $kecil ? 'bingkai-objek bingkai-kecil' : 'bingkai-objek gambar-hasil' }}">
    <img src="{{ asset('storage/' . $item->path_gambar) }}" alt="Citra objek yang diklasifikasikan">
    @foreach ($item->objek ?? [] as $o)
        <span class="kotak-objek {{ $o['prediksi'] === 'Layak' ? 'kotak-layak' : ($o['prediksi'] === 'Tidak Layak' ? 'kotak-tidak-layak' : 'kotak-bukan') }}"
              style="left: {{ $o['x'] * 100 }}%; top: {{ $o['y'] * 100 }}%; width: {{ $o['w'] * 100 }}%; height: {{ $o['h'] * 100 }}%"
              title="{{ $o['prediksi'] }} ({{ number_format($o['skor_kepercayaan'], 2, ',', '.') }}%)">
            @unless ($kecil)
                <span class="label-objek">{{ $o['prediksi'] }}</span>
            @endunless
        </span>
    @endforeach
</div>
