<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Auth\Notifications\ResetPassword;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Notification;
use Tests\TestCase;

// Registrasi petani, lupa kata sandi, atur ulang kata sandi, dan login website khusus admin.
class AkunTest extends TestCase
{
    use RefreshDatabase;

    public function test_registrasi_membuat_akun_petani_dan_token(): void
    {
        $this->postJson('/api/register', [
            'nama' => 'Petani Baru',
            'email' => 'baru@benih.test',
            'password' => 'rahasia123',
            'password_confirmation' => 'rahasia123',
            // Peran dari permintaan diabaikan: registrasi selalu menghasilkan petani.
            'role' => 'Admin',
        ])->assertCreated()->assertJsonStructure(['token', 'pengguna' => ['id', 'nama', 'email']]);

        $this->assertSame('Petani', User::where('email', 'baru@benih.test')->value('role'));
    }

    public function test_registrasi_email_terdaftar_ditolak(): void
    {
        User::factory()->create(['email' => 'ada@benih.test']);

        $this->postJson('/api/register', [
            'nama' => 'X', 'email' => 'ada@benih.test', 'password' => 'rahasia123', 'password_confirmation' => 'rahasia123',
        ])->assertStatus(422)->assertJsonPath('errors.email.0', 'Email sudah terdaftar.');
    }

    public function test_registrasi_konfirmasi_beda_ditolak(): void
    {
        $this->postJson('/api/register', [
            'nama' => 'X', 'email' => 'x@benih.test', 'password' => 'rahasia123', 'password_confirmation' => 'beda12345',
        ])->assertStatus(422)->assertJsonPath('errors.password.0', 'Konfirmasi kata sandi tidak sama.');
    }

    public function test_alamat_login_dan_logout_sesuai_tabel_api(): void
    {
        User::factory()->create(['email' => 'petani@benih.test', 'password' => '12345678']);

        $token = $this->postJson('/api/login', ['email' => 'petani@benih.test', 'password' => '12345678'])
            ->assertOk()->json('token');

        $this->withToken($token)->postJson('/api/logout')->assertOk();
    }

    public function test_lupa_sandi_api_mengirim_tautan_atau_menolak_email_asing(): void
    {
        Notification::fake();
        $petani = User::factory()->create(['email' => 'petani@benih.test']);

        $this->postJson('/api/lupa-sandi', ['email' => 'petani@benih.test'])->assertOk();
        Notification::assertSentTo($petani, ResetPassword::class);

        $this->postJson('/api/lupa-sandi', ['email' => 'asing@benih.test'])
            ->assertStatus(422)->assertJson(['message' => 'Email tidak terdaftar.']);
    }

    public function test_atur_ulang_sandi_lewat_tautan_dan_tautan_kedaluwarsa_ditolak(): void
    {
        Notification::fake();
        $petani = User::factory()->create(['email' => 'petani@benih.test', 'password' => 'lama12345']);
        $petani->createToken('hp');

        $this->post('/lupa-sandi', ['email' => 'petani@benih.test']);
        $token = null;
        Notification::assertSentTo($petani, ResetPassword::class, function ($n) use (&$token) {
            $token = $n->token;

            return true;
        });

        $this->get('/reset-sandi/'.$token.'?email=petani@benih.test')->assertOk()->assertSee('Atur ulang kata sandi');
        $this->post('/reset-sandi', [
            'token' => $token, 'email' => 'petani@benih.test',
            'password' => 'baru12345', 'password_confirmation' => 'baru12345',
        ])->assertRedirect(route('password.selesai'));

        $this->assertTrue(Hash::check('baru12345', $petani->fresh()->password));
        $this->assertSame(0, $petani->tokens()->count());

        // Tautan kedua dibuat, lalu waktu dimajukan melewati 60 menit.
        $this->travel(2)->minutes();
        $this->post('/lupa-sandi', ['email' => 'petani@benih.test']);
        $tokenKedua = null;
        Notification::assertSentTo($petani, ResetPassword::class, function ($n) use (&$tokenKedua) {
            $tokenKedua = $n->token;

            return true;
        });
        $this->travel(61)->minutes();
        $this->from('/reset-sandi/'.$tokenKedua)->post('/reset-sandi', [
            'token' => $tokenKedua, 'email' => 'petani@benih.test',
            'password' => 'lagi12345', 'password_confirmation' => 'lagi12345',
        ])->assertSessionHasErrors(['email' => 'Tautan tidak berlaku atau sudah kedaluwarsa. Minta tautan baru.']);
        $this->assertTrue(Hash::check('baru12345', $petani->fresh()->password));
    }

    public function test_website_menolak_login_petani(): void
    {
        User::factory()->create(['email' => 'petani@benih.test', 'password' => '12345678', 'role' => 'Petani']);

        $this->post('/login', ['email' => 'petani@benih.test', 'password' => '12345678'])
            ->assertSessionHasErrors(['email' => 'Akun petani dipakai di aplikasi Android, bukan di website.']);
        $this->assertGuest();
    }

    public function test_halaman_login_memuat_ikon_mata_dan_tautan_lupa_sandi(): void
    {
        $this->get('/login')->assertOk()->assertSee('data-mata="password"', false)->assertSee('Lupa kata sandi?');
    }
}
