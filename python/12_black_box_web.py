"""Black box testing website, skenario 12-21 Tabel Rancangan Skenario Black Box Testing (BAB III).

Dijalankan di Microsoft Edge (Selenium) terhadap Laravel http://127.0.0.1:8000 dan Flask
http://127.0.0.1:5000 yang benar-benar berjalan. Email lupa kata sandi dikirim dengan mailer
"log" Laravel (storage/logs/laravel.log); tautannya dibaca dari berkas itu lalu dibuka di browser.
Kedaluwarsa tautan (60 menit) disimulasikan dengan memundurkan kolom created_at token 61 menit.

Hasil: bukti/10_black_box/web/ (screenshot per skenario dan hasil_black_box_web.json).
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By

import config

ALAMAT = "http://127.0.0.1:8000"
FOLDER = config.FOLDER_BUKTI / "10_black_box" / "web"
LOG_LARAVEL = config.FOLDER_PYTHON.parent / "laravel" / "storage" / "logs" / "laravel.log"
MYSQL = r"C:\laragon\bin\mysql\mysql-8.0.30-winx64\bin\mysql.exe"
ADMIN, PETANI, SANDI = "admin@benih.test", "petani@benih.test", "12345678"

hasil = []


def sql(perintah):
    return subprocess.run([MYSQL, "-uroot", "-N", "klasifikasi_benih", "-e", perintah],
                          capture_output=True, text=True, check=True).stdout.strip()


def catat(no, fungsi, skenario, harapan, teramati, sesuai, nama_gambar):
    driver.save_screenshot(str(FOLDER / nama_gambar))
    hasil.append({"no": no, "fungsi": fungsi, "skenario": skenario, "harapan": harapan,
                  "teramati": teramati, "hasil": "Sesuai" if sesuai else "Tidak sesuai", "screenshot": nama_gambar})
    print(f"{no:>2}. {'SESUAI' if sesuai else 'TIDAK SESUAI':<12} {fungsi}: {teramati}")


def pesan():
    for kelas in ("pesan-error", "pesan-sukses"):
        el = driver.find_elements(By.CLASS_NAME, kelas)
        if el:
            return el[0].text.strip()
    return ""


def tombol_utama():
    # Tombol kirim formulir utama; tombol Logout di menu admin juga bertipe submit, jadi tidak dipakai.
    driver.find_element(By.XPATH, "//form[not(contains(@action,'/logout'))]//button[@type='submit']").click()


def login(email, sandi):
    driver.get(ALAMAT + "/login")
    driver.find_element(By.ID, "email").clear()
    driver.find_element(By.ID, "email").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(sandi)
    tombol_utama()
    time.sleep(0.8)


def logout():
    tombol = driver.find_elements(By.XPATH, "//form[contains(@action,'/logout')]//button")
    if tombol:
        tombol[0].click()
        time.sleep(0.6)


def tautan_reset_terakhir(email):
    # Hanya pemenggalan baris quoted-printable yang dibuang; dekode penuh merusak "?email=admin%40...".
    isi = LOG_LARAVEL.read_text(encoding="utf-8", errors="replace")
    isi = re.sub(r"=\r?\n", "", isi).replace("=3D", "=")
    tautan = re.findall(r"http://127\.0\.0\.1:8000/reset-sandi/[0-9a-f]+\?email=[^\s\"<>\]\)]+", isi)
    tautan = [t.replace("&amp;", "&") for t in tautan if email.replace("@", "%40") in t or email in t]
    return tautan[-1] if tautan else None


def isi_reset(sandi_baru):
    driver.find_element(By.ID, "password").send_keys(sandi_baru)
    driver.find_element(By.ID, "password_confirmation").send_keys(sandi_baru)
    tombol_utama()
    time.sleep(0.8)


def main():
    global driver
    FOLDER.mkdir(parents=True, exist_ok=True)
    opsi = webdriver.EdgeOptions()
    opsi.add_argument("--window-size=1366,900")
    driver = webdriver.Edge(options=opsi)
    try:
        # 12. Login admin benar
        login(ADMIN, SANDI)
        ok = driver.current_url.endswith("/admin/dashboard")
        catat(12, "Login", "Email dan kata sandi admin benar", "Masuk ke dashboard admin",
              f"URL {driver.current_url}", ok, "12_login_admin.png")
        logout()

        # 13. Login salah
        login(ADMIN, "salah123")
        p = pesan()
        catat(13, "Login", "Email atau kata sandi salah", "Muncul pesan login gagal",
              f"pesan: {p}", p == "Login gagal. Email atau kata sandi salah.", "13_login_salah.png")

        # 14. Ikon mata
        driver.get(ALAMAT + "/login")
        kolom = driver.find_element(By.ID, "password")
        kolom.send_keys("rahasia123")
        mata = driver.find_element(By.CSS_SELECTOR, "[data-mata=password]")
        # Selain tipe kolom, dihitung ikon mata yang benar-benar tampil: harus tepat satu di setiap langkah.
        ikon_tampil = ("return [...document.querySelectorAll('[data-mata=password] svg')]"
                       ".filter(s => getComputedStyle(s).display !== 'none').length")
        jenis = [kolom.get_attribute("type")]
        ikon = [driver.execute_script(ikon_tampil)]
        mata.click()
        jenis.append(kolom.get_attribute("type"))
        ikon.append(driver.execute_script(ikon_tampil))
        driver.save_screenshot(str(FOLDER / "14a_mata_terbuka.png"))
        mata.click()
        jenis.append(kolom.get_attribute("type"))
        ikon.append(driver.execute_script(ikon_tampil))
        catat(14, "Login", "Menekan ikon mata pada kolom kata sandi", "Kata sandi tampil dan tersembunyi bergantian",
              "tipe kolom " + " -> ".join(jenis) + "; ikon tampil " + " -> ".join(map(str, ikon)),
              jenis == ["password", "text", "password"] and ikon == [1, 1, 1], "14b_mata_tertutup.png")

        # 15. Hak akses: akun petani di website
        login(PETANI, SANDI)
        p = pesan()
        di_login = driver.current_url.rstrip("/").endswith("/login")
        driver.save_screenshot(str(FOLDER / "15a_petani_login_ditolak.png"))
        driver.get(ALAMAT + "/admin/pengguna")
        time.sleep(0.5)
        dialihkan = driver.current_url.rstrip("/").endswith("/login")
        catat(15, "Hak akses", "Akun petani masuk ke website lalu membuka halaman admin",
              "Akses ditolak", f"pesan: {p}; /admin/pengguna dialihkan ke {driver.current_url}",
              di_login and dialihkan and p == "Akun petani dipakai di aplikasi Android, bukan di website.",
              "15b_admin_dialihkan.png")

        # 16. Atur ulang kata sandi (admin) lalu tautan kedaluwarsa (petani)
        driver.get(ALAMAT + "/login")
        driver.find_element(By.LINK_TEXT, "Lupa kata sandi?").click()
        driver.find_element(By.ID, "email").send_keys(ADMIN)
        tombol_utama()
        time.sleep(1.0)
        terkirim = pesan()
        driver.save_screenshot(str(FOLDER / "16a_tautan_terkirim.png"))
        tautan = tautan_reset_terakhir(ADMIN)
        driver.get(tautan)
        driver.save_screenshot(str(FOLDER / "16b_halaman_atur_ulang.png"))
        isi_reset("adminbaru123")
        tersimpan = driver.current_url.endswith("/reset-sandi-selesai")
        driver.save_screenshot(str(FOLDER / "16c_kata_sandi_tersimpan.png"))
        login(ADMIN, "adminbaru123")
        bisa_masuk = driver.current_url.endswith("/admin/dashboard")
        logout()

        driver.get(ALAMAT + "/lupa-sandi")
        driver.find_element(By.ID, "email").send_keys(PETANI)
        tombol_utama()
        time.sleep(1.0)
        tautan_petani = tautan_reset_terakhir(PETANI)
        sql(f"UPDATE password_reset_tokens SET created_at = created_at - INTERVAL 61 MINUTE WHERE email='{PETANI}'")
        driver.get(tautan_petani)
        isi_reset("petanibaru123")
        kedaluwarsa = pesan()
        catat(16, "Atur ulang kata sandi",
              "Membuka tautan dari email lalu mengisi kata sandi baru; tautan berumur 61 menit",
              "Kata sandi baru tersimpan; tautan kedaluwarsa ditolak",
              f"{terkirim}; tersimpan: {'ya' if tersimpan else 'tidak'}; login dengan sandi baru: "
              f"{'berhasil' if bisa_masuk else 'gagal'}; tautan kedaluwarsa: {kedaluwarsa}",
              bool(tautan) and tersimpan and bisa_masuk
              and kedaluwarsa == "Tautan tidak berlaku atau sudah kedaluwarsa. Minta tautan baru.",
              "16d_tautan_kedaluwarsa.png")

        # 17. Tambah pengguna
        login(ADMIN, "adminbaru123")
        driver.get(ALAMAT + "/admin/pengguna/create")
        driver.find_element(By.ID, "nama").send_keys("Petani Uji Website")
        driver.find_element(By.ID, "email").send_keys("ujiweb@benih.test")
        driver.find_element(By.ID, "password").send_keys("ujiweb123")
        tombol_utama()
        time.sleep(0.8)
        p = pesan()
        ada = "ujiweb@benih.test" in driver.find_element(By.TAG_NAME, "table").text
        catat(17, "Kelola pengguna", "Menambah pengguna dengan data lengkap",
              "Pengguna baru tersimpan dan tampil pada daftar", f"pesan: {p}; tampil di tabel: {'ya' if ada else 'tidak'}",
              ada and p == "Pengguna berhasil ditambahkan.", "17_tambah_pengguna.png")

        # 18. Email sudah terdaftar
        driver.get(ALAMAT + "/admin/pengguna/create")
        driver.find_element(By.ID, "nama").send_keys("Duplikat")
        driver.find_element(By.ID, "email").send_keys(PETANI)
        driver.find_element(By.ID, "password").send_keys("duplikat123")
        tombol_utama()
        time.sleep(0.8)
        p = pesan()
        catat(18, "Kelola pengguna", "Menambah pengguna dengan email yang sudah terdaftar",
              "Muncul pesan email sudah digunakan", f"pesan: {p}", "Email sudah digunakan." in p,
              "18_email_terdaftar.png")

        # 19. Hapus akun petani dan akun sendiri
        driver.get(ALAMAT + "/admin/pengguna")
        baris = driver.find_element(By.XPATH, "//tr[td[contains(.,'ujiweb@benih.test')]]")
        baris.find_element(By.XPATH, ".//button[contains(.,'Hapus')]").click()
        driver.switch_to.alert.accept()
        time.sleep(0.8)
        p_hapus = pesan()
        hilang = "ujiweb@benih.test" not in driver.find_element(By.TAG_NAME, "table").text
        baris_admin = driver.find_element(By.XPATH, f"//tr[td[contains(.,'{ADMIN}')]]")
        tanpa_tombol = not baris_admin.find_elements(By.XPATH, ".//button[contains(.,'Hapus')]")
        # Permintaan hapus akun sendiri dikirim paksa lewat formulir buatan, seperti pengguna yang mengakali tampilan.
        id_admin = sql(f"SELECT id FROM users WHERE email='{ADMIN}'")
        driver.execute_script("""
            const f = document.createElement('form'); f.method = 'POST'; f.action = arguments[0];
            for (const [k, v] of [['_token', document.querySelector('input[name=_token]').value], ['_method', 'DELETE']]) {
                const i = document.createElement('input'); i.type = 'hidden'; i.name = k; i.value = v; f.appendChild(i);
            }
            document.body.appendChild(f); f.submit();""", f"{ALAMAT}/admin/pengguna/{id_admin}")
        time.sleep(0.8)
        p_sendiri = pesan()
        masih_ada = sql(f"SELECT COUNT(*) FROM users WHERE email='{ADMIN}'") == "1"
        catat(19, "Kelola pengguna", "Menghapus akun petani dan akun sendiri",
              "Akun petani terhapus; penghapusan akun sendiri ditolak",
              f"{p_hapus}; tombol hapus akun sendiri tidak ditampilkan: {'ya' if tanpa_tombol else 'tidak'}; "
              f"permintaan paksa: {p_sendiri}",
              hilang and tanpa_tombol and masih_ada and p_sendiri == "Akun yang sedang dipakai tidak dapat dihapus.",
              "19_hapus_pengguna.png")

        # 20. Riwayat seluruh pengguna
        driver.get(ALAMAT + "/riwayat")
        time.sleep(0.5)
        teks = driver.find_element(By.TAG_NAME, "table").text
        jumlah_db = int(sql("SELECT COUNT(*) FROM riwayat_klasifikasi"))
        ada_nama = "Nama pengguna" in teks
        nama_db = sql("SELECT DISTINCT u.nama FROM riwayat_klasifikasi r JOIN users u ON u.id=r.user_id").splitlines()
        semua_nama = all(n in teks for n in nama_db)
        catat(20, "Riwayat", "Membuka menu riwayat", "Tampil riwayat seluruh pengguna beserta nama pengguna",
              f"kolom nama pengguna: {'ada' if ada_nama else 'tidak'}; {jumlah_db} riwayat di basis data dari "
              f"{len(nama_db)} pengguna ({', '.join(nama_db)}), semua nama tampil: {'ya' if semua_nama else 'tidak'}",
              ada_nama and jumlah_db > 0 and semua_nama, "20_riwayat_admin.png")

        # 21. Logout
        logout()
        catat(21, "Logout", "Menekan tombol logout", "Kembali ke halaman login",
              f"URL {driver.current_url}", driver.current_url.rstrip("/").endswith("/login"), "21_logout.png")
    finally:
        driver.quit()
        (FOLDER / "hasil_black_box_web.json").write_text(json.dumps(hasil, ensure_ascii=False, indent=2),
                                                        encoding="utf-8")
    sesuai = sum(h["hasil"] == "Sesuai" for h in hasil)
    print(f"\n{sesuai} dari {len(hasil)} skenario sesuai")
    return 0 if sesuai == len(hasil) else 1


if __name__ == "__main__":
    sys.exit(main())
