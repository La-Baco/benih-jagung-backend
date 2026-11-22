<?php

use App\Http\Middleware\CekRole;
use Illuminate\Auth\AuthenticationException;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Exceptions\PostTooLargeException;
use Illuminate\Http\Exceptions\ThrottleRequestsException;
use Illuminate\Http\Request;
use Symfony\Component\HttpKernel\Exception\NotFoundHttpException;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        api: __DIR__.'/../routes/api.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->alias([
            'role' => CekRole::class,
        ]);
        $middleware->redirectGuestsTo('/login');
        $middleware->redirectUsersTo('/');
        // Aplikasi berada di belakang nginx VPS, jadi alamat https asli dibaca dari header proxy.
        $middleware->trustProxies(at: '*');
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        // Aplikasi Flutter selalu menerima JSON, walau lupa mengirim header Accept.
        $exceptions->shouldRenderJsonWhen(fn (Request $request) => $request->is('api/*') || $request->expectsJson());

        $exceptions->render(function (AuthenticationException $e, Request $request) {
            if ($request->is('api/*')) {
                return response()->json(['message' => 'Sesi berakhir. Silakan masuk lagi.'], 401);
            }
        });

        $exceptions->render(function (ThrottleRequestsException $e, Request $request) {
            if ($request->is('api/*')) {
                return response()->json(['message' => 'Terlalu banyak permintaan. Tunggu satu menit lalu coba lagi.'], 429);
            }
        });

        $exceptions->render(function (NotFoundHttpException $e, Request $request) {
            if ($request->is('api/*')) {
                return response()->json(['message' => 'Data tidak ditemukan.'], 404);
            }
        });

        // Foto di atas post_max_size ditolak sebelum sesi dimulai, jadi pesannya dibawa lewat URL, bukan lewat sesi.
        $exceptions->render(function (PostTooLargeException $e, Request $request) {
            if ($request->is('api/*')) {
                return response()->json(['message' => 'Ukuran berkas maksimal 10 MB.'], 413);
            }
            if ($request->is('admin/*')) {
                return redirect()->route('admin.dataset.index', ['galat' => 'ukuran']);
            }

            return redirect()->route('klasifikasi', ['galat' => 'ukuran']);
        });
    })->create();
