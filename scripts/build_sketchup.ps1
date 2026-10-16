param([string]$Python = 'C:\python\Python38\python.exe', [switch]$Install)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$cmake = (Get-Command cmake -ErrorAction SilentlyContinue).Source
if (!$cmake) { $cmake = 'C:\Program Files\CMake\bin\cmake.exe' }
$source = Join-Path $projectRoot 'native\sketchup'
$build = Join-Path $projectRoot 'build\sketchup'
& $cmake -S $source -B $build -G 'Visual Studio 16 2019' -A x64 "-DPython_EXECUTABLE=$Python"
if ($LASTEXITCODE) { throw 'SketchUp CMake configuration failed' }
& $cmake --build $build --config Release --parallel
if ($LASTEXITCODE) { throw 'SketchUp native build failed' }
if ($Install) {
    & $cmake --install $build --config Release --prefix (Join-Path $projectRoot 'importers\sketchup')
    if ($LASTEXITCODE) { throw 'SketchUp native installation failed' }
}
