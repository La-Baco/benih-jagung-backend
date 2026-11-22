// Unggahan model .keras dalam potongan 4 MB lewat 3 jalur paralel (halaman admin Model).
//
// - Tiga jalur dipakai karena satu koneksi ke VPS ini hanya sekitar 0,05 MB/detik, sedangkan
//   tiga koneksi sekitar 1 MB/detik (diukur saat mengunggah dataset).
// - Setiap potongan dicocokkan dengan SHA-256 di server dan dikirim ulang bila gagal.
// - Potongan yang sudah diterima disimpan server. Setelah halaman dimuat ulang atau koneksi
//   putus, memilih berkas yang sama melanjutkan dari potongan yang belum terkirim.
(function () {
    const form = document.getElementById('form-model');
    if (!form) return;

    const JALUR = 3;
    const BATAS_ULANG = 5;
    const token = document.querySelector('meta[name="csrf-token"]').content;
    const alamat = form.dataset.alamatUnggahan;

    const el = {
        berkas: document.getElementById('berkas'),
        id: document.getElementById('unggahan_id'),
        kotak: document.getElementById('kemajuan'),
        batang: document.getElementById('batang-unggah'),
        status: document.getElementById('status-unggah'),
        rincian: document.getElementById('rincian-unggah'),
        jeda: document.getElementById('tombol-jeda'),
        batal: document.getElementById('tombol-batal'),
        simpan: document.getElementById('tombol-simpan'),
        galat: document.getElementById('galat-unggah'),
    };

    let berkas = null;
    let sesi = null;
    let antrean = [];
    let berjalan = false;
    let dijeda = false;
    let jedaKarenaJaringan = false;
    const sedangDikirim = new Map(); // indeks -> {xhr, terkirim}
    let byteSelesai = 0;
    let riwayatKecepatan = [];

    const mb = (b) => (b / 1024 / 1024).toLocaleString('id-ID', {maximumFractionDigits: 1}) + ' MB';

    function tampilkanGalat(pesan) {
        el.galat.textContent = pesan;
        el.galat.hidden = !pesan;
    }

    function setStatus(teks) {
        el.status.textContent = teks;
    }

    function perbaruiKemajuan() {
        let byte = byteSelesai;
        sedangDikirim.forEach((s) => { byte += s.terkirim; });
        const persen = Math.min(100, Math.floor(byte / berkas.size * 100));
        el.batang.value = persen;
        el.batang.textContent = persen + '%';

        // Kecepatan dihitung dari 5 detik terakhir supaya angkanya tidak melompat-lompat.
        const sekarang = performance.now();
        riwayatKecepatan.push([sekarang, byte]);
        riwayatKecepatan = riwayatKecepatan.filter(([t]) => sekarang - t <= 5000);
        const [t0, b0] = riwayatKecepatan[0];
        const kecepatan = sekarang - t0 > 500 ? (byte - b0) / ((sekarang - t0) / 1000) : 0;
        let sisa = '';
        if (kecepatan > 0 && byte < berkas.size) {
            const detik = Math.ceil((berkas.size - byte) / kecepatan);
            sisa = detik < 60 ? `, sisa sekitar ${detik} detik` : `, sisa sekitar ${Math.ceil(detik / 60)} menit`;
        }
        el.rincian.textContent = `${persen}% (${mb(byte)} dari ${mb(berkas.size)})` +
            (kecepatan > 0 ? `, ${mb(kecepatan)}/detik${sisa}` : '');
    }

    async function hitungSidik(file) {
        // Sidik dari 1 MB pertama, ukuran, dan nama: cukup untuk mengenali berkas yang sama tanpa membaca seluruh model.
        const awal = await file.slice(0, 1024 * 1024).arrayBuffer();
        const teks = new TextEncoder().encode(`${file.name}|${file.size}|${file.lastModified}|`);
        const gabung = new Uint8Array(teks.length + awal.byteLength);
        gabung.set(teks);
        gabung.set(new Uint8Array(awal), teks.length);
        return hex(await crypto.subtle.digest('SHA-256', gabung));
    }

    function hex(buffer) {
        return [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, '0')).join('');
    }

    async function minta(metode, url, data) {
        const respon = await fetch(url, {
            method: metode,
            headers: {'Content-Type': 'application/json', Accept: 'application/json', 'X-CSRF-TOKEN': token},
            body: data ? JSON.stringify(data) : undefined,
        });
        const isi = await respon.json().catch(() => ({}));
        if (!respon.ok) {
            const pesan = isi.errors ? Object.values(isi.errors)[0][0] : isi.message;
            throw new Error(pesan || `Server menjawab ${respon.status}.`);
        }
        return isi;
    }

    function kirimPotongan(indeks) {
        return new Promise(async (selesai, gagal) => {
            const mulai = indeks * sesi.ukuran_potongan;
            const isi = await berkas.slice(mulai, Math.min(mulai + sesi.ukuran_potongan, berkas.size)).arrayBuffer();
            const sha = hex(await crypto.subtle.digest('SHA-256', isi));
            // Jeda bisa ditekan selama potongan dibaca dan dihitung SHA-256-nya; jangan kirim lagi.
            if (dijeda) {
                gagal(new Error('dijeda'));
                return;
            }

            const xhr = new XMLHttpRequest();
            sedangDikirim.set(indeks, {xhr, terkirim: 0});
            xhr.open('POST', `${alamat}/${sesi.id}/${indeks}`);
            xhr.setRequestHeader('Content-Type', 'application/octet-stream');
            xhr.setRequestHeader('Accept', 'application/json');
            xhr.setRequestHeader('X-CSRF-TOKEN', token);
            xhr.setRequestHeader('X-Sha256', sha);
            xhr.upload.onprogress = (e) => {
                sedangDikirim.get(indeks).terkirim = e.loaded;
                perbaruiKemajuan();
            };
            xhr.onload = () => {
                sedangDikirim.delete(indeks);
                if (xhr.status === 200) {
                    byteSelesai += isi.byteLength;
                    perbaruiKemajuan();
                    selesai();
                } else {
                    let pesan = `Server menjawab ${xhr.status}.`;
                    try { pesan = JSON.parse(xhr.responseText).message || pesan; } catch (e) { /* bukan JSON */ }
                    gagal(new Error(pesan));
                }
            };
            xhr.onerror = () => { sedangDikirim.delete(indeks); gagal(new Error('jaringan')); };
            xhr.onabort = () => { sedangDikirim.delete(indeks); gagal(new Error('dijeda')); };
            xhr.send(isi);
        });
    }

    async function pekerja() {
        while (!dijeda && antrean.length > 0) {
            const indeks = antrean.shift();
            for (let ulang = 0; ; ulang++) {
                try {
                    await kirimPotongan(indeks);
                    break;
                } catch (e) {
                    if (dijeda) {
                        antrean.unshift(indeks);
                        return;
                    }
                    if (!navigator.onLine) {
                        antrean.unshift(indeks);
                        jedaOtomatis();
                        return;
                    }
                    if (ulang >= BATAS_ULANG) {
                        antrean.unshift(indeks);
                        jeda();
                        tampilkanGalat(`Potongan ${indeks + 1} gagal dikirim ${BATAS_ULANG + 1} kali (${e.message}). Tekan Lanjutkan untuk mencoba lagi.`);
                        return;
                    }
                    // Tunggu sebentar sebelum mencoba lagi: 1, 2, 4, 8 detik.
                    await new Promise((r) => setTimeout(r, 1000 * 2 ** Math.min(ulang, 3)));
                }
            }
        }
    }

    async function jalankan() {
        berjalan = true;
        dijeda = false;
        jedaKarenaJaringan = false;
        tampilkanGalat('');
        el.jeda.textContent = 'Jeda';
        el.jeda.disabled = false;
        el.batal.disabled = false;
        const tersimpan = Math.floor(byteSelesai / berkas.size * 100);
        setStatus(tersimpan > 0 ? `Mengunggah, melanjutkan dari ${tersimpan}% yang sudah tersimpan...` : 'Mengunggah...');
        riwayatKecepatan = [];

        await Promise.all(Array.from({length: JALUR}, pekerja));
        if (dijeda) return;

        berjalan = false;
        el.jeda.disabled = true;
        setStatus('Mengecek kelengkapan di server...');
        const info = await minta('GET', `${alamat}/${sesi.id}`).catch((e) => { tampilkanGalat(e.message); return null; });
        if (!info) return;
        if (info.diterima.length !== info.jumlah_potongan) {
            // Ada potongan yang belum tercatat; kirim ulang hanya yang kurang.
            antrean = sisaPotongan(info);
            return jalankan();
        }
        el.id.value = sesi.id;
        el.batang.value = 100;
        setStatus('Unggahan selesai. Model sedang diperiksa server, mohon tunggu.');
        el.simpan.disabled = true;
        form.submit();
    }

    function sisaPotongan(info) {
        const diterima = new Set(info.diterima);
        return Array.from({length: info.jumlah_potongan}, (_, i) => i).filter((i) => !diterima.has(i));
    }

    function jeda() {
        dijeda = true;
        berjalan = false;
        // Potongan yang belum selesai dibuang, jadi batang turun ke jumlah yang benar-benar tersimpan di server.
        sedangDikirim.forEach((s) => s.xhr.abort());
        sedangDikirim.clear();
        riwayatKecepatan = [];
        perbaruiKemajuan();
        el.jeda.textContent = 'Lanjutkan';
        const tersimpan = Math.floor(byteSelesai / berkas.size * 100);
        setStatus(`Unggahan dijeda. ${tersimpan}% sudah tersimpan di server dan tidak perlu dikirim ulang.`);
    }

    function jedaOtomatis() {
        if (dijeda) return;
        jeda();
        jedaKarenaJaringan = true;
        setStatus('Koneksi terputus. Unggahan dijeda dan akan dilanjutkan otomatis saat koneksi kembali.');
    }

    el.jeda.addEventListener('click', () => {
        if (berjalan) {
            jeda();
        } else {
            jalankan();
        }
    });

    el.batal.addEventListener('click', async () => {
        if (!sesi || !confirm('Batalkan unggahan ini? Potongan yang sudah terkirim akan dihapus.')) return;
        jeda();
        await minta('DELETE', `${alamat}/${sesi.id}`).catch(() => {});
        location.reload();
    });

    window.addEventListener('offline', () => { if (berjalan) jedaOtomatis(); });
    window.addEventListener('online', () => {
        if (jedaKarenaJaringan) {
            setStatus('Koneksi kembali. Melanjutkan unggahan...');
            jalankan();
        }
    });
    window.addEventListener('beforeunload', (e) => {
        if (berjalan) e.preventDefault();
    });

    form.addEventListener('submit', (e) => {
        if (!el.id.value) {
            e.preventDefault();
            tampilkanGalat('Pilih berkas model dulu dan tunggu sampai unggahan selesai.');
        }
    });

    el.simpan.addEventListener('click', async (e) => {
        e.preventDefault();
        if (!form.reportValidity()) return;
        berkas = el.berkas.files[0];
        if (!berkas) {
            tampilkanGalat('Pilih berkas model (.keras) dulu.');
            el.berkas.focus();
            return;
        }
        if (!berkas.name.toLowerCase().endsWith('.keras')) {
            tampilkanGalat('Berkas harus berformat .keras.');
            return;
        }
        tampilkanGalat('');
        el.simpan.disabled = true;
        el.berkas.disabled = true;
        el.kotak.hidden = false;
        setStatus('Menyiapkan unggahan...');
        try {
            const sidik = await hitungSidik(berkas);
            sesi = await minta('POST', alamat, {nama: berkas.name, ukuran: berkas.size, sidik});
        } catch (err) {
            tampilkanGalat(err.message);
            el.simpan.disabled = false;
            el.berkas.disabled = false;
            return;
        }
        antrean = sisaPotongan(sesi);
        // Potongan terakhir bisa lebih kecil, jadi byte yang sudah diterima dihitung per potongan.
        byteSelesai = sesi.diterima.reduce((jumlah, i) => jumlah + Math.min(sesi.ukuran_potongan, berkas.size - i * sesi.ukuran_potongan), 0);
        perbaruiKemajuan();
        jalankan();
    });
})();
