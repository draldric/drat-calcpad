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

function Get-PhysicalPath {
    param([string]$Path)

    # Resolve aliases in the existing prefix, then preserve any not-yet-created destination suffix.
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $pathRoot = [System.IO.Path]::GetPathRoot($fullPath)
    $segments = $fullPath.Substring($pathRoot.Length).Split(
        [char[]]@([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar),
        [System.StringSplitOptions]::RemoveEmptyEntries
    )
    $resolvedPath = $pathRoot
    for ($index = 0; $index -lt $segments.Count; $index++) {
        $candidate = Join-Path $resolvedPath $segments[$index]
        $item = Get-Item -LiteralPath $candidate -Force -ErrorAction SilentlyContinue
        if ($null -eq $item) {
            for ($remaining = $index; $remaining -lt $segments.Count; $remaining++) {
                $resolvedPath = Join-Path $resolvedPath $segments[$remaining]
            }
            break
        }

        if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            $target = $item.ResolveLinkTarget($true)
            if ($null -eq $target) {
                throw "Could not resolve reparse-point path: $($item.FullName)"
            }
            $resolvedPath = $target.FullName
        }
        else {
            $resolvedPath = $item.FullName
        }
    }

    return [System.IO.Path]::GetFullPath($resolvedPath).TrimEnd('\', '/')
}

function Test-PathOverlap {
    param(
        [string]$FirstPath,
        [string]$SecondPath
    )

    $first = Get-PhysicalPath -Path $FirstPath
    $second = Get-PhysicalPath -Path $SecondPath
    if ($first.Equals($second, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }

    $firstPrefix = $first + [System.IO.Path]::DirectorySeparatorChar
    $secondPrefix = $second + [System.IO.Path]::DirectorySeparatorChar
    return $first.StartsWith($secondPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or $second.StartsWith($firstPrefix, [System.StringComparison]::OrdinalIgnoreCase)
}

if (Test-PathOverlap -FirstPath $sourceRoot -SecondPath $projectRoot) {
    throw 'Installation and project paths must not be equal, ancestors, or descendants of one another.'
}

$sourceManifestPath = Join-Path $sourceRoot 'manifest.json'
if (-not (Test-Path -LiteralPath $sourceManifestPath -PathType Leaf)) {
    throw "Installed DRAT manifest is missing: $sourceManifestPath"
}
$sourceManifest = Get-Content -LiteralPath $sourceManifestPath -Raw | ConvertFrom-Json
if ($sourceManifest.schema_version -ne 2 -or $sourceManifest.product -ne 'DRAT CalcpadCE' -or $sourceManifest.version -notmatch '^\d+\.\d+\.\d+$' -or $null -eq $sourceManifest.files) {
    throw "Installed DRAT manifest is invalid: $sourceManifestPath"
}

function Assert-InstalledFileIntegrity {
    param([string]$RelativePath)

    $manifestPath = $RelativePath.Replace('\', '/')
    $records = @($sourceManifest.files | Where-Object { $_.path -ceq $manifestPath })
    if ($records.Count -ne 1) {
        throw "Installed DRAT manifest does not contain exactly one record for: $manifestPath"
    }

    $filePath = Join-Path $sourceRoot $RelativePath
    if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
        throw "Installed DRAT file is missing: $manifestPath"
    }

    $actualHash = (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -cne $records[0].sha256) {
        throw "Installed DRAT hash mismatch: $manifestPath"
    }
}

Assert-InstalledFileIntegrity -RelativePath 'Core\DratCore.cpd'
Assert-InstalledFileIntegrity -RelativePath 'Templates\EngineeringCalculationTemplate.cpd'
$materialsFiles = @()
if ($IncludeMaterials) {
    Assert-InstalledFileIntegrity -RelativePath 'Libraries\Materials\EngineeringMaterials.cpd'
    $materialsSource = Join-Path $sourceRoot 'Libraries\Materials'
    if (-not (Test-Path -LiteralPath $materialsSource -PathType Container)) {
        throw "Installed DRAT Materials library directory is missing: $materialsSource"
    }
    $materialsFiles = @(Get-ChildItem -LiteralPath $materialsSource -File -Recurse -Force -ErrorAction Stop)
    foreach ($file in $materialsFiles) {
        $relativeSourcePath = [System.IO.Path]::GetRelativePath($sourceRoot, $file.FullName)
        Assert-InstalledFileIntegrity -RelativePath $relativeSourcePath
    }
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
    $materialsDestination = Join-Path $projectRoot 'Libraries\Materials'
    New-Item -ItemType Directory -Path $materialsDestination -Force | Out-Null
    foreach ($file in $materialsFiles) {
        $relativeMaterialsPath = [System.IO.Path]::GetRelativePath($materialsSource, $file.FullName)
        $destinationFile = Join-Path $materialsDestination $relativeMaterialsPath
        New-Item -ItemType Directory -Path (Split-Path -Parent $destinationFile) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $destinationFile
    }
    if (-not $templateText.Contains('#include ../Core/DratCore.cpd')) {
        throw 'Engineering calculation template does not contain the expected Core include.'
    }
    $templateNewline = if ($templateText.Contains("`r`n")) { "`r`n" } else { "`n" }
    $templateText = $templateText.Replace('#include ../Core/DratCore.cpd', "#include ../Core/DratCore.cpd${templateNewline}#include ../Libraries/Materials/EngineeringMaterials.cpd")
}

$utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)
$worksheetPath = Join-Path $calculationsRoot 'EngineeringCalculation.cpd'
[System.IO.File]::WriteAllText($worksheetPath, $templateText, $utf8WithoutBom)

$projectFileRecords = @(
    foreach ($file in Get-ChildItem -LiteralPath $projectRoot -File -Recurse | Sort-Object FullName) {
        [ordered]@{
            path = [System.IO.Path]::GetRelativePath($projectRoot, $file.FullName).Replace('\', '/')
            sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
)

$projectManifest = [ordered]@{
    schema_version = 1
    product = 'DRAT CalcpadCE Portable Project'
    drat_version = $sourceManifest.version
    core_api = $sourceManifest.core_api
    materials_included = [bool]$IncludeMaterials
    libraries = if ($IncludeMaterials) { @('EngineeringMaterials') } else { @() }
    files = $projectFileRecords
}
[System.IO.File]::WriteAllText((Join-Path $projectRoot 'drat-project.json'), ($projectManifest | ConvertTo-Json) + "`n", $utf8WithoutBom)

Write-Output "Created portable DRAT project: $projectRoot"
Write-Output "Starting worksheet: $worksheetPath"
