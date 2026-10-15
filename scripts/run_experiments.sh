#!/usr/bin/env bash
# run_experiments.sh - Ejecuta los experimentos de escalado y afinidad (Python).
#
# Uso: ./scripts/run_experiments.sh [all|threads|procs|affinity]
# Salida: resultados/mediciones.csv  (rep,mode,units,wall_s,cpu_s,util_pct,checksum)
#         resultados/raw_runs.log    (stderr de todos los programas)
#
# Todas las configuraciones usan el MISMO trabajo total (TOTAL iteraciones),
# repartido entre las unidades. Se ejecutan REPS repeticiones por configuracion.
# Debe ejecutarse desde la raíz del proyecto.
set -u

OUT=resultados/mediciones.csv
LOG=resultados/raw_runs.log
TOTAL=3000000              # iteraciones totales (secuencial ~3 s en Python)
REPS=3
WHAT="${1:-all}"
PY=python3

case "$WHAT" in
  all)      : > "$LOG"; printf 'rep,mode,units,wall_s,cpu_s,util_pct,checksum\n' > "$OUT" ;;
  threads)  : ;;
  procs)    : ;;
  affinity) : ;;
esac

run_one() {  # run_one REP LABEL cmd...
  local rep="$1"; local label="$2"; shift 2
  local out rline
  out=$("$@" 2>>"$LOG")
  rline=$(printf '%s\n' "$out" | awk '/^RESULT /{last=$0} END{print last}')
  printf '%s\n' "$rline" | awk -v rep="$rep" -v label="$label" '{
      for (i=1;i<=NF;i++){ split($i,a,"="); v[a[1]]=a[2] }
      m = (label != "") ? label : v["mode"];
      printf "%s,%s,%s,%s,%s,%s,%s\n", rep, m, v["units"], v["wall_s"], v["cpu_s"], v["util_pct"], v["checksum"]
    }' >> "$OUT"
}

echo "== Inicio $(date -Is)  (what=$WHAT) ==" | tee -a "$LOG"

if [ "$WHAT" = "all" ] || [ "$WHAT" = "threads" ]; then
  echo "-- Secuencial (1 proceso, 1 hilo) --"
  for r in $(seq 1 $REPS); do run_one "$r" "" "$PY" src/secuencial.py "$TOTAL"; done
  echo "-- Hilos threading (limitados por el GIL) --"
  for n in 1 2 4 8 12 16; do
    echo "  n=$n"
    for r in $(seq 1 $REPS); do run_one "$r" "" "$PY" src/hilos_threading.py "$TOTAL" "$n"; done
  done
fi

if [ "$WHAT" = "all" ] || [ "$WHAT" = "procs" ]; then
  echo "-- Procesos fork (paralelismo real) --"
  for n in 1 2 4 8 12 16; do
    echo "  n=$n"
    for r in $(seq 1 $REPS); do run_one "$r" "" "$PY" src/procesos_fork.py "$TOTAL" "$n"; done
  done
fi

if [ "$WHAT" = "all" ] || [ "$WHAT" = "affinity" ]; then
  echo "-- Afinidad: 4 PROCESOS en UN solo procesador logico (CPU 0) --"
  for r in $(seq 1 $REPS); do
    run_one "$r" "afinidad_proc_1lp" taskset -c 0 "$PY" src/procesos_fork.py "$TOTAL" 4
  done
  echo "-- Afinidad: 4 PROCESOS en 4 nucleos fisicos (CPU 0,2,4,6) --"
  for r in $(seq 1 $REPS); do
    run_one "$r" "afinidad_proc_4core" taskset -c 0,2,4,6 "$PY" src/procesos_fork.py "$TOTAL" 4
  done
  echo "-- Afinidad: 4 HILOS en UN solo procesador logico (CPU 0) --"
  for r in $(seq 1 $REPS); do
    run_one "$r" "afinidad_hilos_1lp" taskset -c 0 "$PY" src/hilos_threading.py "$TOTAL" 4
  done
  echo "-- Prueba de migracion (sin afinidad y con afinidad) --"
  echo "### MIGRACION libre ###" >> "$LOG"
  "$PY" src/migracion.py 2000 300 24 >> "$LOG" 2>&1
  echo "### MIGRACION taskset -c 0 ###" >> "$LOG"
  taskset -c 0 "$PY" src/migracion.py 2000 300 24 >> "$LOG" 2>&1
fi

echo "== Fin $(date -Is) ==" | tee -a "$LOG"
