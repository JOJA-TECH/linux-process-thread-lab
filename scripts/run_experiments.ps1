# run_experiments.ps1 - Lanzador de Windows.
#
# Toda la logica esta en scripts/run_experiments.py (multiplataforma), que
# captura stdout/stderr de cada programa sin depender de la redireccion de
# PowerShell (que interpreta el stderr de los procesos nativos como errores).
#
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\run_experiments.ps1
#       powershell -ExecutionPolicy Bypass -File scripts\run_experiments.ps1 procs
#
# Genera:
#   resultados\mediciones.csv   (rep,mode,units,wall_s,cpu_s,util_pct,checksum)
#   resultados\raw_runs.log     (stdout/stderr de todos los programas)
#
# Ejecutar desde la raiz del proyecto.

param([string]$What = "all")

$ErrorActionPreference = "Continue"

python scripts\run_experiments.py $What
if ($LASTEXITCODE -ne 0) {
    Write-Warning "run_experiments.py termino con codigo ${LASTEXITCODE}"
}
