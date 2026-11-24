<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>@yield('judul') - Klasifikasi Benih Jagung Ketan Putih</title>
    <link rel="preload" href="{{ asset('fonts/plus-jakarta-sans-latin-wght.woff2') }}" as="font" type="font/woff2" crossorigin>
    <link rel="stylesheet" href="{{ asset('css/app.css') }}?v={{ filemtime(public_path('css/app.css')) }}">
</head>
<body>
<div class="halaman-login">
    <div class="kotak-login">
        <h1>Klasifikasi Kelayakan Tanam<br>Benih Jagung Ketan Putih</h1>

        @if (session('pesan'))
            <div class="pesan-sukses" role="status">{{ session('pesan') }}</div>
        @endif
        @if ($errors->any())
            <div class="pesan-error" role="alert">{{ $errors->first() }}</div>
        @endif

        @yield('isi')
    </div>
</div>
<script>
    // Ikon mata: menampilkan dan menyembunyikan kata sandi secara bergantian.
    document.querySelectorAll('[data-mata]').forEach(function (tombol) {
        tombol.addEventListener('click', function () {
            var kolom = document.getElementById(tombol.dataset.mata);
            var tampil = kolom.type === 'password';
            kolom.type = tampil ? 'text' : 'password';
            tombol.setAttribute('aria-pressed', tampil ? 'true' : 'false');
            tombol.setAttribute('aria-label', tampil ? 'Sembunyikan kata sandi' : 'Tampilkan kata sandi');
            // Ikon berupa <svg>, yang tidak punya properti .hidden, jadi atributnya diubah langsung.
            tombol.querySelector('.mata-buka').toggleAttribute('hidden', tampil);
            tombol.querySelector('.mata-tutup').toggleAttribute('hidden', !tampil);
        });
    });
</script>
</body>
</html>
