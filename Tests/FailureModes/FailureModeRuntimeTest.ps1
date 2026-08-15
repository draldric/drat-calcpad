[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$CalcPadCli,

    [string]$OutputRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$testRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $testRoot '..\..'))
$fixtureRoot = Join-Path $testRoot 'Fixtures'
$ownsOutputRoot = [string]::IsNullOrWhiteSpace($OutputRoot)
if ($ownsOutputRoot) {
    $OutputRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('drat-failure-modes-' + [guid]::NewGuid().ToString('N'))
}
$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)

if (-not (Test-Path -LiteralPath $CalcPadCli -PathType Leaf)) {
    throw "CalcPad CE CLI was not found: $CalcPadCli"
}
if (-not (Test-Path -LiteralPath $fixtureRoot -PathType Container)) {
    throw "Failure-mode fixture directory was not found: $fixtureRoot"
}
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

$specifications = @(
    [pscustomobject]@{
        Name = 'IncompatibleCoreApi'
        Required = @(
            'EngineeringMaterials requires DRAT core API 1.x',
            'StructuralSections requires DRAT core API 1.x',
            'AiscHssSections requires DRAT core API 1.x',
            'AiscChannelSections requires DRAT core API 1.x',
            'AiscAngleSections requires DRAT core API 1.x',
            'This library requires DRAT core API 1.x')
        Forbidden = @('Error in "', 'Undefined variable or units', 'Unexpected error:')
    },
    [pscustomobject]@{
        Name = 'IncompatibleDataWrapperApi'
        Required = @(
            'EngineeringMaterials requires DataWrapper API 0.3.2 or newer',
            'StructuralSections requires DataWrapper API 0.3.2 or newer',
            'AiscHssSections requires DataWrapper API 0.3.2 or newer',
            'AiscChannelSections requires DataWrapper API 0.3.2 or newer',
            'AiscAngleSections requires DataWrapper API 0.3.2 or newer',
            'This library requires DataWrapper API 0.3.2 or newer')
        Forbidden = @('Error in "', 'Undefined variable or units', 'Unexpected error:')
    },
    [pscustomobject]@{
        Name = 'IncompatibleChecksApi'
        Required = @('This library requires Checks API 1.2.x')
        Forbidden = @('Error in "', 'Undefined variable or units', 'Unexpected error:')
    },
    [pscustomobject]@{
        Name = 'MissingCoreDependency'
        Required = @('Undefined variable or units', 'DRAT_CORE_API')
        Forbidden = @('Common Engineering Materials Library')
    },
    [pscustomobject]@{
        Name = 'IncompatibleCheckUnits'
        Required = @('Error in "unit_check_status = CheckUpperStatus', 'Inconsistent units')
        Forbidden = @('<span class="eq"><var>unit</var><sub>check</sub><sub>status</sub>')
    },
    [pscustomobject]@{
        Name = 'IncompatiblePlottingApi'
        Required = @(
            'EngineeringMaterials requires Plotting API 3.2 or newer',
            'Beam diagram helpers require Plotting API 3.2.x')
        Forbidden = @('Error in "', 'Undefined variable or units', 'Unexpected error:')
    },
    [pscustomobject]@{
        Name = 'UnitBearingBeamCount'
        Required = @('Error in "unit_count_status = BeamModelStatus', 'Inconsistent units')
        Forbidden = @('<span class="eq"><var>unit</var><sub>count</sub><sub>status</sub>')
    }
)

$failures = [System.Collections.Generic.List[string]]::new()
$fixtureNames = @(Get-ChildItem -LiteralPath $fixtureRoot -File -Filter '*.cpd' | ForEach-Object BaseName | Sort-Object)
$specificationNames = @($specifications | ForEach-Object Name | Sort-Object)
foreach ($fixtureName in $fixtureNames) {
    if ($fixtureName -notin $specificationNames) {
        $failures.Add("Fixture '$fixtureName' has no runtime specification.")
    }
}
foreach ($specificationName in $specificationNames) {
    if ($specificationName -notin $fixtureNames) {
        $failures.Add("Runtime specification '$specificationName' has no fixture file.")
    }
}
foreach ($duplicateSpecification in ($specifications | Group-Object Name | Where-Object Count -gt 1)) {
    $failures.Add("Runtime specification '$($duplicateSpecification.Name)' is duplicated.")
}

try {
    foreach ($specification in $specifications) {
        $fixturePath = Join-Path $fixtureRoot ($specification.Name + '.cpd')
        $outputPath = Join-Path $OutputRoot ($specification.Name + '.html')
        if (-not (Test-Path -LiteralPath $fixturePath -PathType Leaf)) {
            $failures.Add("Missing fixture $fixturePath.")
            continue
        }

        if ($specification.Name -ceq 'IncompatiblePlottingApi') {
            $mirrorRoot = Join-Path $OutputRoot 'IncompatiblePlottingApiMirror'
            $mirrorCoreDirectory = Join-Path $mirrorRoot 'Core'
            $mirrorMaterialsDirectory = Join-Path $mirrorRoot 'Libraries\Materials'
            $mirrorAnalysisDirectory = Join-Path $mirrorRoot 'Libraries\Analysis'
            $mirrorFixtureDirectory = Join-Path $mirrorRoot 'Tests\FailureModes\Fixtures'
            foreach ($directory in @($mirrorCoreDirectory, $mirrorMaterialsDirectory, $mirrorAnalysisDirectory, $mirrorFixtureDirectory)) {
                New-Item -ItemType Directory -Path $directory -Force | Out-Null
            }

            $mirrorCorePath = Join-Path $mirrorCoreDirectory 'DratCore.cpd'
            $coreText = [System.IO.File]::ReadAllText((Join-Path $repositoryRoot 'Core\DratCore.cpd'))
            $patchedCoreText = [regex]::Replace($coreText, '(?m)^DRAT_PLOTTING_API\s*=\s*\d+\s*$', 'DRAT_PLOTTING_API = 1')
            if ($patchedCoreText -ceq $coreText) {
                $failures.Add('IncompatiblePlottingApi could not patch DRAT_PLOTTING_API in its temporary Core mirror.')
                continue
            }
            [System.IO.File]::WriteAllText($mirrorCorePath, $patchedCoreText)
            Copy-Item -LiteralPath (Join-Path $repositoryRoot 'Libraries\Materials\EngineeringMaterials.cpd') -Destination (Join-Path $mirrorMaterialsDirectory 'EngineeringMaterials.cpd')
            Copy-Item -LiteralPath (Join-Path $repositoryRoot 'Libraries\Analysis\BeamAnalysis.cpd') -Destination (Join-Path $mirrorAnalysisDirectory 'BeamAnalysis.cpd')
            Copy-Item -LiteralPath $fixturePath -Destination (Join-Path $mirrorFixtureDirectory 'IncompatiblePlottingApi.cpd')
            $fixturePath = Join-Path $mirrorFixtureDirectory 'IncompatiblePlottingApi.cpd'
        }

        & $CalcPadCli $fixturePath $outputPath -s
        if ($LASTEXITCODE -ne 0) {
            $failures.Add("$($specification.Name) returned CalcPad CLI exit code $LASTEXITCODE.")
            continue
        }
        if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
            $failures.Add("$($specification.Name) did not generate HTML output.")
            continue
        }

        $html = [System.IO.File]::ReadAllText($outputPath)
        foreach ($requiredText in $specification.Required) {
            if (-not $html.Contains($requiredText, [System.StringComparison]::Ordinal)) {
                $failures.Add("$($specification.Name) did not report required text '$requiredText'.")
            }
        }
        foreach ($forbiddenText in $specification.Forbidden) {
            if ($html.Contains($forbiddenText, [System.StringComparison]::Ordinal)) {
                $failures.Add("$($specification.Name) rendered forbidden text '$forbiddenText'.")
            }
        }
    }
}
finally {
    if ($ownsOutputRoot -and (Test-Path -LiteralPath $OutputRoot -PathType Container)) {
        $tempPrefix = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
        $safeOutputRoot = $OutputRoot.StartsWith($tempPrefix, [System.StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $OutputRoot).StartsWith('drat-failure-modes-', [System.StringComparison]::Ordinal)
        if ($safeOutputRoot) {
            Remove-Item -LiteralPath $OutputRoot -Recurse -Force
        }
    }
}

if ($failures.Count -gt 0) {
    foreach ($failure in $failures) {
        Write-Output "[FAIL] $failure"
    }
    exit 1
}

Write-Output "[PASS] $($specifications.Count) negative CalcPad fixtures produced the expected compatibility or unit-error diagnostics without false passes."
exit 0
