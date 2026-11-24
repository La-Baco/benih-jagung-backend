<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ $judul }}</title>
    <link rel="preload" href="{{ asset('fonts/plus-jakarta-sans-latin-wght.woff2') }}" as="font" type="font/woff2" crossorigin>
    <link rel="stylesheet" href="{{ asset('css/app.css') }}?v={{ filemtime(public_path('css/app.css')) }}">
</head>
<body>
<main class="halaman-login">
    <div class="kotak-login">
        <h1>{{ $judul }}</h1>
        <p>{{ $pesan }}</p>
        <a href="{{ url('/') }}" class="tombol">{{ $tombol ?? 'Kembali ke dashboard' }}</a>
    </div>
</main>
</body>
</html>
