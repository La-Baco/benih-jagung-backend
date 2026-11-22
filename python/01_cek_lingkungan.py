"""Mencatat versi perangkat lunak, GPU, dan isi dataset sebagai bukti Tabel 3.11."""

import platform
import sys
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version

import cv2
import keras
import matplotlib
import numpy as np
import tensorflow as tf

import config


def versi_paket(nama):
    try:
        return version(nama)
    except PackageNotFoundError:
        return "tidak terpasang"


def nama_sistem_operasi():
    if platform.system() == "Windows":
        # Python 3.10 melaporkan Windows 11 sebagai "10"; Windows 11 dimulai dari build 22000.
        build = int(platform.version().split(".")[-1])
        return f"Windows {'11' if build >= 22000 else '10'} {platform.architecture()[0]} (build {build})"
    try:
        distro = platform.freedesktop_os_release()["PRETTY_NAME"]
    except OSError:
        distro = platform.system()
    return f"{distro}, kernel {platform.release()}"


def nama_prosesor():
    if platform.system() == "Windows":
        import winreg
        kunci = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        return winreg.QueryValueEx(kunci, "ProcessorNameString")[0].strip()
    with open("/proc/cpuinfo", encoding="utf-8") as f:
        for baris in f:
            if baris.startswith("model name"):
                return baris.split(":", 1)[1].strip()
    return platform.processor()


def total_ram_gb():
    if platform.system() == "Windows":
        import ctypes

        class StatusMemori(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        status = StatusMemori()
        status.dwLength = ctypes.sizeof(StatusMemori)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        return status.ullTotalPhys / 1024 ** 3
    import os
    return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024 ** 3


def info_gpu():
    daftar_gpu = tf.config.list_physical_devices("GPU")
    if not daftar_gpu:
        return ["GPU            : tidak terdeteksi, pelatihan berjalan di CPU"]

    info_build = tf.sysconfig.get_build_info()
    baris = [
        f"CUDA (build TF): {info_build.get('cuda_version', '-')}",
        f"cuDNN (build TF): {info_build.get('cudnn_version', '-')}",
    ]
    for gpu in daftar_gpu:
        detail = tf.config.experimental.get_device_details(gpu)
        kapabilitas = detail.get("compute_capability")
        kapabilitas = ".".join(map(str, kapabilitas)) if kapabilitas else "-"
        baris.append(f"GPU            : {detail.get('device_name', gpu.name)} (compute capability {kapabilitas})")
    return baris


def main():
    baris = [
        f"Waktu cek      : {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"Sistem operasi : {nama_sistem_operasi()}",
        f"Prosesor       : {nama_prosesor()}",
        f"RAM            : {total_ram_gb():.1f} GB",
        f"Python         : {sys.version.split()[0]}",
        f"TensorFlow     : {tf.__version__}",
        f"Keras          : {keras.__version__}",
        f"OpenCV         : {cv2.__version__}",
        f"Flask          : {versi_paket('flask')}",
        f"NumPy          : {np.__version__}",
        f"Matplotlib     : {matplotlib.__version__}",
        *info_gpu(),
        "",
        "Isi dataset asli:",
    ]

    total = 0
    for folder in config.KELAS_ASLI:
        jumlah = len(list((config.FOLDER_DATASET / folder).glob("*.jpg")))
        total += jumlah
        baris.append(f"  {folder:<20}: {jumlah} citra")
    baris.append(f"  {'total':<20}: {total} citra")

    teks = "\n".join(baris)
    print(teks)

    # Nama berkas dibedakan supaya hasil cek di Windows dan di WSL tidak saling menimpa.
    tujuan = config.FOLDER_BUKTI / "01_lingkungan" / f"versi_perangkat_lunak_{platform.system().lower()}.txt"
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    tujuan.write_text(teks + "\n", encoding="utf-8")
    print(f"\nDisimpan ke {tujuan}")


if __name__ == "__main__":
    main()
