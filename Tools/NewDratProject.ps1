[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$DestinationPath,
    [string]$InstallationPath,
    [switch]$IncludeMaterials
)

if ([string]::IsNullOrWhiteSpace($InstallationPath)) {
    if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        throw 'LOCALAPPDATA is unavailable. Supply -InstallationPath explicitly.'
    }
    $InstallationPath = Join-Path $env:LOCALAPPDATA 'DRAT-Calcpad\Current'
}

$sourceRoot = [System.IO.Path]::GetFullPath($InstallationPath)
$projectRoot = [System.IO.Path]::GetFullPath($DestinationPath)
$projectPathRoot = [System.IO.Path]::GetPathRoot($projectRoot).TrimEnd('\', '/')
if ($projectRoot.TrimEnd('\', '/') -eq $projectPathRoot) {
    throw "Refusing to create a project directly in a filesystem root: $projectRoot"
}
$sourceManifestPath = Join-Path $sourceRoot 'manifest.json'
if (-not (Test-Path -LiteralPath $sourceManifestPath -PathType Leaf)) {
    throw "Installed DRAT manifest is missing: $sourceManifestPath"
}

if (Test-Path -LiteralPath $projectRoot) {
    if ((Get-ChildItem -LiteralPath $projectRoot -Force | Select-Object -First 1)) {
        throw "Project destination is not empty: $projectRoot"
    }
}
else {
    New-Item -ItemType Directory -Path $projectRoot -Force | Out-Null
}

$calculationsRoot = Join-Path $projectRoot 'Calculations'
$projectCoreRoot = Join-Path $projectRoot 'Core'
New-Item -ItemType Directory -Path $calculationsRoot -Force | Out-Null
New-Item -ItemType Directory -Path $projectCoreRoot -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $sourceRoot 'Core\DratCore.cpd') -Destination $projectCoreRoot

$templateText = [System.IO.File]::ReadAllText((Join-Path $sourceRoot 'Templates\EngineeringCalculationTemplate.cpd'))
if ($IncludeMaterials) {
    $materialsSource = Join-Path $sourceRoot 'Libraries\Materials'
    $materialsDestination = Join-Path $projectRoot 'Libraries\Materials'
    New-Item -ItemType Directory -Path $materialsDestination -Force | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $materialsSource -Force) {
        Copy-Item -LiteralPath $item.FullName -Destination $materialsDestination -Recurse
    }
    $templateNewline = if ($templateText.Contains("`r`n")) { "`r`n" } else { "`n" }
    $templateText = $templateText.Replace('#include ../Core/DratCore.cpd', "#include ../Core/DratCore.cpd${templateNewline}#include ../Libraries/Materials/EngineeringMaterials.cpd")
}

$utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)
$worksheetPath = Join-Path $calculationsRoot 'EngineeringCalculation.cpd'
[System.IO.File]::WriteAllText($worksheetPath, $templateText, $utf8WithoutBom)

$sourceManifest = Get-Content -LiteralPath $sourceManifestPath -Raw | ConvertFrom-Json
$projectManifest = [ordered]@{
    schema_version = 1
    product = 'DRAT CalcpadCE Portable Project'
    drat_version = $sourceManifest.version
    core_api = $sourceManifest.core_api
    materials_included = [bool]$IncludeMaterials
}
[System.IO.File]::WriteAllText((Join-Path $projectRoot 'drat-project.json'), ($projectManifest | ConvertTo-Json) + "`n", $utf8WithoutBom)

Write-Output "Created portable DRAT project: $projectRoot"
Write-Output "Starting worksheet: $worksheetPath"
