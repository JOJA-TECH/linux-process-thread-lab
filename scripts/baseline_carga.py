#!/usr/bin/env python3
"""baseline_carga.py - Cuantifica la carga de fondo del sistema durante el
laboratorio.

- Linux: lee /proc/stat dos veces separadas T segundos.
- Windows: usa GetSystemTimes() (kernel32) dos veces separadas T segundos.

Uso: python3 scripts/baseline_carga.py [segundos]
"""
import sys
import time

T = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
NCPU = (__import__("os").cpu_count() or 1)


def leer_linux():
    with open("/proc/stat") as f:
        line = f.readline().split()
    vals = list(map(int, line[1:]))
    idle = vals[3] + vals[4]          # idle + iowait
    total = sum(vals[:8])
    return idle, total


def leer_windows():
    import ctypes
    from ctypes import wintypes

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD),
                    ("dwHighDateTime", wintypes.DWORD)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
    k32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel),
                       ctypes.byref(user))

    def val(ft):
        return (ft.dwHighDateTime << 32) | ft.dwLowDateTime

    return val(idle), val(kernel) + val(user)


leer = leer_windows if sys.platform == "win32" else leer_linux

i1, t1 = leer()
time.sleep(T)
i2, t2 = leer()

dt = t2 - t1
di = i2 - i1
busy = (dt - di) / dt * 100.0
print(f"Intervalo: {T:.1f} s")
print(f"CPU ocupada (todas las LPs) = {busy:.2f} %   ->  ~{busy/100.0*NCPU:.2f} de {NCPU} LPs")
print(f"CPU ociosa                  = {(di/dt*100):.2f} %")

if sys.platform == "win32":
    print("(En Windows no se lista el top de procesos; no hay `ps`.)")
else:
    with open("/proc/loadavg") as f:
        print("loadavg:", f.read().strip())
    print("\nTop 12 consumidores de CPU (ps):")
    import subprocess
    out = subprocess.run(["ps", "-eo", "comm,pcpu", "--sort=-pcpu"],
                         capture_output=True, text=True).stdout
    for l in out.splitlines()[:13]:
        print(" ", l)
