[CmdletBinding()]
param(
    [switch]$Check
)

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$sourceRoot = Join-Path $repositoryRoot 'Core\Src'
$outputPath = Join-Path $repositoryRoot 'Core\DratCore.cpd'
$moduleNames = @(
    'CoreManifest.cpd'
    'Stylesheet.cpd'
    'Definitions.cpd'
    'DataWrapper.cpd'
    'Checks.cpd'
    'Database.cpd'
    'Validation.cpd'
    'Plotting.cpd'
)

$sections = foreach ($moduleName in $moduleNames) {
    $modulePath = Join-Path $sourceRoot $moduleName
    if (-not (Test-Path -LiteralPath $modulePath -PathType Leaf)) {
        throw "Missing core source module: $modulePath"
    }

    [System.IO.File]::ReadAllText($modulePath).TrimEnd("`r", "`n")
}

$bundle = ($sections -join "`r`n") + "`r`n"

if ($Check) {
    if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
        Write-Error "Generated core bundle is missing: $outputPath"
        exit 1
    }

    $existingBundle = [System.IO.File]::ReadAllText($outputPath)
    if ($existingBundle -cne $bundle) {
        Write-Error 'Core/DratCore.cpd is stale. Run Tools/BuildCore.ps1.'
        exit 1
    }

    Write-Output 'Core/DratCore.cpd is current.'
    exit 0
}

$utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($outputPath, $bundle, $utf8WithoutBom)
Write-Output "Generated $outputPath"
