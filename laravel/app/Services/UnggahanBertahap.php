<?php

namespace App\Services;

use Illuminate\Support\Facades\File;
use Illuminate\Support\Str;

// Unggahan berkas besar (model .keras) dalam potongan 4 MB. Setiap potongan ditulis langsung ke
// posisinya di berkas tujuan, jadi potongan boleh datang tidak berurutan dari beberapa jalur
// sekaligus, dan unggahan yang terputus bisa dilanjutkan dari potongan yang belum diterima.
class UnggahanBertahap
{
    public const UKURAN_POTONGAN = 4 * 1024 * 1024;

    public const UKURAN_MAKS = 400 * 1024 * 1024;

    // Unggahan yang tidak disentuh lebih dari sehari dianggap ditinggalkan.
    private const BATAS_UMUR_DETIK = 24 * 3600;

    private function folder(string $id): string
    {
        return storage_path("app/unggahan/{$id}");
    }

    public function pathBerkas(string $id): string
    {
        return $this->folder($id) . '/berkas.part';
    }

    public function mulai(int $penggunaId, string $nama, int $ukuran, string $sidik): array
    {
        $this->bersihkanYangLama();

        // Berkas yang sama (nama, ukuran, dan sidik isi sama) melanjutkan unggahan sebelumnya.
        foreach ($this->milik($penggunaId) as $info) {
            if ($info['sidik'] === $sidik && $info['ukuran'] === $ukuran) {
                return $info;
            }
        }

        $id = (string) Str::uuid();
        File::ensureDirectoryExists($this->folder($id));
        touch($this->pathBerkas($id));
        $info = [
            'id' => $id,
            'pengguna_id' => $penggunaId,
            'nama' => $nama,
            'ukuran' => $ukuran,
            'sidik' => $sidik,
            'ukuran_potongan' => self::UKURAN_POTONGAN,
            'jumlah_potongan' => (int) ceil($ukuran / self::UKURAN_POTONGAN),
            'diterima' => [],
            'dibuat' => now()->toDateTimeString(),
        ];
        file_put_contents($this->folder($id) . '/info.json', json_encode($info));

        return $info;
    }

    public function info(string $id, int $penggunaId): ?array
    {
        if (! Str::isUuid($id) || ! is_file($this->folder($id) . '/info.json')) {
            return null;
        }
        $info = json_decode(file_get_contents($this->folder($id) . '/info.json'), true);

        return $info['pengguna_id'] === $penggunaId ? $info : null;
    }

    public function ukuranPotongan(array $info, int $indeks): int
    {
        $sisa = $info['ukuran'] - $indeks * $info['ukuran_potongan'];

        return min($info['ukuran_potongan'], $sisa);
    }

    public function simpanPotongan(array $info, int $indeks, string $isi): array
    {
        $berkas = fopen($this->pathBerkas($info['id']), 'c');
        fseek($berkas, $indeks * $info['ukuran_potongan']);
        fwrite($berkas, $isi);
        fclose($berkas);

        // Beberapa potongan bisa selesai bersamaan, jadi daftar potongan diperbarui di bawah kunci berkas.
        $kunci = fopen($this->folder($info['id']) . '/info.json', 'c+');
        flock($kunci, LOCK_EX);
        $terbaru = json_decode(stream_get_contents($kunci), true);
        $terbaru['diterima'] = array_values(array_unique([...$terbaru['diterima'], $indeks]));
        ftruncate($kunci, 0);
        rewind($kunci);
        fwrite($kunci, json_encode($terbaru));
        flock($kunci, LOCK_UN);
        fclose($kunci);

        return $terbaru;
    }

    public function lengkap(array $info): bool
    {
        return count($info['diterima']) === $info['jumlah_potongan']
            && filesize($this->pathBerkas($info['id'])) === $info['ukuran'];
    }

    public function hapus(string $id): void
    {
        File::deleteDirectory($this->folder($id));
    }

    public function milik(int $penggunaId): array
    {
        $hasil = [];
        foreach (glob(storage_path('app/unggahan/*/info.json')) ?: [] as $path) {
            $info = json_decode(file_get_contents($path), true);
            if ($info['pengguna_id'] === $penggunaId) {
                $hasil[] = $info;
            }
        }

        return $hasil;
    }

    private function bersihkanYangLama(): void
    {
        foreach (glob(storage_path('app/unggahan/*'), GLOB_ONLYDIR) ?: [] as $folder) {
            if (time() - filemtime($folder) > self::BATAS_UMUR_DETIK && time() - @filemtime("{$folder}/berkas.part") > self::BATAS_UMUR_DETIK) {
                File::deleteDirectory($folder);
            }
        }
    }
}
