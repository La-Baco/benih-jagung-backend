<?php

use App\Http\Controllers\Api\KlasifikasiController;
use App\Http\Controllers\Api\SesiController;
use Illuminate\Support\Facades\Route;

// API untuk aplikasi Flutter petani. Semua respons berbentuk JSON.
// Alamat mengikuti Tabel REST API di BAB III; /masuk dan /keluar tetap ada untuk APK versi lama.
Route::post('/register', [SesiController::class, 'daftar'])->middleware('throttle:10,1');
Route::post('/login', [SesiController::class, 'masuk'])->middleware('throttle:10,1');
Route::post('/masuk', [SesiController::class, 'masuk'])->middleware('throttle:10,1');
Route::post('/lupa-sandi', [SesiController::class, 'lupaSandi'])->middleware('throttle:6,1');

Route::middleware('auth:sanctum')->group(function () {
    Route::get('/saya', [SesiController::class, 'saya']);
    Route::post('/logout', [SesiController::class, 'keluar']);
    Route::post('/keluar', [SesiController::class, 'keluar']);

    Route::middleware('role:Petani')->group(function () {
        Route::post('/klasifikasi', [KlasifikasiController::class, 'store'])->middleware('throttle:30,1');
        // Mode kamera mengirim sekitar satu frame per detik.
        Route::post('/deteksi', [KlasifikasiController::class, 'deteksi'])->middleware('throttle:150,1');
        Route::get('/riwayat', [KlasifikasiController::class, 'index']);
        Route::get('/riwayat/{riwayat}/gambar', [KlasifikasiController::class, 'gambar'])->name('api.riwayat.gambar');
    });
});
