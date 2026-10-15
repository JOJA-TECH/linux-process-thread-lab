"""hilos_threading.py - Version con HILOS de Python (threading).

Uso: python3 hilos_threading.py [iteraciones] [n_hilos] [repeticion]

IMPORTANTE (hilo conductor del informe): en CPython, el GIL (Global
Interpreter Lock) permite que solo UN hilo ejecute bytecode de Python a la vez.
Por eso esta version NO acelera cargas CPU-bound puras en Python, aunque las
tareas SI son concurrentes. Es el contraste clave con la version C (pthreads),
donde los hilos si aprovechan varios nucleos.

El trabajo TOTAL se reparte igual que en C con work_for(), de modo que la suma
de iteraciones es exactamente el total, sea cual sea el numero de hilos. Cada
hilo escribe su checksum en una casilla propia (sin mutex); se sincroniza con
Thread.join().
"""
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from work import (BASE_SEED, DEFAULT_TOTAL, MASK, SEED_STRIDE, arg_u64,
                  now_sec, proc_cpu_sec, report, spin_work, work_for)


def thread_main(iters, seed, out, idx):
    out[idx] = spin_work(iters, seed)


def main():
    total = arg_u64(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TOTAL
    n = arg_u64(sys.argv[2]) if len(sys.argv) > 2 else 4
    if n < 1:
        sys.stderr.write("n_hilos debe ser >= 1\n")
        return 1

    iters_list = [work_for(total, n, i) for i in range(n)]
    seeds = [(BASE_SEED + i * SEED_STRIDE) & MASK for i in range(n)]
    out = [0] * n

    t0_wall = now_sec()
    t0_cpu = proc_cpu_sec()

    threads = []
    for i in range(n):
        t = threading.Thread(target=thread_main,
                             args=(iters_list[i], seeds[i], out, i))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    checksum = 0
    for v in out:
        checksum ^= v

    wall = now_sec() - t0_wall
    cpu = proc_cpu_sec() - t0_cpu

    report("hilos_threading", total, n, wall, cpu, checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
