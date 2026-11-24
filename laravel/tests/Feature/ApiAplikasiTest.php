<?php

namespace Tests\Feature;

use App\Models\RiwayatKlasifikasi;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

// API untuk aplikasi Flutter petani. Flask diganti Http::fake, jadi tes ini tidak butuh model.
class ApiAplikasiTest extends TestCase
{
    use RefreshDatabase;

    private function petani(): User
    {
        return User::factory()->create(['email' => 'petani@benih.test', 'password' => '12345678']);
    }

    public function test_petani_bisa_masuk_dan_mendapat_token(): void
    {
        $this->petani();

        $this->postJson('/api/masuk', ['email' => 'petani@benih.test', 'password' => '12345678'])
            ->assertOk()
            ->assertJsonStructure(['token', 'pengguna' => ['id', 'nama', 'email']]);
    }

    public function test_kata_sandi_salah_ditolak(): void
    {
        $this->petani();

        $this->postJson('/api/masuk', ['email' => 'petani@benih.test', 'password' => 'salah'])
            ->assertStatus(401)
            ->assertJson(['message' => 'Login gagal. Email atau kata sandi salah.']);
    }

    public function test_admin_tidak_bisa_masuk_lewat_aplikasi(): void
    {
        User::factory()->create(['email' => 'admin@benih.test', 'password' => '12345678', 'role' => 'Admin']);

        $this->postJson('/api/masuk', ['email' => 'admin@benih.test', 'password' => '12345678'])
            ->assertStatus(403);
    }

    public function test_tanpa_token_mendapat_pesan_indonesia(): void
    {
        $this->getJson('/api/riwayat')
            ->assertStatus(401)
            ->assertJson(['message' => 'Sesi berakhir. Silakan masuk lagi.']);
    }

    public function test_klasifikasi_menyimpan_riwayat(): void
    {
        Storage::fake('public');
        Http::fake(['*/predict' => Http::response(['status' => 'sukses', 'prediksi' => 'Layak', 'skor_kepercayaan' => 97.31])]);
        $petani = $this->petani();

        $this->actingAs($petani, 'sanctum')
            ->post('/api/klasifikasi', ['gambar' => UploadedFile::fake()->image('benih.jpg', 640, 480)], ['Accept' => 'application/json'])
            ->assertCreated()
            ->assertJsonPath('data.hasil_prediksi', 'Layak')
            ->assertJsonPath('data.skor_kepercayaan', 97.31);

        $this->assertSame(1, RiwayatKlasifikasi::where('user_id', $petani->id)->count());
    }

    public function test_benih_tidak_terdeteksi_meneruskan_pesan_flask(): void
    {
        Storage::fake('public');
        Http::fake(['*/predict' => Http::response(['status' => 'gagal', 'pesan' => 'Benih tidak terdeteksi.'], 422)]);

        $this->actingAs($this->petani(), 'sanctum')
            ->post('/api/klasifikasi', ['gambar' => UploadedFile::fake()->image('benih.jpg')], ['Accept' => 'application/json'])
            ->assertStatus(422)
            ->assertJson(['message' => 'Benih tidak terdeteksi.']);
    }

    public function test_berkas_bukan_citra_ditolak(): void
    {
        $this->actingAs($this->petani(), 'sanctum')
            ->post('/api/klasifikasi', ['gambar' => UploadedFile::fake()->create('catatan.pdf', 10, 'application/pdf')], ['Accept' => 'application/json'])
            ->assertStatus(422)
            ->assertJsonPath('errors.gambar.0', 'Berkas tidak valid. Unggah citra berformat JPEG atau PNG.');
    }

    public function test_riwayat_hanya_milik_sendiri(): void
    {
        $petani = $this->petani();
        $lain = User::factory()->create();
        $milikLain = RiwayatKlasifikasi::create([
            'user_id' => $lain->id, 'path_gambar' => 'riwayat/a.jpg', 'hasil_prediksi' => 'Layak', 'skor_kepercayaan' => 90,
        ]);
        RiwayatKlasifikasi::create([
            'user_id' => $petani->id, 'path_gambar' => 'riwayat/b.jpg', 'hasil_prediksi' => 'Tidak Layak', 'skor_kepercayaan' => 88.5,
        ]);

        $this->actingAs($petani, 'sanctum')->getJson('/api/riwayat')
            ->assertOk()
            ->assertJsonPath('total', 1)
            ->assertJsonPath('data.0.hasil_prediksi', 'Tidak Layak');

        $this->actingAs($petani, 'sanctum')->getJson("/api/riwayat/{$milikLain->id}/gambar")->assertNotFound();
    }

    public function test_deteksi_meneruskan_kotak_benih_tanpa_menyimpan_riwayat(): void
    {
        Http::fake(['*/deteksi' => Http::response(['status' => 'sukses', 'lebar' => 3000, 'tinggi' => 1688, 'benih' => [
            ['x' => 0.1, 'y' => 0.2, 'w' => 0.2, 'h' => 0.3, 'peluang_layak' => 0.51, 'prediksi' => 'Layak'],
        ]])]);

        $this->actingAs($this->petani(), 'sanctum')
            ->post('/api/deteksi', ['frame' => UploadedFile::fake()->image('frame.jpg', 1920, 1080)], ['Accept' => 'application/json'])
            ->assertOk()
            ->assertJsonPath('benih.0.peluang_layak', 0.51)
            ->assertJsonPath('benih.0.prediksi', 'Layak');

        $this->assertDatabaseCount('riwayat_klasifikasi', 0);
    }

    public function test_login_berulang_tidak_menghabiskan_jatah_lupa_sandi(): void
    {
        $this->petani();
        for ($i = 0; $i < 6; $i++) {
            $this->postJson('/api/login', ['email' => 'petani@benih.test', 'password' => 'salah'])->assertStatus(401);
        }

        $this->postJson('/api/lupa-sandi', ['email' => 'tidak.ada@benih.test'])->assertStatus(422);
    }

    public function test_mode_kamera_tidak_menghabiskan_jatah_klasifikasi(): void
    {
        Storage::fake('public');
        Http::fake([
            '*/deteksi' => Http::response(['status' => 'sukses', 'benih' => []]),
            '*/predict' => Http::response(['status' => 'sukses', 'prediksi' => 'Layak', 'skor_kepercayaan' => 97.31]),
        ]);
        $petani = $this->petani();
        $frame = UploadedFile::fake()->image('frame.jpg', 64, 64);
        for ($i = 0; $i < 31; $i++) {
            $this->actingAs($petani, 'sanctum')
                ->post('/api/deteksi', ['frame' => $frame], ['Accept' => 'application/json'])->assertOk();
        }

        $this->actingAs($petani, 'sanctum')
            ->post('/api/klasifikasi', ['gambar' => UploadedFile::fake()->image('benih.jpg')], ['Accept' => 'application/json'])
            ->assertCreated();
    }

    public function test_keluar_menghapus_token(): void
    {
        $this->petani();
        $token = $this->postJson('/api/masuk', ['email' => 'petani@benih.test', 'password' => '12345678'])->json('token');

        $this->withToken($token)->postJson('/api/keluar')->assertOk();

        $this->assertDatabaseCount('personal_access_tokens', 0);
    }
}
