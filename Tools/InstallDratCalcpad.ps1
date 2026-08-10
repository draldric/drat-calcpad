[CmdletBinding()]
param(
    [string]$PackagePath,
    [string]$DestinationPath,
    [switch]$Force
)

if ([string]::IsNullOrWhiteSpace($PackagePath)) {
    $PackagePath = Split-Path -Parent $PSScriptRoot
}
if ([string]::IsNullOrWhiteSpace($DestinationPath)) {
    if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        throw 'LOCALAPPDATA is unavailable. Supply -DestinationPath explicitly.'
    }
    $DestinationPath = Join-Path $env:LOCALAPPDATA 'DRAT-Calcpad'
}

$packageRoot = [System.IO.Path]::GetFullPath($PackagePath)
$installRoot = [System.IO.Path]::GetFullPath($DestinationPath)
$installRootPathRoot = [System.IO.Path]::GetPathRoot($installRoot).TrimEnd('\', '/')
if ($installRoot.TrimEnd('\', '/') -eq $installRootPathRoot) {
    throw "Refusing to install directly into a filesystem root: $installRoot"
}
$installRootPrefix = $installRoot.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar

function Assert-InstallChildPath {
    param([string]$Path)

    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    if (-not $resolvedPath.StartsWith($script:installRootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to modify a path outside the installation root: $resolvedPath"
    }
}

function Read-DratManifest {
    param([string]$Root)

    $path = Join-Path $Root 'manifest.json'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "DRAT distribution manifest is missing: $path"
    }

    $manifest = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    if ($manifest.schema_version -ne 1 -or $manifest.product -ne 'DRAT CalcpadCE' -or $manifest.version -notmatch '^\d+\.\d+\.\d+$') {
        throw "DRAT distribution manifest is invalid: $path"
    }

    return $manifest
}

function Test-DratPackageIntegrity {
    param(
        [string]$Root,
        [object]$Manifest
    )

    foreach ($record in $Manifest.files) {
        $relativePath = $record.path.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        $filePath = [System.IO.Path]::GetFullPath((Join-Path $Root $relativePath))
        $rootPrefix = $Root.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
        if (-not $filePath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Manifest contains a path outside the package: $($record.path)"
        }
        if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
            throw "Distribution file is missing: $($record.path)"
        }

        $actualHash = (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -cne $record.sha256) {
            throw "Distribution hash mismatch: $($record.path)"
        }
    }
}

function Copy-DratTree {
    param(
        [string]$Source,
        [string]$Destination
    )

    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $Source -Force) {
        Copy-Item -LiteralPath $item.FullName -Destination $Destination -Recurse
    }
}

function Write-ManagedMarker {
    param(
        [string]$Root,
        [string]$Version
    )

    $marker = [ordered]@{ product = 'DRAT CalcpadCE'; version = $Version }
    $utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText((Join-Path $Root '.drat-managed-install.json'), ($marker | ConvertTo-Json) + "`n", $utf8WithoutBom)
}

function Assert-ManagedInstall {
    param([string]$Root)

    $markerPath = Join-Path $Root '.drat-managed-install.json'
    if (-not (Test-Path -LiteralPath $markerPath -PathType Leaf)) {
        throw "Refusing to replace an unmanaged directory: $Root"
    }
    $marker = Get-Content -LiteralPath $markerPath -Raw | ConvertFrom-Json
    if ($marker.product -ne 'DRAT CalcpadCE') {
        throw "Refusing to replace an unrecognized managed directory: $Root"
    }
}

$manifest = Read-DratManifest -Root $packageRoot
Test-DratPackageIntegrity -Root $packageRoot -Manifest $manifest

$versionsRoot = Join-Path $installRoot 'versions'
$versionRoot = Join-Path $versionsRoot $manifest.version
New-Item -ItemType Directory -Path $versionsRoot -Force | Out-Null

if (Test-Path -LiteralPath $versionRoot) {
    $installedValid = $true
    try {
        $installedManifest = Read-DratManifest -Root $versionRoot
        Test-DratPackageIntegrity -Root $versionRoot -Manifest $installedManifest
        $sourceManifestHash = (Get-FileHash -LiteralPath (Join-Path $packageRoot 'manifest.json') -Algorithm SHA256).Hash
        $installedManifestHash = (Get-FileHash -LiteralPath (Join-Path $versionRoot 'manifest.json') -Algorithm SHA256).Hash
        if ($sourceManifestHash -cne $installedManifestHash) {
            $installedValid = $false
        }
    }
    catch {
        $installedValid = $false
    }

    if (-not $installedValid) {
        if (-not $Force) {
            throw "Installed version $($manifest.version) differs from the package. Use -Force to replace the managed version."
        }
        Assert-ManagedInstall -Root $versionRoot
        Assert-InstallChildPath -Path $versionRoot
        Remove-Item -LiteralPath $versionRoot -Recurse -Force
    }
}

if (-not (Test-Path -LiteralPath $versionRoot)) {
    $versionStaging = Join-Path $installRoot ('.staging-version-' + [guid]::NewGuid().ToString('N'))
    try {
        Copy-DratTree -Source $packageRoot -Destination $versionStaging
        Write-ManagedMarker -Root $versionStaging -Version $manifest.version
        Move-Item -LiteralPath $versionStaging -Destination $versionRoot
    }
    finally {
        if (Test-Path -LiteralPath $versionStaging) {
            Assert-InstallChildPath -Path $versionStaging
            Remove-Item -LiteralPath $versionStaging -Recurse -Force
        }
    }
}

$currentRoot = Join-Path $installRoot 'Current'
$currentStaging = Join-Path $installRoot ('.staging-current-' + [guid]::NewGuid().ToString('N'))
$currentBackup = Join-Path $installRoot ('.previous-current-' + [guid]::NewGuid().ToString('N'))
try {
    Copy-DratTree -Source $versionRoot -Destination $currentStaging
    if (Test-Path -LiteralPath $currentRoot) {
        Assert-ManagedInstall -Root $currentRoot
        Move-Item -LiteralPath $currentRoot -Destination $currentBackup
    }
    Move-Item -LiteralPath $currentStaging -Destination $currentRoot
    if (Test-Path -LiteralPath $currentBackup) {
        Assert-ManagedInstall -Root $currentBackup
        Assert-InstallChildPath -Path $currentBackup
        Remove-Item -LiteralPath $currentBackup -Recurse -Force
    }
}
catch {
    if (-not (Test-Path -LiteralPath $currentRoot) -and (Test-Path -LiteralPath $currentBackup)) {
        Move-Item -LiteralPath $currentBackup -Destination $currentRoot
    }
    throw
}
finally {
    if (Test-Path -LiteralPath $currentStaging) {
        Assert-InstallChildPath -Path $currentStaging
        Remove-Item -LiteralPath $currentStaging -Recurse -Force
    }
}

Write-Output "Installed DRAT CalcpadCE $($manifest.version) to $versionRoot"
Write-Output "Current installation: $currentRoot"
Write-Output "Core include: #include $currentRoot\Core\DratCore.cpd"
Write-Output "Materials include: #include $currentRoot\Libraries\Materials\EngineeringMaterials.cpd"
