"""secuencial.py - Version secuencial (1 hilo, 1 proceso) de la carga CPU-bound.

Uso: python3 secuencial.py [iteraciones] [repeticion]
  iteraciones : total de iteraciones de trabajo (por defecto 3000000)
  repeticion  : solo una etiqueta para los registros (no afecta el trabajo)

Mide tiempo de pared (perf_counter) y tiempo de CPU del proceso.
Equivalente a la version C secuencial.c.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from work import (BASE_SEED, DEFAULT_TOTAL, arg_u64, now_sec, proc_cpu_sec,
                  report, spin_work)


def main():
    iters = arg_u64(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TOTAL

    t0_wall = now_sec()
    t0_cpu = proc_cpu_sec()

    checksum = spin_work(iters, BASE_SEED)

    wall = now_sec() - t0_wall
    cpu = proc_cpu_sec() - t0_cpu

    report("secuencial", iters, 1, wall, cpu, checksum)


if __name__ == "__main__":
    main()
