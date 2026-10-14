#!/usr/bin/env bash
# run_experiments.sh - Ejecuta los experimentos de escalado y afinidad.
#
# Uso: ./scripts/run_experiments.sh [all|threads|procs|affinity]
# Salida: resultados/mediciones.csv  (rep,mode,units,wall_s,cpu_s,util_pct,checksum)
#         resultados/raw_runs.log    (stderr de todos los programas)
#
# Todas las configuraciones usan el MISMO trabajo total (TOTAL iteraciones),
# repartido entre las unidades. Se ejecutan REPS repeticiones por configuracion.
set -u

BIN=./bin
OUT=resultados/mediciones.csv
LOG=resultados/raw_runs.log
TOTAL=800000000          # iteraciones totales (secuencial ~2.7 s en este equipo)
REPS=3
WHAT="${1:-all}"

case "$WHAT" in
  all)      : > "$OUT"; printf 'rep,mode,units,wall_s,cpu_s,util_pct,checksum\n' > "$OUT"; : > "$LOG" ;;
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
  for r in $(seq 1 $REPS); do run_one "$r" "" "$BIN/secuencial" "$TOTAL"; done
  echo "-- Hilos pthread --"
  for n in 1 2 4 8 12 16; do
    echo "  n=$n"
    for r in $(seq 1 $REPS); do run_one "$r" "" "$BIN/hilos_pthread" "$TOTAL" "$n"; done
  done
fi

if [ "$WHAT" = "all" ] || [ "$WHAT" = "procs" ]; then
  echo "-- Procesos fork --"
  for n in 1 2 4 8 12 16; do
    echo "  n=$n"
    for r in $(seq 1 $REPS); do run_one "$r" "" "$BIN/procesos_fork" "$TOTAL" "$n"; done
  done
fi

if [ "$WHAT" = "all" ] || [ "$WHAT" = "affinity" ]; then
  echo "-- Afinidad: 4 hilos en UN solo procesador logico (CPU 0) --"
  for r in $(seq 1 $REPS); do
    run_one "$r" "afinidad_1lp" taskset -c 0 "$BIN/hilos_pthread" "$TOTAL" 4
  done
  echo "-- Afinidad: 4 hilos en 4 nucleos fisicos (CPU 0,2,4,6) --"
  for r in $(seq 1 $REPS); do
    run_one "$r" "afinidad_4core" taskset -c 0,2,4,6 "$BIN/hilos_pthread" "$TOTAL" 4
  done
  echo "-- Prueba de migracion (sin afinidad y con afinidad) --"
  echo "### MIGRACION libre ###" >> "$LOG"
  "$BIN/migracion" 2000000 300 >> "$LOG" 2>&1
  echo "### MIGRACION taskset -c 0 ###" >> "$LOG"
  taskset -c 0 "$BIN/migracion" 2000000 300 >> "$LOG" 2>&1
fi

echo "== Fin $(date -Is) ==" | tee -a "$LOG"
