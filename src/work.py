"""work.py - Carga de trabajo CPU-bound determinista y utilidades de medicion.

EQUIVALENCIA BIT A BIT CON LA VERSION C (work.h):
  La carga es el mismo generador xorshift64 sobre enteros de 64 bits sin signo,
  con la misma constante de mezcla y la misma semilla por unidad. Como Python
  usa enteros de precision arbitraria, cada operacion se enmascara a 64 bits
  (MASK) para reproducir el desbordamiento modular de uint64_t en C. Con esto
  los checksums de la version Python COINCIDEN EXACTAMENTE con los de la C,
  lo que permite validar el trabajo entre implementaciones.

La carga incluye una dependencia encadenada (loop-carried) que impide
optimizaciones, y el resultado se acumula en un sumidero global para que el
interprete no pueda eliminar el bucle.
"""
import ctypes
import os
import sys
import time

MASK = (1 << 64) - 1
WORK_MIX = 0x9E3779B97F4A7C15

# Semillas (identicas a la version C) y trabajo total por defecto (Python es
# ~400x mas lento por iteracion que C, por eso el total es mucho menor).
BASE_SEED = 0x123456789ABCDEF
SEED_STRIDE = 0x100000001B3
DEFAULT_TOTAL = 3000000

# Sumidero global (equivalente a `volatile uint64_t g_sink`).
g_sink = 0


def spin_work(iters, seed):
    """iters iteraciones de aritmetica entera de 64 bits con dependencia
    secuencial. Devuelve un checksum determinista que solo depende de
    (iters, seed). Es bit a bit igual a spin_work() de la version C."""
    x = (seed | 1) & MASK  # nunca 0: xorshift con estado 0 queda atrapado
    for i in range(iters):
        x = (x ^ ((x << 13) & MASK)) & MASK
        x ^= x >> 7
        x = (x ^ ((x << 17) & MASK)) & MASK
        x = (x + i * WORK_MIX) & MASK
    return x


def now_sec():
    """Tiempo de pared (monotonico) de alta resolucion, en segundos."""
    return time.perf_counter()


def proc_cpu_sec():
    """Tiempo de CPU del PROCESO completo (suma de todos sus hilos), en
    segundos. Equivale a CLOCK_PROCESS_CPUTIME_ID de Linux."""
    return time.process_time()


def children_cpu_sec():
    """Tiempo de CPU acumulado por los procesos hijo (user+sys). Equivale a
    getrusage(RUSAGE_CHILDREN) de Linux."""
    t = os.times()
    return t.children_user + t.children_system


def split_work(total, n):
    """Reparte `total` iteraciones en `n` partes lo mas iguales posible.
    Devuelve (chunk, remainder): cada parte vale chunk (+1 si su indice es
    menor que remainder). La suma de las partes es exactamente `total`."""
    return total // n, total % n


def work_for(total, n, idx):
    """Iteraciones asignadas a la unidad `idx` (0-based) de `n` unidades."""
    chunk, rem = split_work(total, n)
    return chunk + (1 if idx < rem else 0)


def logical_cpus():
    """Numero de procesadores logicos online (equivale a
    sysconf(_SC_NPROCESSORS_ONLN)). Usa el total de CPUs del sistema, NO la
    mascara de afinidad, para que coincida con la version C aun bajo taskset."""
    return os.cpu_count() or 1


# ---- Acceso al procesador logico actual: multiplataforma ------------------
# Linux : sched_getcpu(3) de libc (os.sched_getcpu no esta en todas las builds)
# Windows: GetCurrentProcessorNumber() de kernel32
def _init_getcpu():
    if sys.platform == "win32":
        try:
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.GetCurrentProcessorNumber.restype = ctypes.c_ulong
            return ("win", k32)
        except OSError:
            return None
    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        libc.sched_getcpu.restype = ctypes.c_int
        return ("libc", libc)
    except OSError:
        return None


_GETCPU = _init_getcpu()


def sched_getcpu():
    """Procesador logico en el que corre el hilo que llama, o -1 si no se
    puede determinar. En Linux equivale a sched_getcpu(3); en Windows usa
    GetCurrentProcessorNumber()."""
    if _GETCPU:
        kind, lib = _GETCPU
        if kind == "win":
            return int(lib.GetCurrentProcessorNumber())
        return int(lib.sched_getcpu())
    try:  # Reserva en Linux: campo 39 (processor) de /proc/self/stat (por hilo).
        with open("/proc/self/stat") as f:
            return int(f.read().rsplit(")", 1)[1].split()[36])
    except Exception:
        return -1


def yield_cpu():
    """Cede la CPU al planificador (os.sched_yield en Linux; time.sleep(0) en
    Windows, que fuerza un cambio de contexto cooperativo)."""
    if hasattr(os, "sched_yield"):
        os.sched_yield()
    else:
        time.sleep(0)


# ---- Afinidad de CPU: multiplataforma -------------------------------------
# Se puede fijar con la variable de entorno AFFINITY="0" o "0,2,4,6", que
# reproduce el efecto de `taskset -c` en Linux y de la mascara de afinidad en
# Windows. Se aplica al importar el modulo, de modo que los procesos hijos lo
# heredan.
def apply_affinity(spec):
    cpus = [int(x) for x in spec.split(",") if x.strip() != ""]
    if not cpus:
        return
    if hasattr(os, "sched_setaffinity"):          # Linux
        os.sched_setaffinity(0, set(cpus))
    elif sys.platform == "win32":                  # Windows
        mask = 0
        for c in cpus:
            mask |= (1 << c)
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        k32.SetProcessAffinityMask.restype = ctypes.c_int
        if not k32.SetProcessAffinityMask(k32.GetCurrentProcess(),
                                          ctypes.c_size_t(mask)):
            raise OSError(ctypes.get_last_error(), "SetProcessAffinityMask")


_env_affinity = os.environ.get("AFFINITY")
if _env_affinity:
    apply_affinity(_env_affinity)



def arg_u64(s):
    """Lectura de argumento entero no negativo con validacion."""
    try:
        v = int(s)
    except ValueError:
        sys.stderr.write("argumento no valido: '%s'\n" % s)
        raise SystemExit(1)
    if v < 0:
        sys.stderr.write("argumento no valido: '%s'\n" % s)
        raise SystemExit(1)
    return v


def report(mode, total, units, wall, cpu, checksum):
    """Impresion uniforme y parseable por scripts (mismo formato que la C)."""
    util = (cpu / wall * 100.0) if wall > 0 else 0.0
    print("RESULT mode=%s units=%d logical_cpus=%d total_iters=%d "
          "wall_s=%.6f cpu_s=%.6f util_pct=%.2f checksum=%d"
          % (mode, units, logical_cpus(), total, wall, cpu, util, checksum))


if __name__ == "__main__":
    # Pequena autoprueba: imprime checksums para comparar con la version C.
    for iters, seed in [(0, 0xABCDEF), (1, 1), (1000, 0x123456789ABCDEF),
                        (100000, 0xABCDEF)]:
        print("iters=%d seed=%d checksum=%d" % (iters, seed, spin_work(iters, seed)))
