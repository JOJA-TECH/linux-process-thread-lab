"""procesos_fork.py - Version con PROCESOS para Linux (os.fork / os.pipe).

Uso: python3 procesos_fork.py [iteraciones] [n_procesos] [repeticion]

El proceso padre crea n procesos hijo con os.fork(). Cada hijo recibe su parte
del trabajo TOTAL (work_for), la ejecuta y comunica su checksum al padre por una
tuberia (os.pipe) con un registro de tamano fijo. Los espacios de direcciones
son independientes (cada hijo tiene su propia copia); la unica comunicacion es
la tuberia. A diferencia de los hilos de Python, aqui SI hay paralelismo real:
cada proceso tiene su propio interprete y su propio GIL.

El padre espera a cada hijo con os.waitpid() y acumula el uso de CPU de los
hijos mediante os.times() (children_user + children_system), de modo que la
utilizacion incluye el tiempo de CPU de los procesos hijo.
Equivalente a la version C procesos_fork.c.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from work import (BASE_SEED, DEFAULT_TOTAL, MASK, SEED_STRIDE, arg_u64,
                  children_cpu_sec, now_sec, report, spin_work, work_for)

# Registro fijo: pid, iteraciones, checksum (3 enteros de 64 bits = 24 bytes).
REC = struct.Struct("<QQQ")
REC_SIZE = REC.size


def main():
    total = arg_u64(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TOTAL
    n = arg_u64(sys.argv[2]) if len(sys.argv) > 2 else 4
    if n < 1:
        sys.stderr.write("n_procesos debe ser >= 1\n")
        return 1

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

    # El padre cierra el extremo de escritura para que read() vea EOF.
    os.close(w)

    # Leer todos los registros completos.
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

    # Esperar a TODOS los hijos.
    for pid in kids:
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass

    wall = now_sec() - wall0
    cpu = children_cpu_sec() - cpu_before

    report("procesos_fork", total, n, wall, cpu, checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
