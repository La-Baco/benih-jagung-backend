<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

// Tahap penyaring objek: benda selain jagung ketan putih (misalnya kerikil) disimpan dengan
// hasil "Bukan Jagung Ketan Putih", dan bounding box setiap objek disimpan di kolom objek.
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('riwayat_klasifikasi', function (Blueprint $table) {
            $table->enum('hasil_prediksi', ['Layak', 'Tidak Layak', 'Bukan Jagung Ketan Putih'])->change();
            $table->json('objek')->nullable()->after('skor_kepercayaan');
        });
    }

    public function down(): void
    {
        Schema::table('riwayat_klasifikasi', function (Blueprint $table) {
            $table->dropColumn('objek');
        });
        DB::table('riwayat_klasifikasi')->where('hasil_prediksi', 'Bukan Jagung Ketan Putih')->delete();
        Schema::table('riwayat_klasifikasi', function (Blueprint $table) {
            $table->enum('hasil_prediksi', ['Layak', 'Tidak Layak'])->change();
        });
    }
};
