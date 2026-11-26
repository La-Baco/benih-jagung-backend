"""Validasi masukan: memastikan objek di foto adalah biji jagung, memakai Gemini API (Google).

Gemini tidak menilai kelayakan. Ia hanya menjawab apakah setiap objek yang ditemukan OpenCV
adalah satu butir biji jagung. Kelayakan tetap dinilai model Custom CNN penelitian.

Semua objek dikirim dalam SATU permintaan: setiap objek dipotong, diberi nomor, lalu disusun
menjadi satu gambar kisi. Dengan begitu satu foto hanya memakai satu kuota permintaan.

API key dibaca dari variabel lingkungan GEMINI_API_KEY (di VPS: deploy/.env.produksi) dan
tidak pernah ditulis ke log maupun dikirim ke aplikasi.
"""

import base64
import json
import urllib.error
import urllib.request

import cv2
import numpy as np

import config

UKURAN_UBIN = 320
TINGGI_LABEL = 44
KOLOM_MAKS = 4

PERINTAH = (
    "Gambar ini berisi {n} kotak bernomor. Setiap kotak adalah potongan foto yang memperlihatkan "
    "satu objek di atas alas. Untuk setiap nomor, tentukan apakah objek di tengah kotak itu adalah "
    "SATU BUTIR BIJI JAGUNG (kernel jagung, warna apa pun, utuh maupun rusak, berlubang, retak, "
    "atau berjamur). Jawab false untuk batu, kerikil, pasir, kacang, kedelai, beras, gabah, biji "
    "lain, potongan tongkol, jari, kertas, atau benda lain. Bila ragu, jawab false. "
    "Kembalikan satu entri untuk setiap nomor dari 1 sampai {n}."
)

SKEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {"nomor": {"type": "INTEGER"}, "biji_jagung": {"type": "BOOLEAN"}},
        "required": ["nomor", "biji_jagung"],
    },
}


class GeminiGagal(Exception):
    """Pemeriksaan tidak bisa dilakukan (kunci salah, kuota habis, jaringan, jawaban rusak)."""


def aktif():
    return bool(config.GEMINI_API_KEY)


def susun_kisi(citra_bgr, daftar_kotak):
    """Potong setiap objek menjadi ubin persegi bernomor, lalu susun dalam kisi."""
    tinggi, lebar = citra_bgr.shape[:2]
    ubin = []
    for i, (x, y, w, h) in enumerate(daftar_kotak, 1):
        sisi = int(max(w, h) * 1.4) + 20
        cx, cy = x + w // 2, y + h // 2
        x0, y0 = max(0, cx - sisi // 2), max(0, cy - sisi // 2)
        x1, y1 = min(lebar, cx + sisi // 2), min(tinggi, cy + sisi // 2)
        potongan = citra_bgr[y0:y1, x0:x1]
        skala = UKURAN_UBIN / max(potongan.shape[:2])
        potongan = cv2.resize(potongan, None, fx=skala, fy=skala, interpolation=cv2.INTER_AREA)
        kotak = np.full((UKURAN_UBIN + TINGGI_LABEL, UKURAN_UBIN, 3), 255, np.uint8)
        py = TINGGI_LABEL + (UKURAN_UBIN - potongan.shape[0]) // 2
        px = (UKURAN_UBIN - potongan.shape[1]) // 2
        kotak[py:py + potongan.shape[0], px:px + potongan.shape[1]] = potongan
        cv2.putText(kotak, f"Nomor {i}", (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
        ubin.append(cv2.copyMakeBorder(kotak, 6, 6, 6, 6, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
    kolom = min(KOLOM_MAKS, len(ubin))
    while len(ubin) % kolom:
        ubin.append(np.full_like(ubin[0], 255))
    return np.vstack([np.hstack(ubin[i:i + kolom]) for i in range(0, len(ubin), kolom)])


def periksa(citra_bgr, daftar_kotak):
    """Kembalikan daftar True/False (biji jagung atau bukan), urut sesuai daftar_kotak."""
    if not daftar_kotak:
        return []
    kisi = susun_kisi(citra_bgr, daftar_kotak)
    ok, jpeg = cv2.imencode(".jpg", kisi, [cv2.IMWRITE_JPEG_QUALITY, 90])
    badan = {
        "contents": [{"parts": [
            {"text": PERINTAH.format(n=len(daftar_kotak))},
            {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpeg.tobytes()).decode()}},
        ]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": SKEMA},
    }
    alamat = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent"
    permintaan = urllib.request.Request(alamat, json.dumps(badan).encode(), method="POST", headers={
        "Content-Type": "application/json", "x-goog-api-key": config.GEMINI_API_KEY})
    try:
        with urllib.request.urlopen(permintaan, timeout=config.GEMINI_BATAS_WAKTU) as respon:
            data = json.load(respon)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise GeminiGagal("kuota Gemini habis") from None
        if e.code in (400, 401, 403):
            raise GeminiGagal(f"permintaan ditolak Gemini (kode {e.code}); periksa API key dan nama model") from None
        raise GeminiGagal(f"Gemini mengembalikan kode {e.code}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise GeminiGagal(f"Gemini tidak dapat dihubungi ({type(e).__name__})") from None

    try:
        jawaban = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
        per_nomor = {int(j["nomor"]): bool(j["biji_jagung"]) for j in jawaban}
        return [per_nomor[i] for i in range(1, len(daftar_kotak) + 1)]
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        raise GeminiGagal("jawaban Gemini tidak dapat dibaca") from None
