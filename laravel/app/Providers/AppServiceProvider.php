<?php

namespace App\Providers;

use Illuminate\Auth\Notifications\ResetPassword;
use Illuminate\Notifications\Messages\MailMessage;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        // Email lupa kata sandi dalam bahasa Indonesia. Tautannya membuka halaman atur ulang di website,
        // baik permintaan datang dari website maupun dari aplikasi Android.
        ResetPassword::toMailUsing(function ($pengguna, string $token) {
            $tautan = route('password.reset', ['token' => $token, 'email' => $pengguna->email]);
            $menit = config('auth.passwords.users.expire');

            return (new MailMessage)
                ->subject('Atur ulang kata sandi')
                ->greeting('Halo, '.$pengguna->nama)
                ->line('Kami menerima permintaan untuk mengatur ulang kata sandi akun Anda.')
                ->action('Atur ulang kata sandi', $tautan)
                ->line("Tautan ini berlaku {$menit} menit.")
                ->line('Abaikan email ini bila Anda tidak memintanya.')
                ->salutation('Klasifikasi Benih Jagung Ketan Putih');
        });
    }
}
