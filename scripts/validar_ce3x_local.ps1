[CmdletBinding()]
param(
    [ValidateSet('Preparar','Aceptar','Estado','Recoger','Pruebas','Entorno','Ayuda')]
    [string]$Modo = 'Ayuda',
    [string]$Carpeta,
    [string]$Origen32,
    [string]$Nativo23,
    [string]$Consentimiento,
    [string]$Python = 'python',
    [string]$CE3X23 = 'C:\Program Files (x86)\CEXv2.3\cexv2.3.exe',
    [string]$CE3X32 = 'C:\Program Files (x86)\CE3Xv3.2\ce3xv3.2.exe',
    [switch]$MuestraPublica
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
if ($Modo -eq 'Ayuda') {
    @'
Entorno     comprueba Python, PowerShell y los ejecutables locales.
Pruebas     ejecuta la regresión automatizada desde el repositorio.
Preparar    -Carpeta <nueva> -Origen32 <cex> [-Nativo23 <cex equivalente>]
Aceptar     -Carpeta <existente> -Consentimiento <token mostrado al preparar>
Estado      -Carpeta <existente> muestra solo los pasos pendientes.
Recoger     -Carpeta <existente> genera resumen.json e indicadores.csv.

Usa una carpeta fuera del repositorio para proyectos reales. Se puede usar
-MuestraPublica con muestras oficiales o sintéticas dentro del repositorio.
Recalcula y exporta el XML desde CE3X sobre las copias que indica Estado.
'@
    return
}
if ($Modo -eq 'Entorno') {
    "PowerShell $($PSVersionTable.PSVersion)"
    & $Python --version
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
    foreach ($candidate in @($CE3X23, $CE3X32)) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $file = Get-Item -LiteralPath $candidate
            "$($file.VersionInfo.FileVersion)  $($file.FullName)"
        } else {
            "No encontrado  $candidate"
        }
    }
    $zig = Get-Command zig -ErrorAction SilentlyContinue
    if ($zig) { & $zig.Source version } else { 'Zig no está en PATH' }
    return
}
if ($Modo -eq 'Pruebas') {
    & $Python -B -X utf8 -m unittest discover -s (Join-Path $repo 'fuentes') -q
    exit $LASTEXITCODE
}
if (-not $Carpeta) { throw 'Indica -Carpeta. Usa -Modo Ayuda para ver los requisitos.' }
$arguments = @($Modo.ToLowerInvariant(), '--directory', $Carpeta)
if ($Origen32) { $arguments += @('--source32', $Origen32) }
if ($Nativo23) { $arguments += @('--native23', $Nativo23) }
if ($Consentimiento) { $arguments += @('--consent', $Consentimiento) }
if ($MuestraPublica) { $arguments += '--public-fixture' }
& $Python -B -X utf8 (Join-Path $PSScriptRoot 'validar_ce3x_local.py') @arguments
exit $LASTEXITCODE
