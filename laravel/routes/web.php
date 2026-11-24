<?php

use App\Http\Controllers\Admin\DatasetController;
use App\Http\Controllers\Admin\ModelController;
use App\Http\Controllers\Admin\UnggahanController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\KlasifikasiController;
use App\Http\Controllers\LoginController;
use App\Http\Controllers\LupaSandiController;
use App\Http\Controllers\PenggunaController;
use App\Http\Controllers\RiwayatController;
use Illuminate\Support\Facades\Route;

Route::middleware('guest')->group(function () {
    Route::get('/login', [LoginController::class, 'create'])->name('login');
    Route::post('/login', [LoginController::class, 'store']);

    Route::get('/lupa-sandi', [LupaSandiController::class, 'create'])->name('password.request');
    Route::post('/lupa-sandi', [LupaSandiController::class, 'store'])->middleware('throttle:6,1,lupa-sandi-web')->name('password.email');
    Route::get('/reset-sandi/{token}', [LupaSandiController::class, 'edit'])->name('password.reset');
    Route::post('/reset-sandi', [LupaSandiController::class, 'update'])->middleware('throttle:10,1,reset-sandi')->name('password.update');
    Route::get('/reset-sandi-selesai', [LupaSandiController::class, 'selesai'])->name('password.selesai');
});

Route::middleware('auth')->group(function () {
    Route::get('/', function () {
        return auth()->user()->role === 'Admin'
            ? redirect()->route('admin.dashboard')
            : redirect()->route('dashboard');
    });

    Route::post('/logout', [LoginController::class, 'destroy'])->name('logout');
    Route::get('/riwayat', [RiwayatController::class, 'index'])->name('riwayat');

    Route::middleware('role:Petani')->group(function () {
        Route::get('/dashboard', [DashboardController::class, 'petani'])->name('dashboard');
        Route::get('/klasifikasi', [KlasifikasiController::class, 'create'])->name('klasifikasi');
        Route::post('/klasifikasi', [KlasifikasiController::class, 'store']);
    });

    Route::middleware('role:Admin')->prefix('admin')->name('admin.')->group(function () {
        Route::get('/dashboard', [DashboardController::class, 'admin'])->name('dashboard');
        Route::resource('pengguna', PenggunaController::class)
            ->except('show')
            ->parameters(['pengguna' => 'pengguna']);

        // Nama kelas dan berkas dibatasi pola, karena keduanya diteruskan ke alamat Flask.
        Route::pattern('kelas', 'layak_tanam|tidak_layak_tanam');
        Route::pattern('nama', '[a-z_]+_[0-9]+\.jpg');

        Route::get('/dataset', [DatasetController::class, 'index'])->name('dataset.index');
        Route::get('/dataset/tambahan.zip', [DatasetController::class, 'unduhTambahan'])->name('dataset.unduh');
        Route::post('/dataset/{kelas}', [DatasetController::class, 'store'])->name('dataset.store');
        Route::delete('/dataset/{kelas}/{nama}', [DatasetController::class, 'destroy'])->name('dataset.destroy');
        Route::get('/dataset/{kelas}/{nama}/gambar', [DatasetController::class, 'gambar'])->name('dataset.gambar');

        Route::get('/model', [ModelController::class, 'index'])->name('model.index');
        Route::post('/model', [ModelController::class, 'store'])->name('model.store');
        Route::post('/model/aktif', [ModelController::class, 'aktifkan'])->name('model.aktifkan');
        Route::delete('/model/{id}', [ModelController::class, 'destroy'])
            ->where('id', '[0-9]{8}-[0-9]{6}')->name('model.destroy');
        Route::get('/model/penelitian/{skenario}/kurva', [ModelController::class, 'kurvaPenelitian'])
            ->where('skenario', 's[1-4]')->name('model.kurva-penelitian');

        // Unggahan bertahap untuk berkas model (public/js/unggah-bertahap.js).
        Route::post('/unggahan', [UnggahanController::class, 'mulai'])->name('unggahan.mulai');
        Route::get('/unggahan/{id}', [UnggahanController::class, 'status'])->name('unggahan.status');
        Route::post('/unggahan/{id}/{indeks}', [UnggahanController::class, 'potongan'])
            ->whereNumber('indeks')->middleware('throttle:600,1,unggahan')->name('unggahan.potongan');
        Route::delete('/unggahan/{id}', [UnggahanController::class, 'batal'])->name('unggahan.batal');
    });
});
