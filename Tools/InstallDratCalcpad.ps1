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
    if ($manifest.schema_version -ne 2 -or $manifest.product -ne 'DRAT CalcpadCE' -or $manifest.version -notmatch '^\d+\.\d+\.\d+$' -or $null -eq $manifest.component_apis -or $null -eq $manifest.libraries -or $null -eq $manifest.files) {
        throw "DRAT distribution manifest is invalid: $path"
    }

    return $manifest
}

function Test-DratPackageIntegrity {
    param(
        [string]$Root,
        [object]$Manifest
    )

    $resolvedRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
    $rootPrefix = $resolvedRoot + [System.IO.Path]::DirectorySeparatorChar
    $manifestPaths = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)

    foreach ($record in $Manifest.files) {
        if ($record.path -isnot [string] -or [string]::IsNullOrWhiteSpace($record.path) -or $record.path.Contains('\') -or $record.path.StartsWith('/') -or $record.path -match '(^|/)\.{1,2}(/|$)|//' -or $record.path -in @('manifest.json', '.drat-managed-install.json')) {
            throw "Manifest contains an invalid package path: $($record.path)"
        }
        if ($record.sha256 -isnot [string] -or $record.sha256 -cnotmatch '^[0-9a-f]{64}$') {
            throw "Manifest contains an invalid SHA-256 hash: $($record.path)"
        }
        if (-not $manifestPaths.Add($record.path)) {
            throw "Manifest contains a duplicate package path: $($record.path)"
        }

        $relativePath = $record.path.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        $filePath = [System.IO.Path]::GetFullPath((Join-Path $resolvedRoot $relativePath))
        if (-not $filePath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Manifest contains a path outside the package: $($record.path)"
        }
        $canonicalPath = [System.IO.Path]::GetRelativePath($resolvedRoot, $filePath).Replace('\', '/')
        if ($canonicalPath -cne $record.path) {
            throw "Manifest contains a noncanonical package path: $($record.path)"
        }
        if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
            throw "Distribution file is missing: $($record.path)"
        }

        $actualHash = (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -cne $record.sha256) {
            throw "Distribution hash mismatch: $($record.path)"
        }
    }

    foreach ($file in Get-ChildItem -LiteralPath $resolvedRoot -File -Recurse -Force) {
        $relativePath = [System.IO.Path]::GetRelativePath($resolvedRoot, $file.FullName).Replace('\', '/')
        if ($relativePath -in @('manifest.json', '.drat-managed-install.json')) {
            continue
        }
        if (-not $manifestPaths.Contains($relativePath)) {
            throw "Distribution contains a file that is not listed in the manifest: $relativePath"
        }
    }
}

function Get-DeclaredApis {
    param([string]$Text)

    $apis = [ordered]@{}
    foreach ($match in [regex]::Matches($Text, '(?m)^(?<name>DRAT_[A-Z_]+_API)\s*=\s*(?<value>\d+)\s*$')) {
        $apiName = $match.Groups['name'].Value
        if ($apis.Contains($apiName)) {
            throw "Packaged Core repeats API declaration: $apiName"
        }
        $apis[$apiName] = [int]$match.Groups['value'].Value
    }

    return $apis
}

function Get-RequirementMap {
    param([object]$Requirements)

    $map = [ordered]@{}
    if ($null -eq $Requirements) {
        return $map
    }

    foreach ($property in $Requirements.PSObject.Properties) {
        $range = $property.Value
        if ($property.Name -notmatch '^DRAT_[A-Z_]+_API$' -or $null -eq $range.minimum -or $null -eq $range.maximum_exclusive -or [int]$range.minimum -ge [int]$range.maximum_exclusive) {
            throw "Manifest contains an invalid API requirement: $($property.Name)"
        }
        $map[$property.Name] = [ordered]@{
            minimum = [int]$range.minimum
            maximum_exclusive = [int]$range.maximum_exclusive
        }
    }

    return $map
}

function Get-LibraryDeclarations {
    param([string]$Text)

    $revisionMatches = [regex]::Matches($Text, '(?m)^#def\s+(?<name>\w+)LibraryRevision\$\s*=\s*(?<revision>\d+\.\d+\.\d+)\s*$')
    if ($revisionMatches.Count -ne 1) {
        throw 'Packaged library must declare exactly one numeric LibraryRevision$.'
    }
    $libraryName = $revisionMatches[0].Groups['name'].Value
    $displayNamePattern = '(?m)^#def\s+' + [regex]::Escape($libraryName) + 'LibraryName\$\s*=\s*(?<display_name>.+?)\s*$'
    $displayNameMatch = [regex]::Match($Text, $displayNamePattern)
    if (-not $displayNameMatch.Success) {
        throw "Packaged library does not declare $($libraryName)LibraryName$."
    }

    $guardEnd = $Text.IndexOf('#hide', [System.StringComparison]::Ordinal)
    if ($guardEnd -lt 0) {
        throw "Packaged library $libraryName has no leading compatibility block."
    }
    $guardPattern = '^#if\s+and\((?<api>DRAT_[A-Z_]+_API)\s+≥\s+(?<minimum>\d+);\s*\k<api>\s+<\s+(?<maximum>\d+)\)\s*$'
    $guardMatches = [regex]::Matches($Text, $guardPattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)
    $leadingGuardCount = [regex]::Matches($Text.Substring(0, $guardEnd), '(?m)^#if\s+').Count
    $required = [ordered]@{}
    $optional = [ordered]@{}
    foreach ($match in $guardMatches) {
        $target = if ($match.Index -lt $guardEnd) { $required } else { $optional }
        $apiName = $match.Groups['api'].Value
        if ($required.Contains($apiName) -or $optional.Contains($apiName)) {
            throw "Packaged library $libraryName repeats API guard $apiName."
        }
        $target[$apiName] = [ordered]@{
            minimum = [int]$match.Groups['minimum'].Value
            maximum_exclusive = [int]$match.Groups['maximum'].Value
        }
    }
    if ($required.Count -ne $leadingGuardCount -or -not $required.Contains('DRAT_CORE_API')) {
        throw "Packaged library $libraryName has unsupported leading compatibility guards."
    }

    return [ordered]@{
        name = $libraryName
        display_name = $displayNameMatch.Groups['display_name'].Value
        revision = $revisionMatches[0].Groups['revision'].Value
        requirements = $required
        optional_requirements = $optional
    }
}

function Assert-RequirementMapsEqual {
    param(
        [System.Collections.IDictionary]$Expected,
        [System.Collections.IDictionary]$Actual,
        [string]$Description
    )

    if ($Expected.Count -ne $Actual.Count) {
        throw "$Description count does not match the packaged declaration."
    }
    foreach ($apiName in $Expected.Keys) {
        if (-not $Actual.Contains($apiName)) {
            throw "$Description omits packaged declaration $apiName."
        }
        if ($Expected[$apiName].minimum -ne $Actual[$apiName].minimum -or $Expected[$apiName].maximum_exclusive -ne $Actual[$apiName].maximum_exclusive) {
            throw "$Description range does not match packaged declaration $apiName."
        }
    }
}

function Assert-DratManifestMetadata {
    param(
        [string]$Root,
        [object]$Manifest
    )

    $corePath = Join-Path $Root 'Core\DratCore.cpd'
    if (-not (Test-Path -LiteralPath $corePath -PathType Leaf)) {
        throw 'Packaged Core declaration file is missing.'
    }
    $coreText = [System.IO.File]::ReadAllText($corePath)
    $versionMatch = [regex]::Match($coreText, '(?m)^#def\s+DRATCoreVersion\$\s*=\s*(?<version>\d+\.\d+\.\d+)\s*$')
    if (-not $versionMatch.Success -or $versionMatch.Groups['version'].Value -cne $Manifest.version) {
        throw 'Manifest version does not match packaged DRATCoreVersion$.'
    }

    $declaredApis = Get-DeclaredApis -Text $coreText
    $manifestApis = [ordered]@{}
    foreach ($property in $Manifest.component_apis.PSObject.Properties) {
        if ($property.Name -notmatch '^DRAT_[A-Z_]+_API$' -or $manifestApis.Contains($property.Name)) {
            throw "Manifest contains an invalid component API: $($property.Name)"
        }
        $manifestApis[$property.Name] = [int]$property.Value
    }
    if ($declaredApis.Count -ne $manifestApis.Count) {
        throw 'Manifest component API inventory does not match packaged Core declarations.'
    }
    foreach ($apiName in $declaredApis.Keys) {
        if (-not $manifestApis.Contains($apiName) -or $manifestApis[$apiName] -ne $declaredApis[$apiName]) {
            throw "Manifest component API does not match packaged Core declaration: $apiName"
        }
    }
    if (-not $declaredApis.Contains('DRAT_CORE_API') -or [int]$Manifest.core_api -ne $declaredApis['DRAT_CORE_API']) {
        throw 'Manifest core_api does not match packaged DRAT_CORE_API.'
    }

    $libraryFiles = @(Get-ChildItem -LiteralPath (Join-Path $Root 'Libraries') -File -Recurse -Filter '*.cpd')
    if ($Manifest.libraries.Count -ne $libraryFiles.Count) {
        throw 'Manifest library inventory does not match packaged library files.'
    }
    $actualLibraryPaths = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($libraryFile in $libraryFiles) {
        $actualPath = [System.IO.Path]::GetRelativePath($Root, $libraryFile.FullName).Replace('\', '/')
        $null = $actualLibraryPaths.Add($actualPath)
    }
    $manifestLibraryPaths = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($libraryRecord in $Manifest.libraries) {
        if ($libraryRecord.path -isnot [string] -or -not $manifestLibraryPaths.Add($libraryRecord.path) -or -not $actualLibraryPaths.Contains($libraryRecord.path)) {
            throw "Manifest contains an invalid or duplicate library path: $($libraryRecord.path)"
        }
        $relativePath = $libraryRecord.path.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        $libraryPath = [System.IO.Path]::GetFullPath((Join-Path $Root $relativePath))
        $librariesPrefix = [System.IO.Path]::GetFullPath((Join-Path $Root 'Libraries')).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
        if (-not $libraryPath.StartsWith($librariesPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $libraryPath -PathType Leaf)) {
            throw "Manifest library path is outside the packaged Libraries directory: $($libraryRecord.path)"
        }

        $declarations = Get-LibraryDeclarations -Text ([System.IO.File]::ReadAllText($libraryPath))
        if ($libraryRecord.name -cne $declarations.name -or $libraryRecord.display_name -cne $declarations.display_name -or $libraryRecord.revision -cne $declarations.revision) {
            throw "Manifest library identity does not match packaged declarations: $($libraryRecord.path)"
        }
        $required = Get-RequirementMap -Requirements $libraryRecord.requirements
        $optional = Get-RequirementMap -Requirements $libraryRecord.optional_requirements
        Assert-RequirementMapsEqual -Expected $declarations.requirements -Actual $required -Description "$($libraryRecord.name) required API metadata"
        Assert-RequirementMapsEqual -Expected $declarations.optional_requirements -Actual $optional -Description "$($libraryRecord.name) optional API metadata"
    }
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
            $target = $null
            try {
                $target = $item.ResolveLinkTarget($true)
            }
            catch {
                if (-not [string]::IsNullOrWhiteSpace($item.LinkType)) {
                    throw "Could not resolve linked path: $($item.FullName)"
                }
            }
            if ($null -ne $target) {
                $resolvedPath = $target.FullName
            }
            elseif (-not [string]::IsNullOrWhiteSpace($item.LinkType)) {
                throw "Could not resolve linked path: $($item.FullName)"
            }
            else {
                # Cloud-storage providers can mark ordinary directories as reparse points without making them links.
                $resolvedPath = $item.FullName
            }
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

if (Test-PathOverlap -FirstPath $packageRoot -SecondPath $installRoot) {
    throw 'Package and installation paths must not be equal, ancestors, or descendants of one another.'
}

$manifest = Read-DratManifest -Root $packageRoot
Test-DratPackageIntegrity -Root $packageRoot -Manifest $manifest
Assert-DratManifestMetadata -Root $packageRoot -Manifest $manifest

$versionsRoot = Join-Path $installRoot 'versions'
$versionRoot = Join-Path $versionsRoot $manifest.version
New-Item -ItemType Directory -Path $versionsRoot -Force | Out-Null

if (Test-Path -LiteralPath $versionRoot) {
    $installedValid = $true
    try {
        $installedManifest = Read-DratManifest -Root $versionRoot
        Test-DratPackageIntegrity -Root $versionRoot -Manifest $installedManifest
        Assert-DratManifestMetadata -Root $versionRoot -Manifest $installedManifest
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
Write-Output "Thermophysical include: #include $currentRoot\Libraries\Thermophysical\ThermophysicalProperties.cpd"
