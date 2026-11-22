"""Alat bantu black box aplikasi Android lewat ADB (HP asli tersambung kabel USB).

Contoh:
  python 13_hp.py layar                 -> daftar teks/tombol yang tampil
  python 13_hp.py ketuk "Masuk"         -> ketuk elemen yang teks/deskripsinya persis "Masuk"
  python 13_hp.py ketuk-mirip "Lupa"    -> ketuk elemen yang teksnya memuat "Lupa"
  python 13_hp.py isi 0 "petani@benih.test" -> isi kolom isian ke-0 (urutan dari atas)
  python 13_hp.py foto 03_login_petani  -> simpan screenshot ke bukti/10_black_box/android/
  python 13_hp.py kembali | tunggu "Teks" [detik]
Aplikasi terhubung ke Laravel di laptop melalui "adb reverse tcp:8000 tcp:8000".
"""

import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import config

ADB = r"C:\Android\sdk\platform-tools\adb.exe"
FOLDER = config.FOLDER_BUKTI / "10_black_box" / "android"


def adb(*arg, biner=False):
    hasil = subprocess.run([ADB, *arg], capture_output=True, check=True)
    return hasil.stdout if biner else hasil.stdout.decode("utf-8", "replace")


def simpul():
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    akar = ET.fromstring(adb("shell", "cat", "/sdcard/ui.xml"))
    daftar = []
    for n in akar.iter("node"):
        x1, y1, x2, y2 = map(int, re.findall(r"\d+", n.get("bounds")))
        daftar.append({"teks": (n.get("text") or n.get("content-desc") or "").strip(), "kelas": n.get("class"),
                       "tengah": ((x1 + x2) // 2, (y1 + y2) // 2), "bisa_diketuk": n.get("clickable") == "true",
                       "isian": n.get("class") == "android.widget.EditText", "kotak": (x1, y1, x2, y2)})
    return daftar


def ketuk_titik(x, y):
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(1.0)


def cari(label, mirip=False):
    for n in simpul():
        if (label in n["teks"]) if mirip else (n["teks"] == label or n["teks"].split("\n")[0] == label):
            return n
    return None


def main():
    perintah, arg = sys.argv[1], sys.argv[2:]
    if perintah == "layar":
        for n in simpul():
            if n["teks"] or n["isian"]:
                print(f"{'[isian] ' if n['isian'] else ''}{n['teks']!r} {n['kelas'].split('.')[-1]} {n['kotak']}")
    elif perintah in ("ketuk", "ketuk-mirip"):
        n = cari(arg[0], mirip=perintah == "ketuk-mirip")
        if not n:
            sys.exit(f"tidak ditemukan: {arg[0]}")
        ketuk_titik(*n["tengah"])
        print("diketuk:", n["teks"])
    elif perintah == "titik":
        ketuk_titik(int(arg[0]), int(arg[1]))
    elif perintah == "isi":
        isian = [n for n in simpul() if n["isian"]]
        ketuk_titik(*isian[int(arg[0])]["tengah"])
        adb("shell", "input", "keyevent", "KEYCODE_MOVE_END")
        for _ in range(60):
            adb("shell", "input", "keyevent", "KEYCODE_DEL")
        adb("shell", "input", "text", arg[1].replace(" ", "%s"))
        print("diisi kolom", arg[0])
    elif perintah == "tutup-keyboard":
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
    elif perintah == "kembali":
        adb("shell", "input", "keyevent", "KEYCODE_BACK")
        time.sleep(1.0)
    elif perintah == "geser":
        adb("shell", "input", "swipe", "540", arg[0], "540", arg[1], "400")
        time.sleep(0.8)
    elif perintah == "tunggu":
        batas = time.time() + float(arg[1] if len(arg) > 1 else 30)
        while time.time() < batas:
            if cari(arg[0], mirip=True):
                print("muncul:", arg[0])
                return
            time.sleep(1.0)
        sys.exit(f"tidak muncul: {arg[0]}")
    elif perintah == "foto":
        FOLDER.mkdir(parents=True, exist_ok=True)
        (FOLDER / f"{arg[0]}.png").write_bytes(adb("exec-out", "screencap", "-p", biner=True))
        print("disimpan:", FOLDER / f"{arg[0]}.png")


if __name__ == "__main__":
    main()
