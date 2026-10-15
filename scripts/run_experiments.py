#!/usr/bin/env python3
"""run_experiments.py - Orquestador multiplataforma (Linux y Windows).

Equivale a run_experiments.sh, pero sin bash ni PowerShell: usa subprocess
directamente, de modo que funciona igual en ambos sistemas y evita los
problemas de redireccion de stderr de PowerShell.

Uso:  python scripts/run_experiments.py [all|threads|procs|affinity]

Salida:
  resultados/mediciones.csv   (rep,mode,units,wall_s,cpu_s,util_pct,checksum)
  resultados/raw_runs.log     (stdout/stderr de todos los programas)

Variables de entorno opcionales: TOTAL (iteraciones), REPS (repeticiones).
Ejecutar desde la raiz del proyecto.
"""
import os
import subprocess
import sys
import time

OUT = os.path.join("resultados", "mediciones.csv")
LOG = os.path.join("resultados", "raw_runs.log")
TOTAL = int(os.environ.get("TOTAL", "3000000"))
REPS = int(os.environ.get("REPS", "3"))
WHAT = sys.argv[1] if len(sys.argv) > 1 else "all"
PY = sys.executable


def env_for(affinity):
    e = dict(os.environ)
    if affinity:
        e["AFFINITY"] = affinity
    else:
        e.pop("AFFINITY", None)
    return e


def run_one(rep, label, args, affinity=None):
    p = subprocess.run([PY] + args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env=env_for(affinity))
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(p.stderr)
    rline = None
    for line in p.stdout.splitlines():
        if line.startswith("RESULT "):
            rline = line
    if rline is None:
        sys.stderr.write("  (sin RESULT) %s\n" % " ".join(args))
        return
    h = {}
    for tok in rline.split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            h[k] = v
    mode = label or h.get("mode", "")
    with open(OUT, "a", encoding="ascii", newline="") as f:
        f.write("%d,%s,%s,%s,%s,%s,%s\n" % (
            rep, mode, h.get("units", ""), h.get("wall_s", ""),
            h.get("cpu_s", ""), h.get("util_pct", ""), h.get("checksum", "")))


def config(label, args, affinity=None):
    for r in range(1, REPS + 1):
        run_one(r, label, args, affinity)


def run_raw(args, affinity=None):
    p = subprocess.run([PY] + args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env=env_for(affinity))
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(p.stdout)
        f.write(p.stderr)


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)


def main():
    os.makedirs("resultados", exist_ok=True)

    if WHAT == "all":
        open(LOG, "w", encoding="utf-8").close()
        with open(OUT, "w", encoding="ascii", newline="") as f:
            f.write("rep,mode,units,wall_s,cpu_s,util_pct,checksum\n")

    log("== Inicio %s  (what=%s) ==" % (time.strftime("%Y-%m-%dT%H:%M:%S"), WHAT))

    if WHAT in ("all", "threads"):
        log("-- Secuencial (1 proceso, 1 hilo) --")
        config("", ["src/secuencial.py", str(TOTAL)])
        log("-- Hilos threading (limitados por el GIL) --")
        for n in (1, 2, 4, 8, 12, 16):
            print("  n=%d" % n)
            config("", ["src/hilos_threading.py", str(TOTAL), str(n)])

    if WHAT in ("all", "procs"):
        log("-- Procesos (fork en Linux / multiprocessing en Windows) --")
        for n in (1, 2, 4, 8, 12, 16):
            print("  n=%d" % n)
            config("", ["src/procesos_fork.py", str(TOTAL), str(n)])

    if WHAT in ("all", "affinity"):
        log("-- Afinidad: 4 PROCESOS en UN solo procesador logico (CPU 0) --")
        config("afinidad_proc_1lp",
               ["src/procesos_fork.py", str(TOTAL), "4"], "0")
        log("-- Afinidad: 4 PROCESOS en 4 nucleos fisicos (CPU 0,2,4,6) --")
        config("afinidad_proc_4core",
               ["src/procesos_fork.py", str(TOTAL), "4"], "0,2,4,6")
        log("-- Afinidad: 4 HILOS en UN solo procesador logico (CPU 0) --")
        config("afinidad_hilos_1lp",
               ["src/hilos_threading.py", str(TOTAL), "4"], "0")

        log("### MIGRACION libre ###")
        run_raw(["src/migracion.py", "2000", "300", "24"])
        log("### MIGRACION AFFINITY=0 ###")
        run_raw(["src/migracion.py", "2000", "300", "24"], "0")

    log("== Fin %s ==" % time.strftime("%Y-%m-%dT%H:%M:%S"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
