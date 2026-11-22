<?php

namespace App\Exceptions;

use RuntimeException;

// Pesan dari exception ini langsung ditampilkan ke pengguna, jadi selalu ditulis dalam bahasa Indonesia.
class PrediksiGagal extends RuntimeException
{
    public function __construct(string $pesan, public readonly int $kodeHttp = 422)
    {
        parent::__construct($pesan);
    }
}
