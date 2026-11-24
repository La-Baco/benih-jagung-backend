<?php

use App\Http\Controllers\Api\KlasifikasiController;
use App\Http\Controllers\Api\SesiController;
use Illuminate\Support\Facades\Route;

// API untuk aplikasi Flutter petani. Semua respons berbentuk JSON.
// Alamat mengikuti Tabel REST API di BAB III; /masuk dan /keluar tetap ada untuk APK versi lama.
// Setiap throttle diberi awalan sendiri. Tanpa awalan, semua rute memakai satu penghitung per IP
// (atau per pengguna), sehingga misalnya beberapa kali login salah menghabiskan jatah lupa-sandi.
Route::post('/register', [SesiController::class, 'daftar'])->middleware('throttle:10,1,daftar');
Route::post('/login', [SesiController::class, 'masuk'])->middleware('throttle:10,1,masuk');
Route::post('/masuk', [SesiController::class, 'masuk'])->middleware('throttle:10,1,masuk');
Route::post('/lupa-sandi', [SesiController::class, 'lupaSandi'])->middleware('throttle:6,1,lupa-sandi');

Route::middleware('auth:sanctum')->group(function () {
    Route::get('/saya', [SesiController::class, 'saya']);
    Route::post('/logout', [SesiController::class, 'keluar']);
    Route::post('/keluar', [SesiController::class, 'keluar']);

    Route::middleware('role:Petani')->group(function () {
        Route::post('/klasifikasi', [KlasifikasiController::class, 'store'])->middleware('throttle:30,1,klasifikasi');
        // Mode kamera mengirim sekitar satu frame per detik.
        Route::post('/deteksi', [KlasifikasiController::class, 'deteksi'])->middleware('throttle:150,1,deteksi');
        Route::get('/riwayat', [KlasifikasiController::class, 'index']);
        Route::get('/riwayat/{riwayat}/gambar', [KlasifikasiController::class, 'gambar'])->name('api.riwayat.gambar');
    });
});
