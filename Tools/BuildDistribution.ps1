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
$materialsPath = Join-Path $repositoryRoot 'Libraries\Materials\EngineeringMaterials.cpd'

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

$buildCorePath = Join-Path $repositoryRoot 'Tools\BuildCore.ps1'
& $buildCorePath -Check
if ($LASTEXITCODE -ne 0) {
    throw 'Core/DratCore.cpd must be current before building a distribution.'
}

$coreManifestText = [System.IO.File]::ReadAllText($coreManifestPath)
$materialsText = [System.IO.File]::ReadAllText($materialsPath)
$version = Get-RequiredMatch -Text $coreManifestText -Pattern '^#def\s+DRATCoreVersion\$\s*=\s*(?<value>\d+\.\d+\.\d+)\s*$' -Description 'DRAT Core version'
$coreApi = [int](Get-RequiredMatch -Text $coreManifestText -Pattern '^DRAT_CORE_API\s*=\s*(?<value>\d+)\s*$' -Description 'DRAT Core API')
$materialsRevision = Get-RequiredMatch -Text $materialsText -Pattern '^#def\s+EngineeringMaterialsLibraryRevision\$\s*=\s*(?<value>\d+\.\d+\.\d+)\s*$' -Description 'Engineering Materials revision'
$materialsMinimumCoreApi = [int](Get-RequiredMatch -Text $materialsText -Pattern '^#if\s+and\(DRAT_CORE_API\s+≥\s+(?<value>\d+);' -Description 'Engineering Materials minimum Core API')
$materialsMinimumDataWrapperApi = [int](Get-RequiredMatch -Text $materialsText -Pattern '^#if\s+and\(DRAT_DATA_WRAPPER_API\s+≥\s+(?<value>\d+);' -Description 'Engineering Materials minimum DataWrapper API')
$materialsMinimumPlottingApi = [int](Get-RequiredMatch -Text $materialsText -Pattern '^#if\s+and\(DRAT_PLOTTING_API\s+≥\s+(?<value>\d+);' -Description 'Engineering Materials minimum Plotting API')

$componentApis = [ordered]@{}
foreach ($match in [regex]::Matches($coreManifestText, '^(?<name>DRAT_[A-Z_]+_API)\s*=\s*(?<value>\d+)\s*$', [System.Text.RegularExpressions.RegexOptions]::Multiline)) {
    $componentApis[$match.Groups['name'].Value] = [int]$match.Groups['value'].Value
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

foreach ($fileName in @('README.md', 'CHANGELOG.md', 'LICENSE')) {
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
    schema_version = 1
    product = 'DRAT CalcpadCE'
    version = $version
    core_api = $coreApi
    component_apis = $componentApis
    libraries = @(
        [ordered]@{
            name = 'EngineeringMaterials'
            revision = $materialsRevision
            path = 'Libraries/Materials/EngineeringMaterials.cpd'
            minimum_core_api = $materialsMinimumCoreApi
            minimum_data_wrapper_api = $materialsMinimumDataWrapperApi
            minimum_plotting_api = $materialsMinimumPlottingApi
        }
    )
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
