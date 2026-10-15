# run_experiments.ps1 - Version Windows (PowerShell) de run_experiments.sh.
#
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\run_experiments.ps1
#       powershell -ExecutionPolicy Bypass -File scripts\run_experiments.ps1 procs
#
# Genera:
#   resultados\mediciones.csv   (rep,mode,units,wall_s,cpu_s,util_pct,checksum)
#   resultados\raw_runs.log     (stderr de todos los programas)
#
# Notas:
#   - En Windows os.fork no existe: la version de procesos usa multiprocessing.
#   - La afinidad se fija con la variable de entorno AFFINITY ("0" o "0,2,4,6").
#   - Ejecutar desde la raiz del proyecto.

param([string]$What = "all")

# Los programas escriben trazas en stderr (p.ej. "[mp] hijo ..."); con
# ErrorActionPreference = "Stop" PowerShell las trata como errores terminantes.
# Usamos "Continue" y comprobamos $LASTEXITCODE manualmente.
$ErrorActionPreference = "Continue"
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false   # PowerShell 7.3+
}

$OUT   = "resultados\mediciones.csv"
$LOG   = "resultados\raw_runs.log"
$TOTAL = 3000000      # trabajo total (secuencial ~3 s en Python)
$REPS  = 3
$PY    = "python"

if (!(Test-Path "resultados")) { New-Item -ItemType Directory -Path "resultados" | Out-Null }

if ($What -eq "all") {
    "rep,mode,units,wall_s,cpu_s,util_pct,checksum" | Set-Content -Encoding ascii $OUT
    "== Inicio $(Get-Date -Format o)  (what=$What) ==" | Set-Content -Encoding ascii $LOG
}

function Run-One {
    param([int]$Rep, [string]$Label, [string[]]$CmdArgs)
    $out = & $PY @CmdArgs 2>> $LOG
    if ($LASTEXITCODE -ne 0) { Write-Warning "salida ${LASTEXITCODE}: $($CmdArgs -join ' ')" }
    $rline = ($out | Where-Object { $_ -match '^RESULT ' } | Select-Object -Last 1)
    if (-not $rline) { return }
    $h = @{}
    foreach ($tok in ($rline -split '\s+')) {
        $kv = $tok -split '=', 2
        if ($kv.Count -eq 2) { $h[$kv[0]] = $kv[1] }
    }
    $mode = if ($Label) { $Label } else { $h['mode'] }
    "$Rep,$mode,$($h['units']),$($h['wall_s']),$($h['cpu_s']),$($h['util_pct']),$($h['checksum'])" |
        Add-Content -Encoding ascii $OUT
}

function Run-Config {
    param([string]$Label, [string[]]$CmdArgs)
    for ($r = 1; $r -le $REPS; $r++) { Run-One -Rep $r -Label $Label -CmdArgs $CmdArgs }
}

if ($What -eq "all" -or $What -eq "threads") {
    Write-Host "-- Secuencial (1 proceso, 1 hilo) --"
    Run-Config -Label "" -CmdArgs @("src/secuencial.py", "$TOTAL")
    Write-Host "-- Hilos threading (limitados por el GIL) --"
    foreach ($n in 1, 2, 4, 8, 12, 16) {
        Write-Host "  n=$n"
        Run-Config -Label "" -CmdArgs @("src/hilos_threading.py", "$TOTAL", "$n")
    }
}

if ($What -eq "all" -or $What -eq "procs") {
    Write-Host "-- Procesos (multiprocessing/spawn: paralelismo real) --"
    foreach ($n in 1, 2, 4, 8, 12, 16) {
        Write-Host "  n=$n"
        Run-Config -Label "" -CmdArgs @("src/procesos_fork.py", "$TOTAL", "$n")
    }
}

if ($What -eq "all" -or $What -eq "affinity") {
    Write-Host "-- Afinidad: 4 PROCESOS en 1 LP (CPU 0) --"
    $env:AFFINITY = "0"
    Run-Config -Label "afinidad_proc_1lp" -CmdArgs @("src/procesos_fork.py", "$TOTAL", "4")
    Write-Host "-- Afinidad: 4 PROCESOS en 4 nucleos (CPU 0,2,4,6) --"
    $env:AFFINITY = "0,2,4,6"
    Run-Config -Label "afinidad_proc_4core" -CmdArgs @("src/procesos_fork.py", "$TOTAL", "4")
    Write-Host "-- Afinidad: 4 HILOS en 1 LP (CPU 0) --"
    $env:AFFINITY = "0"
    Run-Config -Label "afinidad_hilos_1lp" -CmdArgs @("src/hilos_threading.py", "$TOTAL", "4")
    Remove-Item Env:\AFFINITY -ErrorAction SilentlyContinue

    Write-Host "-- Prueba de migracion (libre y con afinidad) --"
    "### MIGRACION libre ###" | Add-Content -Encoding ascii $LOG
    & $PY src/migracion.py 2000 300 24 *>> $LOG
    $env:AFFINITY = "0"
    "### MIGRACION afinidad 0 ###" | Add-Content -Encoding ascii $LOG
    & $PY src/migracion.py 2000 300 24 *>> $LOG
    Remove-Item Env:\AFFINITY -ErrorAction SilentlyContinue
}

"== Fin $(Get-Date -Format o) ==" | Add-Content -Encoding ascii $LOG
Write-Host "Listo -> $OUT"
