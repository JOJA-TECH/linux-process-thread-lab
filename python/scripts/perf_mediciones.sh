#!/usr/bin/env bash
# perf_mediciones.sh - Mide contadores de hardware/software con perf stat
# (version Python). Salida -> resultados/perf_mediciones.txt
# Debe ejecutarse desde el directorio `python/`.
#
# Eventos:
#   cycles, instructions        -> IPC = instructions/cycles
#   branches, branch-misses     -> tasa de fallo de prediccion
#   cache-references, cache-misses
#   context-switches, cpu-migrations
#   task-clock
# Para que aparezcan context-switches/cpu-migrations (eventos de kernel) hay que
# ejecutar con sudo:
#   sudo env OUT=resultados/perf_sudo.txt ./scripts/perf_mediciones.sh
set -u
OUT="${OUT:-resultados/perf_mediciones.txt}"
EVENTS="cycles,instructions,branches,branch-misses,cache-references,cache-misses,context-switches,cpu-migrations,task-clock"
TOTAL=3000000          # el mismo total que los experimentos; perf solo instrumenta
PY=python3

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

correr "secuencial (1 unidad)"        $PY src/secuencial.py   "$TOTAL"
correr "hilos 1"                      $PY src/hilos_threading.py "$TOTAL" 1
correr "hilos 4"                      $PY src/hilos_threading.py "$TOTAL" 4
correr "hilos 8"                      $PY src/hilos_threading.py "$TOTAL" 8
correr "hilos 12"                     $PY src/hilos_threading.py "$TOTAL" 12
correr "hilos 16"                     $PY src/hilos_threading.py "$TOTAL" 16
correr "procesos 4"                   $PY src/procesos_fork.py "$TOTAL" 4
correr "afinidad proc 1 LP (4 proc)"  taskset -c 0 $PY src/procesos_fork.py "$TOTAL" 4

echo "Listo -> $OUT"
