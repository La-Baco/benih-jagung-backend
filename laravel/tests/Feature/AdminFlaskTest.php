<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\UnggahanBertahap;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

// Halaman admin Dataset dan Pelatihan Model. Endpoint /admin Flask diganti Http::fake.
class AdminFlaskTest extends TestCase
{
    use RefreshDatabase;

    protected function tearDown(): void
    {
        // Unggahan bertahap ditulis ke storage sungguhan; sisa tes dibersihkan.
        File::deleteDirectory(storage_path('app/unggahan'));
        parent::tearDown();
    }

    private function admin(): User
    {
        return User::factory()->create(['role' => 'Admin']);
    }

    private function ringkasanDataset(): array
    {
        return ['status' => 'sukses', 'kelas' => [
            ['folder' => 'layak_tanam', 'label' => 'Layak', 'jumlah' => 501, 'tambahan' => 1],
            ['folder' => 'tidak_layak_tanam', 'label' => 'Tidak Layak', 'jumlah' => 500, 'tambahan' => 0],
        ]];
    }

    public function test_halaman_dataset_menampilkan_isi(): void
    {
        config(['services.flask.kunci' => 'kunci-uji']);
        Http::fake([
            '*/admin/dataset/layak_tanam*' => Http::response(['status' => 'sukses', 'total' => 501, 'halaman' => 1, 'per_halaman' => 24,
                'berkas' => [['nama' => 'layak_501.jpg', 'data_penelitian' => false], ['nama' => 'layak_500.jpg', 'data_penelitian' => true]]]),
            '*/admin/dataset' => Http::response($this->ringkasanDataset()),
        ]);

        $this->actingAs($this->admin())->get('/admin/dataset')
            ->assertOk()
            ->assertSee('layak_501.jpg')
            ->assertSee('Data penelitian')
            ->assertSee('Halaman 1 dari 21');

        Http::assertSent(fn ($r) => $r->hasHeader('X-Kunci-Layanan', 'kunci-uji'));
    }

    public function test_flask_mati_menampilkan_pesan(): void
    {
        Http::fake(fn () => throw new \Illuminate\Http\Client\ConnectionException('mati'));

        $this->actingAs($this->admin())->get('/admin/dataset')
            ->assertOk()
            ->assertSee('Layanan Flask tidak dapat dihubungi');
    }

    public function test_unggah_dataset_melaporkan_foto_ditolak(): void
    {
        Http::fake(['*/admin/dataset/tidak_layak_tanam' => Http::response(['status' => 'sukses',
            'disimpan' => ['tidak_layak_501.jpg'],
            'ditolak' => [['nama' => 'gelap.jpg', 'alasan' => 'benih tidak terdeteksi']]])]);

        $this->actingAs($this->admin())
            ->post('/admin/dataset/tidak_layak_tanam', ['gambar' => [
                UploadedFile::fake()->image('a.jpg'), UploadedFile::fake()->image('gelap.jpg'),
            ]])
            ->assertRedirect('/admin/dataset?kelas=tidak_layak_tanam')
            ->assertSessionHas('pesan', '1 foto ditambahkan ke dataset. Nama berkas: tidak_layak_501.jpg.')
            ->assertSessionHas('ditolak');

        // Flask membaca kolom "gambar" (tanpa []), dan kedua foto harus ikut terkirim.
        Http::assertSent(function ($r) {
            $kolom = array_column($r->data(), 'name');

            return $kolom === ['gambar', 'gambar'];
        });
    }

    public function test_unggah_dataset_lewat_skrip_mendapat_alamat_tujuan(): void
    {
        Http::fake(['*/admin/dataset/layak_tanam' => Http::response(['status' => 'sukses',
            'disimpan' => ['layak_501.jpg'], 'ditolak' => []])]);

        $this->actingAs($this->admin())
            ->post('/admin/dataset/layak_tanam', ['gambar' => [UploadedFile::fake()->image('a.jpg')]], ['Accept' => 'application/json'])
            ->assertOk()
            ->assertJsonPath('alamat', route('admin.dataset.index', ['kelas' => 'layak_tanam']));
    }

    public function test_petani_tidak_bisa_membuka_halaman_model(): void
    {
        $this->actingAs(User::factory()->create())->get('/admin/model')->assertForbidden();
        $this->actingAs(User::factory()->create())->postJson('/admin/unggahan', [])->assertForbidden();
    }

    public function test_halaman_model_menampilkan_unggahan_tertunda(): void
    {
        Http::fake(['*/admin/model' => Http::response(['status' => 'sukses', 'model_aktif' => ['sumber' => 'penelitian', 'nama' => 'Model penelitian S2'],
            'sisi_potong_aktif' => 1330, 'unggahan' => [], 'penelitian' => null, 'bisa_ganti_model' => true])]);
        $admin = $this->admin();
        $this->actingAs($admin)->postJson('/admin/unggahan', ['nama' => 'model_s2.keras', 'ukuran' => 20 * 1024 * 1024, 'sidik' => str_repeat('a', 64)]);

        $this->actingAs($admin)->get('/admin/model')
            ->assertOk()
            ->assertSee('berhenti di 0%', false)
            ->assertSee('model_s2.keras');
    }

    public function test_unggahan_bertahap_bisa_dilanjutkan_dan_diteruskan_ke_flask(): void
    {
        Http::fake(['*/admin/model/unggah' => Http::response(['status' => 'sukses',
            'model' => ['id' => '20261114-120000', 'keterangan' => 'S2 uji', 'ukuran_mb' => 9.0]], 201)]);
        $admin = $this->admin();
        $potong = UnggahanBertahap::UKURAN_POTONGAN;
        $ukuran = $potong + 1000;
        $isi = random_bytes($ukuran);
        $awal = ['nama' => 'model.keras', 'ukuran' => $ukuran, 'sidik' => hash('sha256', 'sidik-uji')];

        $sesi = $this->actingAs($admin)->postJson('/admin/unggahan', $awal)->assertOk()->json();
        $this->assertSame(2, $sesi['jumlah_potongan']);

        // Potongan kedua dikirim lebih dulu: urutan boleh acak karena ditulis langsung ke posisinya.
        $kedua = substr($isi, $potong);
        $this->actingAs($admin)->call('POST', "/admin/unggahan/{$sesi['id']}/1", [], [], [],
            ['HTTP_X_SHA256' => hash('sha256', $kedua), 'HTTP_ACCEPT' => 'application/json', 'CONTENT_TYPE' => 'application/octet-stream'], $kedua)
            ->assertOk()->assertJsonPath('diterima', 1);

        // Isi yang rusak di jalan ditolak.
        $pertama = substr($isi, 0, $potong);
        $this->actingAs($admin)->call('POST', "/admin/unggahan/{$sesi['id']}/0", [], [], [],
            ['HTTP_X_SHA256' => str_repeat('0', 64), 'HTTP_ACCEPT' => 'application/json', 'CONTENT_TYPE' => 'application/octet-stream'], $pertama)
            ->assertStatus(422);

        // Halaman dimuat ulang: berkas yang sama melanjutkan sesi lama, potongan 1 sudah tercatat.
        $lanjut = $this->actingAs($admin)->postJson('/admin/unggahan', $awal)->json();
        $this->assertSame($sesi['id'], $lanjut['id']);
        $this->assertSame([1], $lanjut['diterima']);

        $this->actingAs($admin)->call('POST', "/admin/unggahan/{$sesi['id']}/0", [], [], [],
            ['HTTP_X_SHA256' => hash('sha256', $pertama), 'HTTP_ACCEPT' => 'application/json', 'CONTENT_TYPE' => 'application/octet-stream'], $pertama)
            ->assertOk()->assertJsonPath('diterima', 2);

        $this->actingAs($admin)
            ->post('/admin/model', ['unggahan_id' => $sesi['id'], 'keterangan' => 'S2 uji', 'sisi_potong' => 1330])
            ->assertRedirect('/admin/model')
            ->assertSessionHas('pesan');

        Http::assertSent(fn ($r) => str_ends_with($r->url(), '/admin/model/unggah'));
        $this->assertDirectoryDoesNotExist(storage_path("app/unggahan/{$sesi['id']}"));
    }

    public function test_simpan_model_ditolak_bila_unggahan_belum_lengkap(): void
    {
        Http::fake();
        $admin = $this->admin();
        $sesi = $this->actingAs($admin)->postJson('/admin/unggahan', ['nama' => 'm.keras', 'ukuran' => 5000, 'sidik' => hash('sha256', 'x')])->json();

        $this->actingAs($admin)
            ->post('/admin/model', ['unggahan_id' => $sesi['id'], 'keterangan' => 'uji', 'sisi_potong' => 1330])
            ->assertSessionHasErrors('unggahan_id');

        Http::assertNothingSent();
        $this->actingAs($admin)->deleteJson("/admin/unggahan/{$sesi['id']}")->assertOk();
    }

    public function test_berkas_selain_keras_tidak_bisa_diunggah(): void
    {
        $this->actingAs($this->admin())
            ->postJson('/admin/unggahan', ['nama' => 'model.h5', 'ukuran' => 100, 'sidik' => hash('sha256', 'x')])
            ->assertStatus(422)
            ->assertJsonPath('errors.nama.0', 'Pilih berkas model berformat .keras.');
    }

    public function test_nama_berkas_aneh_tidak_diteruskan(): void
    {
        Http::fake();

        $this->actingAs($this->admin())->get('/admin/dataset/layak_tanam/..%2F..%2Fenv/gambar')->assertNotFound();

        Http::assertNothingSent();
    }
}
