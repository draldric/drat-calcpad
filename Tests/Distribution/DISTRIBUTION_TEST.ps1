[CmdletBinding()]
param(
    [string]$CalcPadCli,
    [switch]$KeepOutput
)

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('drat-distribution-test-' + [guid]::NewGuid().ToString('N'))
$outputRoot = Join-Path $testRoot 'output'
$installRoot = Join-Path $testRoot 'clean install'
$generatedProjectsRoot = Join-Path $testRoot 'generated projects'
$movedProjectsRoot = Join-Path $testRoot 'moved portable projects'
$successMarker = '[PASS] Distribution archive, declaration-backed metadata and hashes, overlap rejection, retained update, stable Current path, and moved current-version projects.'

function Assert-DistributionTest {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Assert-ScriptThrows {
    param(
        [scriptblock]$Action,
        [string]$ExpectedMessage,
        [string]$FailureMessage
    )

    $thrownMessage = $null
    try {
        & $Action
    }
    catch {
        $thrownMessage = $_.Exception.Message
    }

    Assert-DistributionTest -Condition (-not [string]::IsNullOrWhiteSpace($thrownMessage)) -Message $FailureMessage
    Assert-DistributionTest -Condition ($thrownMessage.Contains($ExpectedMessage, [System.StringComparison]::Ordinal)) -Message "$FailureMessage Received: $thrownMessage"
}

function Get-DeclaredApiMap {
    param([string]$Text)

    $map = [ordered]@{}
    foreach ($match in [regex]::Matches($Text, '(?m)^(?<api>DRAT_[A-Z_]+_API)\s*=\s*(?<value>\d+)\s*$')) {
        Assert-DistributionTest -Condition (-not $map.Contains($match.Groups['api'].Value)) -Message "Packaged Core repeats API declaration: $($match.Groups['api'].Value)"
        $map[$match.Groups['api'].Value] = [int]$match.Groups['value'].Value
    }
    return $map
}

function Get-RangeMapFromObject {
    param([object]$Value)

    $map = [ordered]@{}
    if ($null -eq $Value) {
        return $map
    }
    foreach ($property in $Value.PSObject.Properties) {
        $map[$property.Name] = "$([int]$property.Value.minimum):$([int]$property.Value.maximum_exclusive)"
    }
    return $map
}

function Assert-MapEqual {
    param(
        [System.Collections.IDictionary]$Expected,
        [System.Collections.IDictionary]$Actual,
        [string]$Description
    )

    Assert-DistributionTest -Condition ($Expected.Count -eq $Actual.Count) -Message "$Description count differs."
    foreach ($key in $Expected.Keys) {
        Assert-DistributionTest -Condition ($Actual.Contains($key) -and $Actual[$key] -ceq $Expected[$key]) -Message "$Description differs for $key."
    }
}

function Assert-DistributionMetadata {
    param(
        [string]$Root,
        [object]$Manifest
    )

    Assert-DistributionTest -Condition ($Manifest.schema_version -eq 2 -and $Manifest.product -eq 'DRAT CalcpadCE') -Message 'Distribution manifest identity is invalid.'
    $coreText = [System.IO.File]::ReadAllText((Join-Path $Root 'Core\DratCore.cpd'))
    $versionMatch = [regex]::Match($coreText, '(?m)^#def\s+DRATCoreVersion\$\s*=\s*(?<version>\d+\.\d+\.\d+)\s*$')
    Assert-DistributionTest -Condition ($versionMatch.Success -and $versionMatch.Groups['version'].Value -ceq $Manifest.version) -Message 'Manifest version differs from packaged Core.'

    $declaredApis = Get-DeclaredApiMap -Text $coreText
    $manifestApis = [ordered]@{}
    foreach ($property in $Manifest.component_apis.PSObject.Properties) {
        $manifestApis[$property.Name] = [int]$property.Value
    }
    Assert-MapEqual -Expected $declaredApis -Actual $manifestApis -Description 'Component API metadata'
    Assert-DistributionTest -Condition ($Manifest.core_api -eq $declaredApis['DRAT_CORE_API']) -Message 'Manifest Core API differs from packaged Core.'

    $libraryFiles = @(Get-ChildItem -LiteralPath (Join-Path $Root 'Libraries') -File -Recurse -Filter '*.cpd')
    Assert-DistributionTest -Condition ($Manifest.libraries.Count -eq $libraryFiles.Count) -Message 'Manifest library inventory differs from packaged libraries.'
    foreach ($libraryFile in $libraryFiles) {
        $libraryPath = [System.IO.Path]::GetRelativePath($Root, $libraryFile.FullName).Replace('\', '/')
        $records = @($Manifest.libraries | Where-Object { $_.path -ceq $libraryPath })
        Assert-DistributionTest -Condition ($records.Count -eq 1) -Message "Packaged library has no unique metadata record: $libraryPath"
        $record = $records[0]
        $libraryText = [System.IO.File]::ReadAllText($libraryFile.FullName)
        $revisionMatches = [regex]::Matches($libraryText, '(?m)^#def\s+(?<name>\w+)LibraryRevision\$\s*=\s*(?<revision>\d+\.\d+\.\d+)\s*$')
        Assert-DistributionTest -Condition ($revisionMatches.Count -eq 1) -Message "Packaged library revision declaration is invalid: $libraryPath"
        $libraryName = $revisionMatches[0].Groups['name'].Value
        $displayNamePattern = '(?m)^#def\s+' + [regex]::Escape($libraryName) + 'LibraryName\$\s*=\s*(?<display_name>.+?)\s*$'
        $displayNameMatch = [regex]::Match($libraryText, $displayNamePattern)
        Assert-DistributionTest -Condition ($displayNameMatch.Success) -Message "Packaged library display-name declaration is missing: $libraryPath"
        Assert-DistributionTest -Condition ($record.name -ceq $libraryName -and $record.display_name -ceq $displayNameMatch.Groups['display_name'].Value -and $record.revision -ceq $revisionMatches[0].Groups['revision'].Value) -Message "Library identity metadata differs from packaged declarations: $libraryPath"

        $guardEnd = $libraryText.IndexOf('#hide', [System.StringComparison]::Ordinal)
        Assert-DistributionTest -Condition ($guardEnd -ge 0) -Message "Packaged library has no leading guard block: $libraryPath"
        $guardPattern = '^#if\s+and\((?<api>DRAT_[A-Z_]+_API)\s+≥\s+(?<minimum>\d+);\s*\k<api>\s+<\s+(?<maximum>\d+)\)\s*$'
        $requiredDeclarations = [ordered]@{}
        $optionalDeclarations = [ordered]@{}
        foreach ($match in [regex]::Matches($libraryText, $guardPattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)) {
            $target = if ($match.Index -lt $guardEnd) { $requiredDeclarations } else { $optionalDeclarations }
            $target[$match.Groups['api'].Value] = "$([int]$match.Groups['minimum'].Value):$([int]$match.Groups['maximum'].Value)"
        }
        Assert-MapEqual -Expected $requiredDeclarations -Actual (Get-RangeMapFromObject -Value $record.requirements) -Description "$libraryPath required API metadata"
        Assert-MapEqual -Expected $optionalDeclarations -Actual (Get-RangeMapFromObject -Value $record.optional_requirements) -Description "$libraryPath optional API metadata"
        foreach ($rangeMap in @($requiredDeclarations, $optionalDeclarations)) {
            foreach ($apiName in $rangeMap.Keys) {
                $bounds = @($rangeMap[$apiName].Split(':') | ForEach-Object { [int]$_ })
                Assert-DistributionTest -Condition ($declaredApis.Contains($apiName) -and $declaredApis[$apiName] -ge $bounds[0] -and $declaredApis[$apiName] -lt $bounds[1]) -Message "Packaged Core does not satisfy $libraryPath guard $apiName."
            }
        }
    }
}

function Get-RelativeFileRecords {
    param(
        [string]$Root,
        [string[]]$Exclude = @()
    )

    $excludedPaths = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($path in $Exclude) {
        $null = $excludedPaths.Add($path)
    }

    return @(
        foreach ($file in Get-ChildItem -LiteralPath $Root -File -Recurse -Force | Sort-Object FullName) {
            $relativePath = [System.IO.Path]::GetRelativePath($Root, $file.FullName).Replace('\', '/')
            if (-not $excludedPaths.Contains($relativePath)) {
                [ordered]@{
                    path = $relativePath
                    sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
                }
            }
        }
    )
}

function Assert-ManifestFileRecords {
    param(
        [string]$Root,
        [object[]]$Records,
        [string[]]$Exclude = @()
    )

    $actualRecords = @(Get-RelativeFileRecords -Root $Root -Exclude $Exclude)
    Assert-DistributionTest -Condition ($Records.Count -eq $actualRecords.Count) -Message "Manifest file count does not match packaged files under $Root."

    $recordPaths = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $previousPath = $null
    foreach ($record in $Records) {
        Assert-DistributionTest -Condition ($record.path -is [string] -and $record.path -cmatch '^[^\\/](?:.*[^\\/])?$') -Message "Manifest path is invalid: $($record.path)"
        Assert-DistributionTest -Condition (-not $record.path.Contains('\') -and -not $record.path.Contains('../')) -Message "Manifest path is not normalized: $($record.path)"
        Assert-DistributionTest -Condition ($record.sha256 -is [string] -and $record.sha256 -cmatch '^[0-9a-f]{64}$') -Message "Manifest SHA-256 is invalid: $($record.path)"
        Assert-DistributionTest -Condition ($recordPaths.Add($record.path)) -Message "Manifest path is duplicated: $($record.path)"
        if ($null -ne $previousPath) {
            Assert-DistributionTest -Condition ([string]::Compare($previousPath, $record.path, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) -Message 'Manifest file records are not in deterministic path order.'
        }
        $previousPath = $record.path

        $actualRecord = @($actualRecords | Where-Object { $_.path -ceq $record.path })
        Assert-DistributionTest -Condition ($actualRecord.Count -eq 1) -Message "Manifest file is missing or path casing differs: $($record.path)"
        Assert-DistributionTest -Condition ($actualRecord[0].sha256 -ceq $record.sha256) -Message "Manifest hash mismatch: $($record.path)"
    }
}

function Get-PriorVersion {
    param([string]$Version)

    $parts = @($Version.Split('.') | ForEach-Object { [int]$_ })
    if ($parts[2] -gt 0) {
        return "$($parts[0]).$($parts[1]).$($parts[2] - 1)"
    }
    if ($parts[1] -gt 0) {
        return "$($parts[0]).$($parts[1] - 1).0"
    }
    if ($parts[0] -gt 0) {
        return "$($parts[0] - 1).0.0"
    }

    throw "Cannot synthesize a prior version before $Version."
}

function Get-TreeFingerprint {
    param([string]$Root)

    return @(
        Get-RelativeFileRecords -Root $Root | ForEach-Object { "$($_.path)|$($_.sha256)" }
    ) -join "`n"
}

function Assert-PortableProject {
    param(
        [string]$Root,
        [bool]$ExpectMaterials,
        [string]$ExpectedVersion,
        [string[]]$ForbiddenPaths
    )

    $projectManifestPath = Join-Path $Root 'drat-project.json'
    Assert-DistributionTest -Condition (Test-Path -LiteralPath $projectManifestPath -PathType Leaf) -Message "Portable-project manifest is missing: $Root"
    $projectManifest = Get-Content -LiteralPath $projectManifestPath -Raw | ConvertFrom-Json
    Assert-DistributionTest -Condition ($projectManifest.schema_version -eq 1 -and $projectManifest.product -eq 'DRAT CalcpadCE Portable Project') -Message "Portable-project manifest is invalid: $Root"
    Assert-DistributionTest -Condition ($projectManifest.drat_version -eq $ExpectedVersion) -Message "Portable project changed its source DRAT version: $Root"
    Assert-DistributionTest -Condition ([bool]$projectManifest.materials_included -eq $ExpectMaterials) -Message "Portable-project Materials flag is invalid: $Root"
    Assert-ManifestFileRecords -Root $Root -Records @($projectManifest.files) -Exclude @('drat-project.json')

    $worksheetPath = Join-Path $Root 'Calculations\EngineeringCalculation.cpd'
    Assert-DistributionTest -Condition (Test-Path -LiteralPath $worksheetPath -PathType Leaf) -Message "Portable worksheet is missing: $Root"
    Assert-DistributionTest -Condition (Test-Path -LiteralPath (Join-Path $Root 'Core\DratCore.cpd') -PathType Leaf) -Message "Portable Core is missing: $Root"
    Assert-DistributionTest -Condition ((Test-Path -LiteralPath (Join-Path $Root 'Libraries\Materials\EngineeringMaterials.cpd') -PathType Leaf) -eq $ExpectMaterials) -Message "Portable Materials content is invalid: $Root"
    Assert-DistributionTest -Condition ((Test-Path -LiteralPath (Join-Path $Root 'Libraries') -PathType Container) -eq $ExpectMaterials) -Message "Portable-project library directory is invalid: $Root"
    Assert-DistributionTest -Condition ((@($projectManifest.libraries) -contains 'EngineeringMaterials') -eq $ExpectMaterials) -Message "Portable-project library inventory is invalid: $Root"

    foreach ($textFile in Get-ChildItem -LiteralPath $Root -File -Recurse | Where-Object { $_.Extension -in @('.cpd', '.json') }) {
        $text = [System.IO.File]::ReadAllText($textFile.FullName)
        foreach ($forbiddenPath in $ForbiddenPaths) {
            Assert-DistributionTest -Condition (-not $text.Contains($forbiddenPath, [System.StringComparison]::OrdinalIgnoreCase)) -Message "Portable project contains an external path in $($textFile.FullName): $forbiddenPath"
        }
    }

    foreach ($sourceFile in Get-ChildItem -LiteralPath $Root -File -Recurse -Filter '*.cpd') {
        foreach ($line in [System.IO.File]::ReadAllLines($sourceFile.FullName)) {
            $includeMatch = [regex]::Match($line, '^\s*#include\s+(?<path>.+?)\s*$')
            if (-not $includeMatch.Success) {
                continue
            }

            $includePath = $includeMatch.Groups['path'].Value.Trim().Trim('"')
            Assert-DistributionTest -Condition (-not [System.IO.Path]::IsPathRooted($includePath) -and $includePath -notmatch '^%[^%]+%') -Message "Portable project contains a non-relative include: $includePath"
            $resolvedInclude = [System.IO.Path]::GetFullPath((Join-Path $sourceFile.DirectoryName $includePath))
            $projectPrefix = [System.IO.Path]::GetFullPath($Root).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
            Assert-DistributionTest -Condition ($resolvedInclude.StartsWith($projectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) -Message "Portable include resolves outside its project: $includePath"
            Assert-DistributionTest -Condition (Test-Path -LiteralPath $resolvedInclude -PathType Leaf) -Message "Portable include target is missing: $includePath"
        }
    }

    $worksheetText = [System.IO.File]::ReadAllText($worksheetPath)
    Assert-DistributionTest -Condition ($worksheetText.Contains('#include ../Core/DratCore.cpd')) -Message 'Portable project Core include is invalid.'
    Assert-DistributionTest -Condition ($worksheetText.Contains('#include ../Libraries/Materials/EngineeringMaterials.cpd') -eq $ExpectMaterials) -Message 'Portable project Materials include is invalid.'
}

function Invoke-PortableProjectRender {
    param(
        [string]$ProjectRoot,
        [string]$OutputPath
    )

    $worksheetPath = Join-Path $ProjectRoot 'Calculations\EngineeringCalculation.cpd'
    $previousErrorActionPreference = $ErrorActionPreference
    $calcPadExitCode = $null
    try {
        $ErrorActionPreference = 'Stop'
        try {
            & $CalcPadCli $worksheetPath $OutputPath -s
            $calcPadExitCode = $LASTEXITCODE
        }
        catch {
            throw "CalcPad launch failed for moved portable project $ProjectRoot. $($_.Exception.Message)"
        }
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    Assert-DistributionTest -Condition ($null -ne $calcPadExitCode -and $calcPadExitCode -eq 0) -Message "CalcPad launch failed for moved portable project $ProjectRoot with exit code $calcPadExitCode."
    Assert-DistributionTest -Condition (Test-Path -LiteralPath $OutputPath -PathType Leaf) -Message "CalcPad did not create portable-project output: $OutputPath"
    $calcPadOutput = [System.IO.File]::ReadAllText($OutputPath)
    Assert-DistributionTest -Condition ($calcPadOutput -notmatch 'Error in &quot;|class="err"') -Message "The moved portable project contains a CalcPad parser or runtime error: $ProjectRoot"
}

$testFailure = $null
try {
    New-Item -ItemType Directory -Path $testRoot -Force | Out-Null

    $buildOverlapRoot = Join-Path $testRoot 'build overlap fixture'
    foreach ($directory in @('Core', 'Libraries', 'Templates', 'Examples', 'docs', 'Tools')) {
        New-Item -ItemType Directory -Path (Join-Path $buildOverlapRoot $directory) -Force | Out-Null
    }
    Copy-Item -LiteralPath (Join-Path $repositoryRoot 'Tools\BuildDistribution.ps1') -Destination (Join-Path $buildOverlapRoot 'Tools')
    $overlapBuildScript = Join-Path $buildOverlapRoot 'Tools\BuildDistribution.ps1'
    foreach ($overlapOutput in @(
        (Join-Path $buildOverlapRoot 'Core'),
        (Join-Path $buildOverlapRoot 'Core\nested output'),
        (Join-Path $buildOverlapRoot 'Tools\nested output'),
        $buildOverlapRoot
    )) {
        Assert-ScriptThrows -Action { & $overlapBuildScript -OutputDirectory $overlapOutput } -ExpectedMessage 'Distribution output overlaps distribution source directory' -FailureMessage "Build accepted an overlapping output/source path: $overlapOutput"
    }
    $buildCoreAlias = Join-Path $testRoot 'build core junction alias'
    New-Item -ItemType Junction -Path $buildCoreAlias -Target (Join-Path $buildOverlapRoot 'Core') -ErrorAction Stop | Out-Null
    Assert-ScriptThrows -Action { & $overlapBuildScript -OutputDirectory (Join-Path $buildCoreAlias 'uncreated nested output') } -ExpectedMessage 'Distribution output overlaps distribution source directory' -FailureMessage 'Build accepted an output whose nearest existing ancestor is a junction into a source tree.'

    $overlapInstallParent = Join-Path $testRoot 'install overlap fixture'
    $overlapPackage = Join-Path $overlapInstallParent 'package'
    New-Item -ItemType Directory -Path $overlapPackage -Force | Out-Null
    $repositoryInstaller = Join-Path $repositoryRoot 'Tools\InstallDratCalcpad.ps1'
    foreach ($overlapInstallCase in @(
        [ordered]@{ package = $overlapPackage; destination = $overlapPackage },
        [ordered]@{ package = $overlapPackage; destination = (Join-Path $overlapPackage 'nested install') },
        [ordered]@{ package = $overlapPackage; destination = $overlapInstallParent }
    )) {
        Assert-ScriptThrows -Action { & $repositoryInstaller -PackagePath $overlapInstallCase.package -DestinationPath $overlapInstallCase.destination } -ExpectedMessage 'Package and installation paths must not be equal, ancestors, or descendants' -FailureMessage 'Installer accepted overlapping package and installation paths.'
    }
    $overlapPackageAlias = Join-Path $testRoot 'package junction alias'
    New-Item -ItemType Junction -Path $overlapPackageAlias -Target $overlapPackage -ErrorAction Stop | Out-Null
    Assert-ScriptThrows -Action { & $repositoryInstaller -PackagePath $overlapPackage -DestinationPath (Join-Path $overlapPackageAlias 'uncreated nested install') } -ExpectedMessage 'Package and installation paths must not be equal, ancestors, or descendants' -FailureMessage 'Installer accepted a destination whose nearest existing ancestor is a junction into the package.'

    $overlapProjectParent = Join-Path $testRoot 'project overlap fixture'
    $overlapInstallation = Join-Path $overlapProjectParent 'installation'
    New-Item -ItemType Directory -Path $overlapInstallation -Force | Out-Null
    $repositoryProjectGenerator = Join-Path $repositoryRoot 'Tools\NewDratProject.ps1'
    foreach ($overlapProjectCase in @(
        [ordered]@{ installation = $overlapInstallation; project = $overlapInstallation },
        [ordered]@{ installation = $overlapInstallation; project = (Join-Path $overlapInstallation 'nested project') },
        [ordered]@{ installation = $overlapInstallation; project = $overlapProjectParent }
    )) {
        Assert-ScriptThrows -Action { & $repositoryProjectGenerator -InstallationPath $overlapProjectCase.installation -DestinationPath $overlapProjectCase.project } -ExpectedMessage 'Installation and project paths must not be equal, ancestors, or descendants' -FailureMessage 'Project generator accepted overlapping installation and project paths.'
    }
    $overlapInstallationAlias = Join-Path $testRoot 'installation junction alias'
    New-Item -ItemType Junction -Path $overlapInstallationAlias -Target $overlapInstallation -ErrorAction Stop | Out-Null
    Assert-ScriptThrows -Action { & $repositoryProjectGenerator -InstallationPath $overlapInstallation -DestinationPath (Join-Path $overlapInstallationAlias 'uncreated nested project') } -ExpectedMessage 'Installation and project paths must not be equal, ancestors, or descendants' -FailureMessage 'Project generator accepted a destination whose nearest existing ancestor is a junction into the installation.'

    & (Join-Path $repositoryRoot 'Tools\BuildDistribution.ps1') -OutputDirectory $outputRoot -Archive
    $packageDirectories = @(Get-ChildItem -LiteralPath $outputRoot -Directory)
    Assert-DistributionTest -Condition ($packageDirectories.Count -eq 1) -Message 'Distribution did not create exactly one versioned package directory.'
    $packageRoot = $packageDirectories[0].FullName
    $manifestPath = Join-Path $packageRoot 'manifest.json'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    Assert-DistributionTest -Condition ($manifest.schema_version -eq 2 -and $manifest.product -eq 'DRAT CalcpadCE') -Message 'Distribution manifest identity is invalid.'
    Assert-DistributionTest -Condition ($manifest.version -match '^\d+\.\d+\.\d+$' -and $manifest.core_api -gt 0) -Message 'Distribution version or Core API is invalid.'
    Assert-DistributionTest -Condition ($packageDirectories[0].Name -ceq "DRAT-Calcpad-$($manifest.version)") -Message 'Distribution directory does not match the manifest version.'
    Assert-DistributionMetadata -Root $packageRoot -Manifest $manifest

    foreach ($requiredPath in @(
        'Core\DratCore.cpd',
        'Libraries\Analysis\BeamAnalysis.cpd',
        'Libraries\Materials\EngineeringMaterials.cpd',
        'Libraries\Thermophysical\ThermophysicalProperties.cpd',
        'Libraries\Steel\AiscAngleSections.cpd',
        'Libraries\Steel\AiscChannelSections.cpd',
        'Libraries\Steel\AiscHssSections.cpd',
        'Libraries\Steel\StructuralSections.cpd',
        'Templates\EngineeringCalculationTemplate.cpd',
        'Examples\BeamAnalysisDemo.cpd',
        'Examples\ThermophysicalPropertiesDemo.cpd',
        'docs\Distribution.md',
        'Tools\InstallDratCalcpad.ps1',
        'Tools\NewDratProject.ps1',
        'README.md',
        'CHANGELOG.md',
        'LICENSE',
        'THIRD-PARTY-NOTICES.md'
    )) {
        Assert-DistributionTest -Condition (Test-Path -LiteralPath (Join-Path $packageRoot $requiredPath) -PathType Leaf) -Message "Required distribution file is missing: $requiredPath"
    }
    Assert-DistributionTest -Condition (-not (Test-Path -LiteralPath (Join-Path $packageRoot 'Core\Src'))) -Message 'Core source modules must not be included in the runtime distribution.'
    Assert-DistributionTest -Condition (-not (Test-Path -LiteralPath (Join-Path $packageRoot 'Tests'))) -Message 'Repository tests must not be included in the runtime distribution.'
    Assert-DistributionTest -Condition (-not (Test-Path -LiteralPath (Join-Path $packageRoot 'Data'))) -Message 'Raw generator inputs and provenance workbooks must not be included in the runtime distribution.'
    Assert-DistributionTest -Condition (@(Get-ChildItem -LiteralPath $packageRoot -File -Recurse | Where-Object Extension -In @('.xlsx', '.xls', '.json')).Count -eq 1) -Message 'Runtime distribution contains an unexpected raw workbook or JSON dataset.'
    Assert-ManifestFileRecords -Root $packageRoot -Records @($manifest.files) -Exclude @('manifest.json')

    $expectedLibraryPaths = @(
        'Libraries/Analysis/BeamAnalysis.cpd',
        'Libraries/Materials/EngineeringMaterials.cpd',
        'Libraries/Thermophysical/ThermophysicalProperties.cpd',
        'Libraries/Steel/AiscAngleSections.cpd',
        'Libraries/Steel/AiscChannelSections.cpd',
        'Libraries/Steel/AiscHssSections.cpd',
        'Libraries/Steel/StructuralSections.cpd'
    )
    $packagedLibraryPaths = @(
        Get-ChildItem -LiteralPath (Join-Path $packageRoot 'Libraries') -File -Recurse -Filter '*.cpd' |
            ForEach-Object { [System.IO.Path]::GetRelativePath($packageRoot, $_.FullName).Replace('\', '/') }
    )
    Assert-DistributionTest -Condition ($manifest.libraries.Count -eq $packagedLibraryPaths.Count) -Message 'Distribution library manifest does not cover every packaged library.'
    foreach ($packagedLibraryPath in $packagedLibraryPaths) {
        Assert-DistributionTest -Condition (@($manifest.libraries | Where-Object { $_.path -ceq $packagedLibraryPath }).Count -eq 1) -Message "Packaged library has no unique manifest record: $packagedLibraryPath"
    }
    foreach ($libraryPath in $expectedLibraryPaths) {
        $libraryRecords = @($manifest.libraries | Where-Object { $_.path -ceq $libraryPath })
        Assert-DistributionTest -Condition ($libraryRecords.Count -eq 1) -Message "Distribution library record is missing or duplicated: $libraryPath"
        Assert-DistributionTest -Condition ($libraryRecords[0].revision -match '^\d+\.\d+\.\d+$') -Message "Distribution library revision is invalid: $libraryPath"
        $libraryText = [System.IO.File]::ReadAllText((Join-Path $packageRoot $libraryPath.Replace('/', [System.IO.Path]::DirectorySeparatorChar)))
        $revisionMatch = [regex]::Match($libraryText, '(?m)^#def\s+\w+LibraryRevision\$\s*=\s*(?<revision>\d+\.\d+\.\d+)\s*$')
        Assert-DistributionTest -Condition ($revisionMatch.Success -and $revisionMatch.Groups['revision'].Value -ceq $libraryRecords[0].revision) -Message "Distribution library revision does not match its packaged source: $libraryPath"
        Assert-DistributionTest -Condition ($null -ne $libraryRecords[0].requirements.DRAT_CORE_API) -Message "Distribution library Core requirement is missing: $libraryPath"
        Assert-DistributionTest -Condition ($manifest.core_api -ge $libraryRecords[0].requirements.DRAT_CORE_API.minimum -and $manifest.core_api -lt $libraryRecords[0].requirements.DRAT_CORE_API.maximum_exclusive) -Message "Packaged Core is incompatible with library: $libraryPath"
    }
    $beamManifestRecord = @($manifest.libraries | Where-Object { $_.path -ceq 'Libraries/Analysis/BeamAnalysis.cpd' })[0]
    Assert-DistributionTest -Condition ($null -ne $beamManifestRecord.optional_requirements.DRAT_PLOTTING_API) -Message 'Beam Analysis optional Plotting API requirement is missing.'

    foreach ($sourceFile in Get-ChildItem -LiteralPath $packageRoot -File -Recurse -Filter '*.cpd') {
        foreach ($line in [System.IO.File]::ReadAllLines($sourceFile.FullName)) {
            $includeMatch = [regex]::Match($line, '^\s*#include\s+(?<path>.+?)\s*$')
            if ($includeMatch.Success) {
                $includePath = $includeMatch.Groups['path'].Value.Trim().Trim('"')
                Assert-DistributionTest -Condition (-not [System.IO.Path]::IsPathRooted($includePath) -and $includePath -notmatch '^%[^%]+%') -Message "Packaged worksheet contains an absolute include: $($sourceFile.FullName)"
            }
        }
        $sourceText = [System.IO.File]::ReadAllText($sourceFile.FullName)
        Assert-DistributionTest -Condition (-not $sourceText.Contains($repositoryRoot, [System.StringComparison]::OrdinalIgnoreCase)) -Message "Packaged worksheet contains the development repository path: $($sourceFile.FullName)"
    }

    $archivePath = Join-Path $outputRoot ($packageDirectories[0].Name + '.zip')
    Assert-DistributionTest -Condition (Test-Path -LiteralPath $archivePath -PathType Leaf) -Message 'Distribution archive was not created.'
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($archivePath)
    try {
        $archiveFileEntries = @($archive.Entries | Where-Object { -not [string]::IsNullOrEmpty($_.Name) })
        Assert-DistributionTest -Condition ($archiveFileEntries.Count -eq ($manifest.files.Count + 1)) -Message 'Archive file count does not match the package and manifest.'
        foreach ($entry in $archive.Entries) {
            $entryPath = $entry.FullName.Replace('\', '/')
            Assert-DistributionTest -Condition ($entryPath.StartsWith($packageDirectories[0].Name + '/', [System.StringComparison]::Ordinal)) -Message "Archive entry is outside the versioned package root: $entryPath"
            Assert-DistributionTest -Condition ($entryPath -notmatch '(^|/)\.\.(/|$)' -and $entryPath -notmatch '^[A-Za-z]:|^/') -Message "Archive entry path is unsafe: $entryPath"
        }
    }
    finally {
        $archive.Dispose()
    }

    $extractionRoot = Join-Path $testRoot 'extracted archive'
    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractionRoot
    $extractedPackageRoot = Join-Path $extractionRoot $packageDirectories[0].Name
    $extractedManifest = Get-Content -LiteralPath (Join-Path $extractedPackageRoot 'manifest.json') -Raw | ConvertFrom-Json
    Assert-ManifestFileRecords -Root $extractedPackageRoot -Records @($extractedManifest.files) -Exclude @('manifest.json')
    Assert-DistributionMetadata -Root $extractedPackageRoot -Manifest $extractedManifest
    $packagedInstallerPath = Join-Path $extractedPackageRoot 'Tools\InstallDratCalcpad.ps1'

    $tamperedPackageRoot = Join-Path $testRoot 'tampered package'
    Copy-Item -LiteralPath $extractedPackageRoot -Destination $tamperedPackageRoot -Recurse
    Add-Content -LiteralPath (Join-Path $tamperedPackageRoot 'Core\DratCore.cpd') -Value "`n' tampered"
    $tamperRejected = $false
    try {
        & (Join-Path $tamperedPackageRoot 'Tools\InstallDratCalcpad.ps1') -PackagePath $tamperedPackageRoot -DestinationPath (Join-Path $testRoot 'tampered install')
    }
    catch {
        $tamperRejected = $true
    }
    Assert-DistributionTest -Condition $tamperRejected -Message 'Installer accepted a package with a modified file.'

    $unlistedPackageRoot = Join-Path $testRoot 'unlisted package'
    Copy-Item -LiteralPath $extractedPackageRoot -Destination $unlistedPackageRoot -Recurse
    Set-Content -LiteralPath (Join-Path $unlistedPackageRoot 'unexpected.txt') -Value 'not declared by manifest'
    $unlistedRejected = $false
    try {
        & (Join-Path $unlistedPackageRoot 'Tools\InstallDratCalcpad.ps1') -PackagePath $unlistedPackageRoot -DestinationPath (Join-Path $testRoot 'unlisted install')
    }
    catch {
        $unlistedRejected = $true
    }
    Assert-DistributionTest -Condition $unlistedRejected -Message 'Installer accepted a package with an unlisted file.'

    $utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)

    $metadataTamperCases = @(
        [ordered]@{
            id = 'version'
            expected = 'Manifest version does not match packaged DRATCoreVersion$'
            mutate = { param($metadata) $metadata.version = Get-PriorVersion -Version $metadata.version }
        },
        [ordered]@{
            id = 'component api'
            expected = 'Manifest component API does not match packaged Core declaration'
            mutate = { param($metadata) $metadata.component_apis.DRAT_DATA_WRAPPER_API = [int]$metadata.component_apis.DRAT_DATA_WRAPPER_API + 1 }
        },
        [ordered]@{
            id = 'library identity'
            expected = 'Manifest library identity does not match packaged declarations'
            mutate = { param($metadata) $metadata.libraries[0].display_name = $metadata.libraries[0].display_name + ' tampered' }
        },
        [ordered]@{
            id = 'library revision'
            expected = 'Manifest library identity does not match packaged declarations'
            mutate = { param($metadata) $metadata.libraries[0].revision = '9.9.9' }
        },
        [ordered]@{
            id = 'required api range'
            expected = 'required API metadata range does not match packaged declaration'
            mutate = {
                param($metadata)
                $library = @($metadata.libraries | Where-Object { $_.name -ceq 'EngineeringMaterials' })[0]
                $library.requirements.DRAT_CORE_API.minimum = [int]$library.requirements.DRAT_CORE_API.minimum + 1
            }
        },
        [ordered]@{
            id = 'optional api range'
            expected = 'optional API metadata range does not match packaged declaration'
            mutate = {
                param($metadata)
                $library = @($metadata.libraries | Where-Object { $_.name -ceq 'BeamAnalysis' })[0]
                $library.optional_requirements.DRAT_PLOTTING_API.maximum_exclusive = [int]$library.optional_requirements.DRAT_PLOTTING_API.maximum_exclusive + 1
            }
        }
    )
    foreach ($metadataTamperCase in $metadataTamperCases) {
        $metadataTamperedRoot = Join-Path $testRoot ("metadata tampered package - " + $metadataTamperCase.id)
        Copy-Item -LiteralPath $extractedPackageRoot -Destination $metadataTamperedRoot -Recurse
        $metadataTamperedManifestPath = Join-Path $metadataTamperedRoot 'manifest.json'
        $metadataTamperedManifest = Get-Content -LiteralPath $metadataTamperedManifestPath -Raw | ConvertFrom-Json
        & ($metadataTamperCase.mutate) $metadataTamperedManifest
        [System.IO.File]::WriteAllText($metadataTamperedManifestPath, ($metadataTamperedManifest | ConvertTo-Json -Depth 12) + [Environment]::NewLine, $utf8WithoutBom)
        $metadataTamperedInstall = Join-Path $testRoot ("metadata tampered install - " + $metadataTamperCase.id)
        Assert-ScriptThrows -Action { & (Join-Path $metadataTamperedRoot 'Tools\InstallDratCalcpad.ps1') -PackagePath $metadataTamperedRoot -DestinationPath $metadataTamperedInstall } -ExpectedMessage $metadataTamperCase.expected -FailureMessage "Installer accepted tampered $($metadataTamperCase.id) metadata."
    }

    $priorPackageRoot = Join-Path $testRoot 'internally consistent prior package'
    Copy-Item -LiteralPath $extractedPackageRoot -Destination $priorPackageRoot -Recurse
    $priorManifestPath = Join-Path $priorPackageRoot 'manifest.json'
    $priorManifest = Get-Content -LiteralPath $priorManifestPath -Raw | ConvertFrom-Json
    $priorVersion = Get-PriorVersion -Version $priorManifest.version
    $priorVersionParts = @($priorVersion.Split('.') | ForEach-Object { [int]$_ })
    $priorCoreApi = ($priorVersionParts[0] * 10000) + ($priorVersionParts[1] * 100) + $priorVersionParts[2]
    $priorCorePath = Join-Path $priorPackageRoot 'Core\DratCore.cpd'
    $priorCoreText = [System.IO.File]::ReadAllText($priorCorePath)
    Assert-DistributionTest -Condition ([regex]::Matches($priorCoreText, '(?m)^#def\s+DRATCoreVersion\$\s*=\s*\d+\.\d+\.\d+\s*$').Count -eq 1) -Message 'Prior fixture cannot uniquely replace DRATCoreVersion$.'
    Assert-DistributionTest -Condition ([regex]::Matches($priorCoreText, '(?m)^DRAT_CORE_API\s*=\s*\d+\s*$').Count -eq 1) -Message 'Prior fixture cannot uniquely replace DRAT_CORE_API.'
    $priorCoreText = [regex]::Replace($priorCoreText, '(?m)^#def\s+DRATCoreVersion\$\s*=\s*\d+\.\d+\.\d+\s*$', "#def DRATCoreVersion$ = $priorVersion")
    $priorCoreText = [regex]::Replace($priorCoreText, '(?m)^DRAT_CORE_API\s*=\s*\d+\s*$', "DRAT_CORE_API = $priorCoreApi")
    [System.IO.File]::WriteAllText($priorCorePath, $priorCoreText, $utf8WithoutBom)
    $priorManifest.version = $priorVersion
    $priorManifest.core_api = $priorCoreApi
    $priorManifest.component_apis.DRAT_CORE_API = $priorCoreApi
    $priorCoreRecords = @($priorManifest.files | Where-Object { $_.path -ceq 'Core/DratCore.cpd' })
    Assert-DistributionTest -Condition ($priorCoreRecords.Count -eq 1) -Message 'Prior fixture Core manifest record is missing or duplicated.'
    $priorCoreRecords[0].sha256 = (Get-FileHash -LiteralPath $priorCorePath -Algorithm SHA256).Hash.ToLowerInvariant()
    [System.IO.File]::WriteAllText($priorManifestPath, ($priorManifest | ConvertTo-Json -Depth 12) + [Environment]::NewLine, $utf8WithoutBom)
    Assert-ManifestFileRecords -Root $priorPackageRoot -Records @($priorManifest.files) -Exclude @('manifest.json')
    Assert-DistributionMetadata -Root $priorPackageRoot -Manifest $priorManifest

    & (Join-Path $priorPackageRoot 'Tools\InstallDratCalcpad.ps1') -PackagePath $priorPackageRoot -DestinationPath $installRoot
    $priorVersionRoot = Join-Path $installRoot ("versions\$priorVersion")
    $currentRoot = Join-Path $installRoot 'Current'
    Assert-DistributionTest -Condition (Test-Path -LiteralPath (Join-Path $priorVersionRoot '.drat-managed-install.json') -PathType Leaf) -Message 'Prior versioned installation is missing.'
    $priorMarker = Get-Content -LiteralPath (Join-Path $priorVersionRoot '.drat-managed-install.json') -Raw | ConvertFrom-Json
    Assert-DistributionTest -Condition ($priorMarker.version -eq $priorVersion) -Message 'Prior versioned installation marker is invalid.'
    $priorVersionFingerprint = Get-TreeFingerprint -Root $priorVersionRoot

    $priorProjectRoot = Join-Path $generatedProjectsRoot 'Prior Version Project'
    & (Join-Path $currentRoot 'Tools\NewDratProject.ps1') -InstallationPath $currentRoot -DestinationPath $priorProjectRoot
    $priorProjectFingerprint = Get-TreeFingerprint -Root $priorProjectRoot

    & $packagedInstallerPath -PackagePath $extractedPackageRoot -DestinationPath $installRoot
    & $packagedInstallerPath -PackagePath $extractedPackageRoot -DestinationPath $installRoot

    $currentMarker = Get-Content -LiteralPath (Join-Path $currentRoot '.drat-managed-install.json') -Raw | ConvertFrom-Json
    $currentManifest = Get-Content -LiteralPath (Join-Path $currentRoot 'manifest.json') -Raw | ConvertFrom-Json
    Assert-DistributionTest -Condition ($currentMarker.version -eq $manifest.version -and $currentManifest.version -eq $manifest.version) -Message 'Stable Current installation does not identify the newly installed version.'
    Assert-DistributionTest -Condition ((Get-TreeFingerprint -Root $priorVersionRoot) -ceq $priorVersionFingerprint) -Message 'Updating modified the retained previous version.'
    Assert-DistributionTest -Condition (Test-Path -LiteralPath (Join-Path $installRoot "versions\$($manifest.version)\.drat-managed-install.json") -PathType Leaf) -Message 'New versioned installation is missing.'
    Assert-ManifestFileRecords -Root $currentRoot -Records @($currentManifest.files) -Exclude @('manifest.json', '.drat-managed-install.json')
    Assert-DistributionMetadata -Root $currentRoot -Manifest $currentManifest
    Assert-DistributionTest -Condition ((Get-TreeFingerprint -Root $priorProjectRoot) -ceq $priorProjectFingerprint) -Message 'Updating modified an existing prior-version portable project.'

    $installedProjectGenerator = Join-Path $currentRoot 'Tools\NewDratProject.ps1'
    $missingMaterialsInstallation = Join-Path $testRoot 'installation missing Materials manifest entry'
    Copy-Item -LiteralPath $currentRoot -Destination $missingMaterialsInstallation -Recurse
    $missingMaterialsManifestPath = Join-Path $missingMaterialsInstallation 'manifest.json'
    $missingMaterialsManifest = Get-Content -LiteralPath $missingMaterialsManifestPath -Raw | ConvertFrom-Json
    $missingMaterialsManifest.files = @($missingMaterialsManifest.files | Where-Object { $_.path -cne 'Libraries/Materials/EngineeringMaterials.cpd' })
    [System.IO.File]::WriteAllText($missingMaterialsManifestPath, ($missingMaterialsManifest | ConvertTo-Json -Depth 12) + [Environment]::NewLine, $utf8WithoutBom)
    $missingMaterialsProject = Join-Path $generatedProjectsRoot 'Missing Materials Entry Project'
    Assert-ScriptThrows -Action { & (Join-Path $missingMaterialsInstallation 'Tools\NewDratProject.ps1') -InstallationPath $missingMaterialsInstallation -DestinationPath $missingMaterialsProject -IncludeMaterials } -ExpectedMessage 'Installed DRAT manifest does not contain exactly one record for: Libraries/Materials/EngineeringMaterials.cpd' -FailureMessage 'Materials project generation accepted a missing EngineeringMaterials.cpd manifest entry.'
    Assert-DistributionTest -Condition (-not (Test-Path -LiteralPath $missingMaterialsProject)) -Message 'Materials project generation wrote files before completing EngineeringMaterials.cpd preflight.'

    $missingMaterialsFileInstallation = Join-Path $testRoot 'installation missing Materials entrypoint file'
    Copy-Item -LiteralPath $currentRoot -Destination $missingMaterialsFileInstallation -Recurse
    Remove-Item -LiteralPath (Join-Path $missingMaterialsFileInstallation 'Libraries\Materials\EngineeringMaterials.cpd') -Force
    $missingMaterialsFileProject = Join-Path $generatedProjectsRoot 'Missing Materials Entrypoint Project'
    Assert-ScriptThrows -Action { & (Join-Path $missingMaterialsFileInstallation 'Tools\NewDratProject.ps1') -InstallationPath $missingMaterialsFileInstallation -DestinationPath $missingMaterialsFileProject -IncludeMaterials } -ExpectedMessage 'Installed DRAT file is missing: Libraries/Materials/EngineeringMaterials.cpd' -FailureMessage 'Materials project generation accepted a manifest-declared but missing EngineeringMaterials.cpd entrypoint.'
    Assert-DistributionTest -Condition (-not (Test-Path -LiteralPath $missingMaterialsFileProject)) -Message 'Materials project generation wrote files before detecting the missing EngineeringMaterials.cpd entrypoint.'

    $coreProjectRoot = Join-Path $generatedProjectsRoot 'Current Core Only Project'
    $materialsProjectRoot = Join-Path $generatedProjectsRoot 'Current Materials Project'
    & $installedProjectGenerator -InstallationPath $currentRoot -DestinationPath $coreProjectRoot
    & $installedProjectGenerator -InstallationPath $currentRoot -DestinationPath $materialsProjectRoot -IncludeMaterials
    $forbiddenPaths = @($repositoryRoot, $installRoot, $extractedPackageRoot, $priorPackageRoot)
    Assert-PortableProject -Root $coreProjectRoot -ExpectMaterials $false -ExpectedVersion $manifest.version -ForbiddenPaths $forbiddenPaths
    Assert-PortableProject -Root $materialsProjectRoot -ExpectMaterials $true -ExpectedVersion $manifest.version -ForbiddenPaths $forbiddenPaths
    $coreProjectFingerprint = Get-TreeFingerprint -Root $coreProjectRoot
    $materialsProjectFingerprint = Get-TreeFingerprint -Root $materialsProjectRoot

    New-Item -ItemType Directory -Path $movedProjectsRoot -Force | Out-Null
    $movedCoreProjectRoot = Join-Path $movedProjectsRoot 'Moved Core Only Project'
    $movedMaterialsProjectRoot = Join-Path $movedProjectsRoot 'Moved Materials Project'
    Move-Item -LiteralPath $coreProjectRoot -Destination $movedCoreProjectRoot
    Move-Item -LiteralPath $materialsProjectRoot -Destination $movedMaterialsProjectRoot
    Assert-PortableProject -Root $movedCoreProjectRoot -ExpectMaterials $false -ExpectedVersion $manifest.version -ForbiddenPaths $forbiddenPaths
    Assert-PortableProject -Root $movedMaterialsProjectRoot -ExpectMaterials $true -ExpectedVersion $manifest.version -ForbiddenPaths $forbiddenPaths
    Assert-DistributionTest -Condition ((Get-TreeFingerprint -Root $movedCoreProjectRoot) -ceq $coreProjectFingerprint) -Message 'Moving changed the Core-only portable project.'
    Assert-DistributionTest -Condition ((Get-TreeFingerprint -Root $movedMaterialsProjectRoot) -ceq $materialsProjectFingerprint) -Message 'Moving changed the Materials portable project.'

    $requestedCalcPadCli = $CalcPadCli
    $invalidCalcPadCli = Join-Path $testRoot 'missing-calcpad-cli.exe'
    try {
        $CalcPadCli = $invalidCalcPadCli
        Assert-ScriptThrows -Action { Invoke-PortableProjectRender -ProjectRoot $movedCoreProjectRoot -OutputPath (Join-Path $testRoot 'invalid-cli-output.html') } -ExpectedMessage 'CalcPad launch failed' -FailureMessage 'A CalcPad native launch failure did not terminate distribution qualification.'
    }
    finally {
        $CalcPadCli = $requestedCalcPadCli
    }

    if (-not [string]::IsNullOrWhiteSpace($CalcPadCli)) {
        Assert-DistributionTest -Condition (Test-Path -LiteralPath $CalcPadCli -PathType Leaf) -Message "CalcPad CLI is missing: $CalcPadCli"
        $offlineInstallRoot = Join-Path $testRoot 'installation made unavailable'
        Move-Item -LiteralPath $installRoot -Destination $offlineInstallRoot
        $offlineExtractionRoot = Join-Path $testRoot 'package made unavailable'
        Move-Item -LiteralPath $extractionRoot -Destination $offlineExtractionRoot
        Invoke-PortableProjectRender -ProjectRoot $movedCoreProjectRoot -OutputPath (Join-Path $testRoot 'moved-core-only.html')
        Invoke-PortableProjectRender -ProjectRoot $movedMaterialsProjectRoot -OutputPath (Join-Path $testRoot 'moved-materials.html')
        Write-Output '[PASS] CalcPad rendered both moved projects after installation and package paths were made unavailable.'
    }
    else {
        Write-Output '[SKIP] CalcPad rendering was not requested; static relocation and dependency checks passed.'
    }

    Write-Output $successMarker
}
catch {
    $testFailure = $_
}
finally {
    if ($KeepOutput) {
        Write-Output "Distribution qualification output retained at: $testRoot"
    }
    else {
        $resolvedTestRoot = [System.IO.Path]::GetFullPath($testRoot)
        $temporaryRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
        if ($resolvedTestRoot.StartsWith($temporaryRoot, [System.StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $resolvedTestRoot).StartsWith('drat-distribution-test-')) {
            Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

if ($null -ne $testFailure) {
    [Console]::Error.WriteLine($testFailure.ToString())
    exit 1
}
exit 0
