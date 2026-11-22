{{-- Kolom kata sandi dengan ikon mata. Parameter: $id, $label, $isiOtomatis --}}
<label for="{{ $id }}">{{ $label }}</label>
<div class="kolom-sandi">
    <input type="password" id="{{ $id }}" name="{{ $id }}" autocomplete="{{ $isiOtomatis }}" required>
    <button type="button" class="tombol-mata" data-mata="{{ $id }}" aria-label="Tampilkan kata sandi" aria-pressed="false">
        <svg class="mata-buka" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="2"/></svg>
        <svg class="mata-tutup" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" hidden><path fill="none" stroke="currentColor" stroke-width="2" d="M3 3l18 18M10.6 5.1A10.9 10.9 0 0 1 12 5c7 0 11 7 11 7a18 18 0 0 1-3.2 4M6.6 6.6A18 18 0 0 0 1 12s4 7 11 7a10.9 10.9 0 0 0 5.4-1.4M9.9 9.9a3 3 0 0 0 4.2 4.2"/></svg>
    </button>
</div>
