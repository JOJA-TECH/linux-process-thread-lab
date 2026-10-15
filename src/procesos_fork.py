"""procesos_fork.py - Version con PROCESOS (paralelismo real, sin GIL compartido).

Uso: python3 procesos_fork.py [iteraciones] [n_procesos] [repeticion]

En Linux se usa os.fork() + tuberia (os.pipe) para comunicar los checksums al
padre, como en la version C. En Windows (donde os.fork no existe) se usa
multiprocessing con el metodo 'spawn': cada proceso hijo arranca un interprete
nuevo, ejecuta su parte y devuelve (pid, iteraciones, checksum, tiempo_cpu).

En ambos casos el trabajo TOTAL se reparte con work_for(), de modo que la suma
de iteraciones es exactamente el total. Cada proceso tiene su propio interprete
y su propio GIL, por lo que aqui SI hay paralelismo real (a diferencia de los
hilos de Python). El tiempo de CPU total es la suma del tiempo de CPU de todos
los procesos hijo.

La variable de entorno FORCE_SPAWN=1 permite usar la ruta multiprocessing
tambien en Linux (util para probarla).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from work import (BASE_SEED, DEFAULT_TOTAL, MASK, SEED_STRIDE, arg_u64,
                  children_cpu_sec, now_sec, proc_cpu_sec, report, spin_work,
                  work_for)

# Registro fijo: pid, iteraciones, checksum (3 enteros de 64 bits = 24 bytes).
REC = struct.Struct("<QQQ")
REC_SIZE = REC.size


def run_fork(total, n):
    """Linux: os.fork() + os.pipe(). Equivalente a procesos_fork.c."""
    r, w = os.pipe()
    cpu_before = children_cpu_sec()
    wall0 = now_sec()

    kids = []
    creados = 0
    for i in range(n):
        pid = os.fork()
        if pid < 0:
            sys.stderr.write("fork fallo\n")
            break
        if pid == 0:
            # ---- Proceso hijo ----
            os.close(r)  # el hijo no lee
            iters = work_for(total, n, i)
            seed = (BASE_SEED + i * SEED_STRIDE) & MASK
            s = spin_work(iters, seed)
            os.write(w, REC.pack(os.getpid(), iters, s))
            os.close(w)
            os._exit(0)  # _exit evita duplicar buffers de stdio
        kids.append(pid)
        creados += 1
    n = creados

    os.close(w)  # el padre cierra escritura para que read() vea EOF

    buf = b""
    while True:
        chunk = os.read(r, REC_SIZE * max(1, n) * 4)
        if not chunk:
            break
        buf += chunk
    os.close(r)

    checksum = 0
    for off in range(0, (len(buf) // REC_SIZE) * REC_SIZE, REC_SIZE):
        pid, iters, s = REC.unpack_from(buf, off)
        checksum ^= s
        sys.stderr.write("[fork] hijo pid=%d iters=%d checksum=%d\n" % (pid, iters, s))

    for pid in kids:
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass

    wall = now_sec() - wall0
    cpu = children_cpu_sec() - cpu_before
    report("procesos_fork", total, n, wall, cpu, checksum)
    return 0


def _mp_worker(args):
    """Trabajo de un proceso hijo (debe ser picklable: top-level)."""
    iters, seed = args
    t0 = proc_cpu_sec()
    s = spin_work(iters, seed)
    cpu = proc_cpu_sec() - t0
    sys.stderr.write("[mp] hijo pid=%d iters=%d checksum=%d\n"
                     % (os.getpid(), iters, s))
    return (os.getpid(), iters, s, cpu)


def run_spawn(total, n):
    """Windows (y FORCE_SPAWN): multiprocessing con contexto 'spawn'."""
    import multiprocessing as mp
    ctx = mp.get_context("spawn")
    args = [(work_for(total, n, i), (BASE_SEED + i * SEED_STRIDE) & MASK)
            for i in range(n)]
    wall0 = now_sec()
    with ctx.Pool(processes=n) as pool:
        res = pool.map(_mp_worker, args)
    wall = now_sec() - wall0

    checksum = 0
    cpu = 0.0
    for _pid, _iters, s, dt in res:
        checksum ^= s
        cpu += dt
    report("procesos_mp", total, n, wall, cpu, checksum)
    return 0


def main():
    total = arg_u64(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TOTAL
    n = arg_u64(sys.argv[2]) if len(sys.argv) > 2 else 4
    if n < 1:
        sys.stderr.write("n_procesos debe ser >= 1\n")
        return 1

    if hasattr(os, "fork") and not os.environ.get("FORCE_SPAWN"):
        return run_fork(total, n)
    return run_spawn(total, n)


if __name__ == "__main__":
    raise SystemExit(main())
