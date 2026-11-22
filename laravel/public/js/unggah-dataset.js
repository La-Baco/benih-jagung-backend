// Unggahan foto dataset dengan progress bar. Foto paling besar 20 x 10 MB, jadi cukup satu
// permintaan; yang dibutuhkan admin adalah melihat kemajuannya, bukan melanjutkan setelah putus.
(function () {
    const form = document.getElementById('form-dataset');
    if (!form) return;

    const tombol = document.getElementById('tombol-unggah');
    const kotak = document.getElementById('kemajuan-dataset');
    const batang = document.getElementById('batang-dataset');
    const status = document.getElementById('status-dataset');
    const galat = document.getElementById('galat-dataset');

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        const xhr = new XMLHttpRequest();
        xhr.open('POST', form.action);
        xhr.setRequestHeader('Accept', 'application/json');

        xhr.upload.onprogress = function (ev) {
            if (!ev.lengthComputable) return;
            const persen = Math.floor(ev.loaded / ev.total * 100);
            const mb = (b) => (b / 1048576).toLocaleString('id-ID', {maximumFractionDigits: 1});
            batang.value = persen;
            batang.textContent = persen + '%';
            status.textContent = persen < 100
                ? `Mengunggah ${persen}% (${mb(ev.loaded)} dari ${mb(ev.total)} MB)`
                : 'Unggahan selesai. Server sedang memeriksa setiap foto...';
        };
        xhr.onload = function () {
            let isi = {};
            try { isi = JSON.parse(xhr.responseText); } catch (er) { /* bukan JSON */ }
            if (xhr.status === 200 && isi.alamat) {
                location.href = isi.alamat;
                return;
            }
            const pesan = isi.errors ? Object.values(isi.errors)[0][0] : isi.message;
            gagal(pesan || `Unggahan gagal (kode ${xhr.status}).`);
        };
        xhr.onerror = function () {
            gagal('Koneksi terputus saat mengunggah. Periksa jaringan lalu kirim lagi.');
        };

        galat.hidden = true;
        kotak.hidden = false;
        tombol.disabled = true;
        tombol.textContent = 'Mengunggah...';
        xhr.send(new FormData(form));
    });

    function gagal(pesan) {
        galat.textContent = pesan;
        galat.hidden = false;
        kotak.hidden = true;
        tombol.disabled = false;
        tombol.textContent = tombol.dataset.label;
    }
})();
