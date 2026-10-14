#!/usr/bin/env python3
"""baseline_carga.py - Cuantifica la carga de fondo del sistema durante el
laboratorio, leyendo /proc/stat dos veces separadas T segundos.

Uso: python3 scripts/baseline_carga.py [segundos]
"""
import sys
import time

T = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0


def leer():
    with open("/proc/stat") as f:
        line = f.readline().split()
    vals = list(map(int, line[1:]))
    # user nice system idle iowait irq softirq steal guest guest_nice
    idle = vals[3] + vals[4]
    total = sum(vals[:8])
    return idle, total, vals


i1, t1, _ = leer()
time.sleep(T)
i2, t2, _ = leer()

dt = t2 - t1
di = i2 - i1
busy = (dt - di) / dt * 100.0
print(f"Intervalo: {T:.1f} s   ticks_totales={dt}")
print(f"CPU ocupada (todas las LPs) = {busy:.2f} %   ->  ~{busy/100.0*12:.2f} de 12 LPs")
print(f"CPU ociosa                  = {(di/dt*100):.2f} %")

with open("/proc/loadavg") as f:
    print("loadavg:", f.read().strip())

print("\nTop 12 consumidores de CPU (ps):")
import subprocess
out = subprocess.run(["ps", "-eo", "comm,pcpu", "--sort=-pcpu"],
                     capture_output=True, text=True).stdout
for l in out.splitlines()[:13]:
    print(" ", l)
