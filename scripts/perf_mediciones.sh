#!/usr/bin/env bash
# perf_mediciones.sh - Mide contadores de hardware/software con perf stat para
# las configuraciones clave. Salida -> resultados/perf_mediciones.txt
#
# Eventos:
#   cycles, instructions        -> IPC = instructions/cycles
#   branches, branch-misses     -> tasa de fallo de prediccion
#   cache-references, cache-misses
#   context-switches, cpu-migrations
#   task-clock
set -u
OUT="${OUT:-resultados/perf_mediciones.txt}"
EVENTS="cycles,instructions,branches,branch-misses,cache-references,cache-misses,context-switches,cpu-migrations,task-clock"
TOTAL=800000000

: > "$OUT"

correr() {  # correr <etiqueta> <comando...>
  local label="$1"; shift
  {
    echo "############################################################"
    echo "### $label"
    echo "### cmd: $*"
    echo "############################################################"
  } >> "$OUT"
  perf stat -e "$EVENTS" "$@" >> "$OUT" 2>&1
  echo >> "$OUT"
}

correr "secuencial (1 unidad)"        ./bin/secuencial   "$TOTAL"
correr "hilos 1"                      ./bin/hilos_pthread "$TOTAL" 1
correr "hilos 4"                      ./bin/hilos_pthread "$TOTAL" 4
correr "hilos 8"                      ./bin/hilos_pthread "$TOTAL" 8
correr "hilos 12"                     ./bin/hilos_pthread "$TOTAL" 12
correr "hilos 16"                     ./bin/hilos_pthread "$TOTAL" 16
correr "procesos 4"                   ./bin/procesos_fork "$TOTAL" 4
correr "afinidad 1 LP (4 hilos)"      taskset -c 0 ./bin/hilos_pthread "$TOTAL" 4

echo "Listo -> $OUT"
