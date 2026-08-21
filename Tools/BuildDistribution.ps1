[CmdletBinding()]
param(
    [string]$OutputDirectory,
    [switch]$Archive,
    [switch]$Force
)

$repositoryRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $repositoryRoot 'artifacts'
}

$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
$coreManifestPath = Join-Path $repositoryRoot 'Core\Src\CoreManifest.cpd'

$librarySpecifications = @(
    [ordered]@{ name = 'BeamAnalysis'; path = 'Libraries/Analysis/BeamAnalysis.cpd'; revision_definition = 'BeamAnalysisLibraryRevision$' }
    [ordered]@{ name = 'EngineeringMaterials'; path = 'Libraries/Materials/EngineeringMaterials.cpd'; revision_definition = 'EngineeringMaterialsLibraryRevision$' }
    [ordered]@{ name = 'ThermophysicalProperties'; path = 'Libraries/Thermophysical/ThermophysicalProperties.cpd'; revision_definition = 'ThermophysicalPropertiesLibraryRevision$' }
    [ordered]@{ name = 'AiscAngle'; path = 'Libraries/Steel/AiscAngleSections.cpd'; revision_definition = 'AiscAngleLibraryRevision$' }
    [ordered]@{ name = 'AiscChannel'; path = 'Libraries/Steel/AiscChannelSections.cpd'; revision_definition = 'AiscChannelLibraryRevision$' }
    [ordered]@{ name = 'AiscHss'; path = 'Libraries/Steel/AiscHssSections.cpd'; revision_definition = 'AiscHssLibraryRevision$' }
    [ordered]@{ name = 'StructuralSections'; path = 'Libraries/Steel/StructuralSections.cpd'; revision_definition = 'StructuralSectionsLibraryRevision$' }
)

function Get-RequiredMatch {
    param(
        [string]$Text,
        [string]$Pattern,
        [string]$Description
    )

    $match = [regex]::Match($Text, $Pattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)
    if (-not $match.Success) {
        throw "Could not read $Description."
    }

    return $match.Groups['value'].Value
}

function Copy-DistributionDirectory {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        throw "Distribution source directory is missing: $Source"
    }

    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    foreach ($file in Get-ChildItem -LiteralPath $Source -File -Recurse) {
        $relativePath = [System.IO.Path]::GetRelativePath($Source, $file.FullName)
        $destinationPath = Join-Path $Destination $relativePath
        New-Item -ItemType Directory -Path (Split-Path -Parent $destinationPath) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $destinationPath
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

function Get-LibraryManifestRecord {
    param([System.Collections.IDictionary]$Specification)

    $relativePath = $Specification.path.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
    $libraryPath = Join-Path $repositoryRoot $relativePath
    if (-not (Test-Path -LiteralPath $libraryPath -PathType Leaf)) {
        throw "Distribution library is missing: $($Specification.path)"
    }

    $libraryText = [System.IO.File]::ReadAllText($libraryPath)
    $revisionPattern = '^#def\s+' + [regex]::Escape($Specification.revision_definition) + '\s*=\s*(?<value>\d+\.\d+\.\d+)\s*$'
    $revision = Get-RequiredMatch -Text $libraryText -Pattern $revisionPattern -Description "$($Specification.name) revision"
    $nameDefinition = $Specification.revision_definition.Replace('Revision$', 'Name$')
    $displayNamePattern = '^#def\s+' + [regex]::Escape($nameDefinition) + '\s*=\s*(?<value>.+?)\s*$'
    $displayName = Get-RequiredMatch -Text $libraryText -Pattern $displayNamePattern -Description "$($Specification.name) display name"

    $guardEnd = $libraryText.IndexOf('#hide', [System.StringComparison]::Ordinal)
    if ($guardEnd -lt 0) {
        throw "Could not read $($Specification.name) compatibility guards."
    }

    $guardText = $libraryText.Substring(0, $guardEnd)
    $requirements = [ordered]@{}
    $optionalRequirements = [ordered]@{}
    $guardPattern = '^#if\s+and\((?<api>DRAT_[A-Z_]+_API)\s+≥\s+(?<minimum>\d+);\s*\k<api>\s+<\s+(?<maximum>\d+)\)\s*$'
    $allGuardMatches = [regex]::Matches($libraryText, $guardPattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)
    $guardMatches = @($allGuardMatches | Where-Object { $_.Index -lt $guardEnd })
    $guardLineCount = [regex]::Matches($guardText, '(?m)^#if\s+').Count
    if ($guardMatches.Count -ne $guardLineCount) {
        throw "$($Specification.name) has an unsupported leading compatibility guard."
    }
    foreach ($match in $guardMatches) {
        $apiName = $match.Groups['api'].Value
        if ($requirements.Contains($apiName)) {
            throw "$($Specification.name) repeats compatibility guard $apiName."
        }
        $requirements[$apiName] = [ordered]@{
            minimum = [int]$match.Groups['minimum'].Value
            maximum_exclusive = [int]$match.Groups['maximum'].Value
        }
    }
    foreach ($match in $allGuardMatches | Where-Object { $_.Index -ge $guardEnd }) {
        $apiName = $match.Groups['api'].Value
        if ($requirements.Contains($apiName) -or $optionalRequirements.Contains($apiName)) {
            throw "$($Specification.name) repeats optional compatibility guard $apiName."
        }
        $optionalRequirements[$apiName] = [ordered]@{
            minimum = [int]$match.Groups['minimum'].Value
            maximum_exclusive = [int]$match.Groups['maximum'].Value
        }
    }

    if ($requirements.Count -eq 0 -or -not $requirements.Contains('DRAT_CORE_API')) {
        throw "$($Specification.name) does not declare a leading Core compatibility guard."
    }

    return [ordered]@{
        name = $Specification.name
        display_name = $displayName
        revision = $revision
        path = $Specification.path
        requirements = $requirements
        optional_requirements = $optionalRequirements
    }
}

$distributionSourceRoots = @(
    (Join-Path $repositoryRoot 'Core'),
    (Join-Path $repositoryRoot 'Libraries'),
    (Join-Path $repositoryRoot 'Templates'),
    (Join-Path $repositoryRoot 'Examples'),
    (Join-Path $repositoryRoot 'docs'),
    (Join-Path $repositoryRoot 'Tools')
)
foreach ($sourceRoot in $distributionSourceRoots) {
    if (Test-PathOverlap -FirstPath $outputRoot -SecondPath $sourceRoot) {
        throw "Distribution output overlaps distribution source directory: $sourceRoot"
    }
}

$buildCorePath = Join-Path $repositoryRoot 'Tools\BuildCore.ps1'
& $buildCorePath -Check
if ($LASTEXITCODE -ne 0) {
    throw 'Core/DratCore.cpd must be current before building a distribution.'
}

$coreManifestText = [System.IO.File]::ReadAllText($coreManifestPath)
$version = Get-RequiredMatch -Text $coreManifestText -Pattern '^#def\s+DRATCoreVersion\$\s*=\s*(?<value>\d+\.\d+\.\d+)\s*$' -Description 'DRAT Core version'
$coreApi = [int](Get-RequiredMatch -Text $coreManifestText -Pattern '^DRAT_CORE_API\s*=\s*(?<value>\d+)\s*$' -Description 'DRAT Core API')

$componentApis = [ordered]@{}
foreach ($match in [regex]::Matches($coreManifestText, '^(?<name>DRAT_[A-Z_]+_API)\s*=\s*(?<value>\d+)\s*$', [System.Text.RegularExpressions.RegexOptions]::Multiline)) {
    $componentApis[$match.Groups['name'].Value] = [int]$match.Groups['value'].Value
}

$specifiedLibraryPaths = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($specification in $librarySpecifications) {
    if (-not $specifiedLibraryPaths.Add($specification.path)) {
        throw "Distribution library specification is duplicated: $($specification.path)"
    }
}
foreach ($libraryFile in Get-ChildItem -LiteralPath (Join-Path $repositoryRoot 'Libraries') -File -Recurse -Filter '*.cpd') {
    $libraryPath = [System.IO.Path]::GetRelativePath($repositoryRoot, $libraryFile.FullName).Replace('\', '/')
    if (-not $specifiedLibraryPaths.Contains($libraryPath)) {
        throw "Distribution library has no manifest specification: $libraryPath"
    }
}

$libraryRecords = @(
    foreach ($specification in $librarySpecifications) {
        Get-LibraryManifestRecord -Specification $specification
    }
)
foreach ($libraryRecord in $libraryRecords) {
    foreach ($requirementSet in @($libraryRecord.requirements, $libraryRecord.optional_requirements)) {
        foreach ($apiName in $requirementSet.Keys) {
            $requirement = $requirementSet[$apiName]
            if (-not $componentApis.Contains($apiName)) {
                throw "$($libraryRecord.name) requires API $apiName, which is absent from CoreManifest.cpd."
            }
            if ($componentApis[$apiName] -lt $requirement.minimum -or $componentApis[$apiName] -ge $requirement.maximum_exclusive) {
                throw "Packaged Core API $apiName=$($componentApis[$apiName]) is incompatible with $($libraryRecord.name)."
            }
        }
    }
}

$packageName = "DRAT-Calcpad-$version"
$packageRoot = Join-Path $outputRoot $packageName
if (Test-Path -LiteralPath $packageRoot) {
    if (-not $Force) {
        throw "Distribution already exists: $packageRoot. Use -Force to replace it."
    }

    $resolvedPackageRoot = [System.IO.Path]::GetFullPath($packageRoot)
    if ((Split-Path -Leaf $resolvedPackageRoot) -cne $packageName -or (Split-Path -Parent $resolvedPackageRoot) -cne $outputRoot) {
        throw "Refusing to replace an unexpected distribution path: $resolvedPackageRoot"
    }

    Remove-Item -LiteralPath $resolvedPackageRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null
Copy-DistributionDirectory -Source (Join-Path $repositoryRoot 'Core') -Destination (Join-Path $packageRoot 'Core')
$packagedSourceRoot = [System.IO.Path]::GetFullPath((Join-Path $packageRoot 'Core\Src'))
$packagePrefix = [System.IO.Path]::GetFullPath($packageRoot).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
if (-not $packagedSourceRoot.StartsWith($packagePrefix, [System.StringComparison]::OrdinalIgnoreCase) -or (Split-Path -Leaf $packagedSourceRoot) -cne 'Src') {
    throw "Refusing to remove an unexpected packaged-source path: $packagedSourceRoot"
}
Remove-Item -LiteralPath $packagedSourceRoot -Recurse -Force
Copy-DistributionDirectory -Source (Join-Path $repositoryRoot 'Libraries') -Destination (Join-Path $packageRoot 'Libraries')
Copy-DistributionDirectory -Source (Join-Path $repositoryRoot 'Templates') -Destination (Join-Path $packageRoot 'Templates')
Copy-DistributionDirectory -Source (Join-Path $repositoryRoot 'Examples') -Destination (Join-Path $packageRoot 'Examples')
Copy-DistributionDirectory -Source (Join-Path $repositoryRoot 'docs') -Destination (Join-Path $packageRoot 'docs')

$packageTools = Join-Path $packageRoot 'Tools'
New-Item -ItemType Directory -Path $packageTools -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $repositoryRoot 'Tools\InstallDratCalcpad.ps1') -Destination $packageTools
Copy-Item -LiteralPath (Join-Path $repositoryRoot 'Tools\NewDratProject.ps1') -Destination $packageTools

foreach ($fileName in @('README.md', 'CHANGELOG.md', 'LICENSE', 'THIRD-PARTY-NOTICES.md')) {
    Copy-Item -LiteralPath (Join-Path $repositoryRoot $fileName) -Destination $packageRoot
}

$fileRecords = @(
    foreach ($file in Get-ChildItem -LiteralPath $packageRoot -File -Recurse | Sort-Object FullName) {
        $relativePath = [System.IO.Path]::GetRelativePath($packageRoot, $file.FullName).Replace('\', '/')
        [ordered]@{
            path = $relativePath
            sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
)

$manifest = [ordered]@{
    schema_version = 2
    product = 'DRAT CalcpadCE'
    version = $version
    core_api = $coreApi
    component_apis = $componentApis
    libraries = $libraryRecords
    files = $fileRecords
}

$utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)
$manifestPath = Join-Path $packageRoot 'manifest.json'
[System.IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 8) + "`n", $utf8WithoutBom)

if ($Archive) {
    $archivePath = Join-Path $outputRoot "$packageName.zip"
    if (Test-Path -LiteralPath $archivePath) {
        if (-not $Force) {
            throw "Distribution archive already exists: $archivePath. Use -Force to replace it."
        }
        Remove-Item -LiteralPath $archivePath -Force
    }

    Compress-Archive -LiteralPath $packageRoot -DestinationPath $archivePath -CompressionLevel Optimal
    Write-Output "Created distribution archive: $archivePath"
}

Write-Output "Created distribution directory: $packageRoot"
