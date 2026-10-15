"""migracion.py - Evidencia de migracion de hilos entre procesadores logicos.

Uso: python3 migracion.py [iteraciones_por_lote] [n_lotes] [n_workers]

Cada hilo ejecuta lotes cortos de trabajo CPU-bound, cede la CPU
(os.sched_yield) y, entre lote y lote, consulta con sched_getcpu() en que
procesador logico esta corriendo. Registra el conjunto de CPUs observados y
cuenta los cambios (migraciones).

Nota: en CPython, por el GIL, los hilos de Python no se ejecutan en paralelo en
varios nucleos; sin embargo, el SO SIGUE planificando el hilo y puede moverlo de
un LP a otro entre cesiones, por lo que la migracion es observable igualmente.
Para ver paralelismo real, usar la version de procesos.

Equivalente a la version C migracion.c.
"""
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from work import arg_u64, logical_cpus, sched_getcpu, spin_work, yield_cpu

# Sumidero local por hilo (evita que el resultado se descarte).
_sink = 0


def worker(iters, lotes, wid, results):
    global _sink
    seen = set()
    last = -1
    migrations = 0
    acc = 0
    for l in range(lotes):
        acc ^= spin_work(iters, 0xABCDEF + l)
        cpu = sched_getcpu()
        if cpu is not None and cpu >= 0:
            seen.add(cpu)
            if last != -1 and cpu != last:
                migrations += 1
            last = cpu
        yield_cpu()  # da oportunidad al scheduler de balancear/migrar
    _sink ^= acc
    results[wid] = (len(seen), migrations, sorted(seen))


def main():
    iters_lote = arg_u64(sys.argv[1]) if len(sys.argv) > 1 else 100000
    lotes = arg_u64(sys.argv[2]) if len(sys.argv) > 2 else 300
    nworkers = arg_u64(sys.argv[3]) if len(sys.argv) > 3 else 24

    print("INICIO pid=%d cpu_actual=%d logical_cpus=%d n_workers=%d"
          % (os.getpid(), sched_getcpu(), logical_cpus(), nworkers))

    results = [None] * nworkers
    threads = []
    for i in range(nworkers):
        t = threading.Thread(target=worker, args=(iters_lote, lotes, i, results))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    for i in range(nworkers):
        distinct, migrations, lista = results[i]
        print("  worker %2d: distinct_cpus=%d migrations=%d lista=%s"
              % (i, distinct, migrations, " ".join(str(c) for c in lista)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
