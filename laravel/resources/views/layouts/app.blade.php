<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>@yield('judul') - Klasifikasi Benih Jagung Ketan Putih</title>
    <link rel="preload" href="{{ asset('fonts/plus-jakarta-sans-latin-wght.woff2') }}" as="font" type="font/woff2" crossorigin>
    <link rel="stylesheet" href="{{ asset('css/app.css') }}?v={{ filemtime(public_path('css/app.css')) }}">
</head>
<body>
<div class="halaman">
    <aside class="menu">
        <p class="judul-aplikasi">Klasifikasi Benih<br>Jagung Ketan Putih</p>

        <nav>
            @if (auth()->user()->role === 'Admin')
                <a href="{{ route('admin.dashboard') }}" class="{{ request()->routeIs('admin.dashboard') ? 'aktif' : '' }}">Dashboard</a>
                <a href="{{ route('admin.pengguna.index') }}" class="{{ request()->routeIs('admin.pengguna.*') ? 'aktif' : '' }}">Pengguna</a>
                <a href="{{ route('admin.dataset.index') }}" class="{{ request()->routeIs('admin.dataset.*') ? 'aktif' : '' }}">Dataset</a>
                <a href="{{ route('admin.model.index') }}" class="{{ request()->routeIs('admin.model.*') ? 'aktif' : '' }}">Model</a>
            @else
                <a href="{{ route('dashboard') }}" class="{{ request()->routeIs('dashboard') ? 'aktif' : '' }}">Dashboard</a>
                <a href="{{ route('klasifikasi') }}" class="{{ request()->routeIs('klasifikasi') ? 'aktif' : '' }}">Klasifikasi</a>
            @endif
            <a href="{{ route('riwayat') }}" class="{{ request()->routeIs('riwayat') ? 'aktif' : '' }}">Riwayat</a>
            <form method="POST" action="{{ route('logout') }}">
                @csrf
                <button type="submit">Logout</button>
            </form>
        </nav>

        <div class="pengguna">
            {{ auth()->user()->nama }}<br>
            Pengguna: {{ auth()->user()->role }}
        </div>
    </aside>

    <main class="isi">
        <h1>@yield('judul')</h1>

        @if (session('pesan'))
            <div class="pesan-sukses">{{ session('pesan') }}</div>
        @endif

        @yield('konten')
    </main>
</div>
</body>
</html>
