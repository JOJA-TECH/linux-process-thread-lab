#!/usr/bin/env bash
# observar_scheduler.sh - Evidencia para el Experimento 5 (version Python).
# Observa DOS cargas:
#   (a) hilos_threading con 8 hilos -> muestra que, por el GIL, solo se usa
#       ~1 CPU aunque existan 9 hilos en el proceso (cada hilo ~1/8 de core).
#   (b) procesos_fork con 8 procesos -> muestra paralelismo real: los procesos
#       hijo (PIDs distintos) usan cada uno ~100 % de una CPU.
# Guarda todo en resultados/scheduler_observacion.txt
# Debe ejecutarse desde el directorio `python/`.
set -u
OUT=resultados/scheduler_observacion.txt
PY=python3
: > "$OUT"

echo "===== $(date -Is) =====" >> "$OUT"

# ----- (a) 8 hilos de Python (GIL): ~9 s -----
$PY src/hilos_threading.py 8000000 8 >/dev/null 2>&1 &
PID_A=$!
sleep 1
{
  echo "----- (a) hilos_threading 8 hilos (GIL) -- PID $PID_A -----"
  echo "--- ps -eLf (proceso y sus hilos; NLWP = numero de hilos) ---"
  ps -eLf | head -1
  ps -eLf | awk -v p="$PID_A" '$2==p'
  echo "--- /proc/$PID_A/status (Threads, cpus_allowed_list, cambios de contexto) ---"
  awk '/^Name|^Pid|^Threads|^Cpus_allowed_list|^voluntary_ctxt_switches|^nonvoluntary_ctxt_switches/' /proc/$PID_A/status
  echo "--- pidstat -t -p $PID_A 1 5 (uso por hilo: cada hilo ~1/N de un core) ---"
  pidstat -t -p "$PID_A" 1 5 2>&1 || echo "pidstat no disponible"
  echo
} >> "$OUT" 2>&1
wait "$PID_A"

# ----- (b) 8 procesos: paralelismo real (~8 s) -----
$PY src/procesos_fork.py 60000000 8 >/dev/null 2>&1 &
PID_B=$!
sleep 1
{
  echo "----- (b) procesos_fork 8 procesos -- PID padre $PID_B -----"
  echo "--- ps -o (procesos hijo del padre; cada uno es un proceso independiente) ---"
  ps -o pid,ppid,pcpu,stat,comm --ppid "$PID_B" 2>&1 || echo "ps --ppid no disponible"
  echo "--- /proc/$PID_B/status (Threads=1: es solo el padre) ---"
  awk '/^Name|^Pid|^Threads|^Cpus_allowed_list/' /proc/$PID_B/status 2>/dev/null
  echo "--- pidstat -C python3 1 3 (el padre + los 8 hijos, cada uno ~100 %) ---"
  pidstat -C python3 1 3 2>&1 || echo "pidstat no disponible"
  echo
} >> "$OUT" 2>&1
wait "$PID_B"

echo "===== carga finalizada $(date -Is) =====" >> "$OUT"
echo "Evidencia guardada en $OUT"
