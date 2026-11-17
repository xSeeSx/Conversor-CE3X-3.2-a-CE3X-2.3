$ErrorActionPreference = 'Stop'
$packageRoot = Split-Path -Parent $PSScriptRoot
if (-not (Get-Command zig -ErrorAction SilentlyContinue)) {
    throw 'Instala Zig 0.13.0 y anade zig.exe al PATH antes de compilar.'
}
& zig cc -target x86_64-windows-gnu -O2 -municode '-Wl,--subsystem,windows' `
    (Join-Path $PSScriptRoot 'launcher.c') `
    -o (Join-Path $packageRoot 'Conversor_CE3X.exe') `
    -lcomdlg32 -lshell32 -lole32 -luuid -lgdi32 -luser32
if ($LASTEXITCODE -ne 0) { throw 'Ha fallado la compilacion del lanzador.' }
Write-Host 'Conversor_CE3X.exe compilado.'
