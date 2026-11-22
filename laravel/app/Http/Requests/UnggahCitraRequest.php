<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

// Aturan unggah yang sama untuk halaman web dan aplikasi Flutter (Tabel 3.12 no. 3-5).
class UnggahCitraRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'gambar' => ['required', 'file', 'mimes:jpg,jpeg,png', 'max:10240'],
        ];
    }

    public function messages(): array
    {
        return [
            'gambar.required' => 'Berkas citra wajib diisi.',
            'gambar.uploaded' => 'Berkas gagal diunggah. Periksa ukuran berkas (maksimal 10 MB).',
            'gambar.file' => 'Berkas tidak valid. Unggah citra berformat JPEG atau PNG.',
            'gambar.mimes' => 'Berkas tidak valid. Unggah citra berformat JPEG atau PNG.',
            'gambar.max' => 'Ukuran berkas maksimal 10 MB.',
        ];
    }
}
