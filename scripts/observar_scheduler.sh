#!/usr/bin/env bash
# observar_scheduler.sh - Evidencia para el Experimento 5.
# Lanza una carga con 8 hilos y observa procesos/hilos/CPU con varias
# herramientas de Linux. Guarda todo en resultados/scheduler_observacion.txt
set -u
OUT=resultados/scheduler_observacion.txt
: > "$OUT"

# Carga larga (~13 s) para poder observarla en vivo.
./bin/hilos_pthread 30000000000 8 >/dev/null 2>&1 &
PID=$!
sleep 1

{
  echo "===== $(date -Is) ====="
  echo "PID observado = $PID  (hilos_pthread 8 hilos)"
  echo
  echo "----- ps -eLf (proceso y sus hilos; columnas LWP/NLWP) -----"
  # -L muestra un renglon por hilo (LWP = Light Weight Process = TID)
  ps -eLf | head -1
  ps -eLf | awk -v p="$PID" '$2==p'
  echo
  echo "----- /proc/$PID/status (Threads, cpus_allowed_list) -----"
  awk '/^Name|^Pid|^Threads|^Cpus_allowed_list|^voluntary_ctxt_switches|^nonvoluntary_ctxt_switches/' /proc/$PID/status
  echo
  echo "----- lscpu -e (uso de cada procesador logico mientras corre) -----"
  lscpu -e=CPU,CORE,ONLINE,MHZ
  echo
  echo "----- pidstat -t -p $PID 1 5 (uso por hilo, 5 muestras) -----"
  pidstat -t -p "$PID" 1 5 2>&1 || echo "pidstat no disponible"
  echo
  echo "----- top -b -n1 -H -p $PID (top por hilos, instantanea) -----"
  top -b -n1 -H -p "$PID" 2>&1 | tail -n 20
} >> "$OUT" 2>&1

wait $PID
{
  echo
  echo "===== carga finalizada $(date -Is) ====="
} >> "$OUT"
echo "Evidencia guardada en $OUT"
