$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$temporaryBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
$fixtureRoot = [System.IO.Path]::GetFullPath((Join-Path $temporaryBase ('drat-build-core-' + [System.Guid]::NewGuid().ToString('N'))))
$fixtureTools = Join-Path $fixtureRoot 'Tools'
$fixtureCore = Join-Path $fixtureRoot 'Core'
$fixtureSource = Join-Path $fixtureCore 'Src'
$fixtureBuildScript = Join-Path $fixtureTools 'BuildCore.ps1'
$fixtureOutput = Join-Path $fixtureCore 'DratCore.cpd'
$powerShellPath = (Get-Process -Id $PID).Path

function Assert-BuildCoreTest {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Get-FileFingerprint {
    param([string]$Path)

    $bytes = [System.IO.File]::ReadAllBytes($Path)
    return [System.Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($bytes))
}

function Invoke-FixtureBuild {
    param([string[]]$Arguments = @())

    $output = & $script:powerShellPath -NoProfile -File $script:fixtureBuildScript @Arguments 2>&1
    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output = (($output | ForEach-Object { $_.ToString() }) -join ' ')
    }
}

function Assert-NoTemporaryBundles {
    $temporaryFiles = @(Get-ChildItem -LiteralPath $script:fixtureCore -File -Filter '.DratCore.cpd.*.tmp' -ErrorAction SilentlyContinue)
    Assert-BuildCoreTest -Condition ($temporaryFiles.Count -eq 0) -Message 'BuildCore left a temporary bundle behind.'
}

try {
    New-Item -ItemType Directory -Path $fixtureTools -Force | Out-Null
    New-Item -ItemType Directory -Path $fixtureSource -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $repositoryRoot 'Tools\BuildCore.ps1') -Destination $fixtureBuildScript
    foreach ($sourceFile in Get-ChildItem -LiteralPath (Join-Path $repositoryRoot 'Core\Src') -File) {
        Copy-Item -LiteralPath $sourceFile.FullName -Destination (Join-Path $fixtureSource $sourceFile.Name)
    }

    [System.IO.File]::WriteAllText($fixtureOutput, 'STALE CORE')
    $successfulBuild = Invoke-FixtureBuild
    Assert-BuildCoreTest -Condition ($successfulBuild.ExitCode -eq 0) -Message "Successful generation failed: $($successfulBuild.Output)"
    $expectedBundle = [System.IO.File]::ReadAllText((Join-Path $repositoryRoot 'Core\DratCore.cpd'))
    $generatedBundle = [System.IO.File]::ReadAllText($fixtureOutput)
    Assert-BuildCoreTest -Condition ($generatedBundle -ceq $expectedBundle) -Message 'Successful generation did not produce the deterministic maintained bundle.'
    Assert-NoTemporaryBundles

    $beforeCheckFingerprint = Get-FileFingerprint -Path $fixtureOutput
    $beforeCheckWriteTime = [System.IO.File]::GetLastWriteTimeUtc($fixtureOutput)
    $currentCheck = Invoke-FixtureBuild -Arguments @('-Check')
    Assert-BuildCoreTest -Condition ($currentCheck.ExitCode -eq 0) -Message "Current-bundle check failed: $($currentCheck.Output)"
    Assert-BuildCoreTest -Condition ((Get-FileFingerprint -Path $fixtureOutput) -ceq $beforeCheckFingerprint) -Message 'BuildCore -Check modified the generated bundle content.'
    Assert-BuildCoreTest -Condition ([System.IO.File]::GetLastWriteTimeUtc($fixtureOutput) -eq $beforeCheckWriteTime) -Message 'BuildCore -Check modified the generated bundle timestamp.'
    Assert-NoTemporaryBundles

    $plottingPath = Join-Path $fixtureSource 'Plotting.cpd'
    $plottingBytes = [System.IO.File]::ReadAllBytes($plottingPath)
    [System.IO.File]::AppendAllText($plottingPath, "`r`n'<!-- stale-check fixture -->")
    $beforeStaleCheck = Get-FileFingerprint -Path $fixtureOutput
    $staleCheck = Invoke-FixtureBuild -Arguments @('-Check')
    Assert-BuildCoreTest -Condition ($staleCheck.ExitCode -ne 0) -Message 'BuildCore -Check accepted a stale generated bundle.'
    Assert-BuildCoreTest -Condition ((Get-FileFingerprint -Path $fixtureOutput) -ceq $beforeStaleCheck) -Message 'A stale -Check modified the maintained output.'
    [System.IO.File]::WriteAllBytes($plottingPath, $plottingBytes)
    Assert-NoTemporaryBundles

    $missingPath = Join-Path $fixtureSource 'Plotting.cpd.missing'
    Move-Item -LiteralPath $plottingPath -Destination $missingPath
    $beforeMissingModule = Get-FileFingerprint -Path $fixtureOutput
    $missingModuleBuild = Invoke-FixtureBuild
    Assert-BuildCoreTest -Condition ($missingModuleBuild.ExitCode -ne 0) -Message 'BuildCore accepted a missing source module.'
    Assert-BuildCoreTest -Condition ((Get-FileFingerprint -Path $fixtureOutput) -ceq $beforeMissingModule) -Message 'A missing source module changed the maintained output.'
    Move-Item -LiteralPath $missingPath -Destination $plottingPath
    Assert-NoTemporaryBundles

    [System.IO.File]::AppendAllText($plottingPath, "`r`n'<!-- replacement-failure fixture -->")
    $beforeReplacementFailure = Get-FileFingerprint -Path $fixtureOutput
    $outputLock = [System.IO.File]::Open($fixtureOutput, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    try {
        $failedReplacement = Invoke-FixtureBuild
    }
    finally {
        $outputLock.Dispose()
    }
    Assert-BuildCoreTest -Condition ($failedReplacement.ExitCode -ne 0) -Message 'BuildCore unexpectedly replaced an exclusively locked output.'
    Assert-BuildCoreTest -Condition ((Get-FileFingerprint -Path $fixtureOutput) -ceq $beforeReplacementFailure) -Message 'A failed atomic replacement changed the prior maintained output.'
    Assert-NoTemporaryBundles

    Write-Output '[PASS] Atomic Core generation, read-only checking, failure preservation, and temporary cleanup.'
}
finally {
    if ($fixtureRoot.StartsWith($temporaryBase, [System.StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $fixtureRoot)) {
        Remove-Item -LiteralPath $fixtureRoot -Recurse -Force
    }
}
