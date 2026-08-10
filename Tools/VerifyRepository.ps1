[CmdletBinding()]
param(
    [string]$CalcPadCli,
    [switch]$SkipCalcPad,
    [switch]$KeepOutput
)

$repositoryRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot)).TrimEnd('\', '/')
$repositoryPrefix = $repositoryRoot + [System.IO.Path]::DirectorySeparatorChar
$verificationFailures = [System.Collections.Generic.List[string]]::new()
$includeRecords = [System.Collections.Generic.List[object]]::new()
$calcPadOutputRoot = $null

function Add-VerificationFailure {
    param([string]$Message)

    $script:verificationFailures.Add($Message)
}

function Get-RepositoryRelativePath {
    param([string]$Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if ($fullPath.StartsWith($script:repositoryPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $fullPath.Substring($script:repositoryPrefix.Length)
    }

    return $fullPath
}

function Test-RepositoryPath {
    param([string]$Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    return $fullPath.StartsWith($script:repositoryPrefix, [System.StringComparison]::OrdinalIgnoreCase)
}

function Test-ExactPathCasing {
    param([string]$Path)

    if (-not (Test-RepositoryPath -Path $Path)) {
        return $false
    }

    $relativePath = Get-RepositoryRelativePath -Path $Path
    $segments = $relativePath -split '[\\/]'
    $currentPath = $script:repositoryRoot

    foreach ($segment in $segments) {
        $exactMatch = Get-ChildItem -LiteralPath $currentPath -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -ceq $segment } |
            Select-Object -First 1

        if ($null -eq $exactMatch) {
            return $false
        }

        $currentPath = $exactMatch.FullName
    }

    return $true
}

function Convert-VersionToApi {
    param([string]$Version)

    $parts = $Version.Split('.')
    if ($parts.Count -ne 3) {
        return $null
    }

    return ([int]$parts[0] * 10000) + ([int]$parts[1] * 100) + [int]$parts[2]
}

function Test-CoreBundle {
    $buildScript = Join-Path $script:repositoryRoot 'Tools\BuildCore.ps1'
    if (-not (Test-Path -LiteralPath $buildScript -PathType Leaf)) {
        Add-VerificationFailure -Message 'Tools\BuildCore.ps1 is missing.'
        return
    }

    $powerShellPath = (Get-Process -Id $PID).Path
    $buildOutput = & $powerShellPath -NoProfile -File $buildScript -Check 2>&1
    $buildExitCode = $LASTEXITCODE

    if ($buildExitCode -ne 0) {
        Add-VerificationFailure -Message ('Generated Core check failed: ' + (($buildOutput | ForEach-Object { $_.ToString() }) -join ' '))
        return
    }

    Write-Output '[PASS] Generated Core bundle is current.'
}

function Test-ApiVersions {
    $startingFailureCount = $script:verificationFailures.Count
    $manifestPath = Join-Path $script:repositoryRoot 'Core\Src\CoreManifest.cpd'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        Add-VerificationFailure -Message 'Core\Src\CoreManifest.cpd is missing.'
        return
    }

    $manifestText = [System.IO.File]::ReadAllText($manifestPath)
    $apiValues = @{}

    foreach ($match in [regex]::Matches($manifestText, '(?m)^(?<name>DRAT_[A-Z_]+_API)\s*=\s*(?<value>\d+)\s*$')) {
        $apiValues[$match.Groups['name'].Value] = [int]$match.Groups['value'].Value
    }

    $coreVersionMatch = [regex]::Match($manifestText, '(?m)^#def\s+DRATCoreVersion\$\s*=\s*(?<version>\d+\.\d+\.\d+)\s*$')
    if (-not $coreVersionMatch.Success) {
        Add-VerificationFailure -Message 'CoreManifest.cpd does not declare a numeric DRATCoreVersion$.'
    }
    elseif ($apiValues.ContainsKey('DRAT_CORE_API')) {
        $expectedCoreApi = Convert-VersionToApi -Version $coreVersionMatch.Groups['version'].Value
        if ($apiValues['DRAT_CORE_API'] -ne $expectedCoreApi) {
            Add-VerificationFailure -Message "DRAT_CORE_API does not match DRATCoreVersion$ $($coreVersionMatch.Groups['version'].Value)."
        }
    }
    else {
        Add-VerificationFailure -Message 'CoreManifest.cpd does not declare DRAT_CORE_API.'
    }

    $componentApis = [ordered]@{
        'Definitions.cpd' = 'DRAT_DEFINITIONS_API'
        'DataWrapper.cpd' = 'DRAT_DATA_WRAPPER_API'
        'Checks.cpd' = 'DRAT_CHECKS_API'
        'Database.cpd' = 'DRAT_DATABASE_API'
        'Validation.cpd' = 'DRAT_VALIDATION_API'
        'CalculationStatus.cpd' = 'DRAT_CALCULATION_STATUS_API'
        'Plotting.cpd' = 'DRAT_PLOTTING_API'
    }

    foreach ($componentName in $componentApis.Keys) {
        $componentPath = Join-Path $script:repositoryRoot "Core\Src\$componentName"
        if (-not (Test-Path -LiteralPath $componentPath -PathType Leaf)) {
            Add-VerificationFailure -Message "Core\Src\$componentName is missing."
            continue
        }

        $componentText = [System.IO.File]::ReadAllText($componentPath)
        $versionMatch = [regex]::Match($componentText, '(?:Version\s+|Wrapper\s+)(?<version>\d+\.\d+\.\d+)')
        $apiName = $componentApis[$componentName]

        if (-not $versionMatch.Success) {
            Add-VerificationFailure -Message "$componentName does not contain a numeric Version declaration."
            continue
        }

        if (-not $apiValues.ContainsKey($apiName)) {
            Add-VerificationFailure -Message "CoreManifest.cpd does not declare $apiName."
            continue
        }

        $expectedApi = Convert-VersionToApi -Version $versionMatch.Groups['version'].Value
        if ($apiValues[$apiName] -ne $expectedApi) {
            Add-VerificationFailure -Message "$apiName does not match $componentName version $($versionMatch.Groups['version'].Value)."
        }
    }

    if ($script:verificationFailures.Count -eq $startingFailureCount) {
        Write-Output "[PASS] Core and component API declarations are consistent ($($componentApis.Count + 1) checked)."
    }
}

function Test-DistributionTooling {
    $distributionTestPath = Join-Path $script:repositoryRoot 'Tests\Distribution\DISTRIBUTION_TEST.ps1'
    if (-not (Test-Path -LiteralPath $distributionTestPath -PathType Leaf)) {
        Add-VerificationFailure -Message 'Tests\Distribution\DISTRIBUTION_TEST.ps1 is missing.'
        return
    }

    $powerShellPath = (Get-Process -Id $PID).Path
    $distributionArguments = @('-NoProfile', '-File', $distributionTestPath)
    if (-not $script:SkipCalcPad) {
        $resolvedCli = Resolve-CalcPadCli
        if (-not [string]::IsNullOrWhiteSpace($resolvedCli) -and (Test-Path -LiteralPath $resolvedCli -PathType Leaf)) {
            $distributionArguments += @('-CalcPadCli', $resolvedCli)
        }
    }
    $testOutput = & $powerShellPath @distributionArguments 2>&1
    $testExitCode = $LASTEXITCODE
    if ($testExitCode -ne 0) {
        Add-VerificationFailure -Message ('Distribution verification failed: ' + (($testOutput | ForEach-Object { $_.ToString() }) -join ' '))
        return
    }

    Write-Output '[PASS] Distribution build, install, update, and portable-project workflow.'
}

function Test-IncludeGraph {
    $startingFailureCount = $script:verificationFailures.Count
    $artifactsPrefix = (Join-Path $script:repositoryRoot 'artifacts').TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    $sourceFiles = Get-ChildItem -LiteralPath $script:repositoryRoot -Recurse -File -Filter '*.cpd' |
        Where-Object { -not $_.FullName.StartsWith($artifactsPrefix, [System.StringComparison]::OrdinalIgnoreCase) } |
        Sort-Object FullName

    foreach ($sourceFile in $sourceFiles) {
        $lines = [System.IO.File]::ReadAllLines($sourceFile.FullName)
        for ($lineIndex = 0; $lineIndex -lt $lines.Count; $lineIndex++) {
            $includeMatch = [regex]::Match($lines[$lineIndex], '^\s*#include\s+(?<path>.+?)\s*$')
            if (-not $includeMatch.Success) {
                continue
            }

            $includePath = $includeMatch.Groups['path'].Value.Trim().Trim('"')
            $sourceRelative = Get-RepositoryRelativePath -Path $sourceFile.FullName
            $location = "${sourceRelative}:$($lineIndex + 1)"

            if ([System.IO.Path]::IsPathRooted($includePath) -or $includePath -match '^%[^%]+%' -or $includePath -match '^[\\/]{1,2}') {
                Add-VerificationFailure -Message "$location uses an absolute include: $includePath"
                continue
            }

            $targetPath = [System.IO.Path]::GetFullPath((Join-Path $sourceFile.DirectoryName $includePath))
            if (-not (Test-RepositoryPath -Path $targetPath)) {
                Add-VerificationFailure -Message "$location resolves outside the repository: $includePath"
                continue
            }

            if (-not (Test-Path -LiteralPath $targetPath -PathType Leaf)) {
                Add-VerificationFailure -Message "$location includes a missing file: $includePath"
                continue
            }

            if (-not (Test-ExactPathCasing -Path $targetPath)) {
                Add-VerificationFailure -Message "$location does not match the exact path casing: $includePath"
                continue
            }

            $script:includeRecords.Add([pscustomobject]@{
                Source = $sourceFile.FullName
                SourceRelative = $sourceRelative
                Line = $lineIndex + 1
                Include = $includePath
                Target = $targetPath
                TargetRelative = Get-RepositoryRelativePath -Path $targetPath
            })
        }
    }

    foreach ($record in $script:includeRecords) {
        $targetText = [System.IO.File]::ReadAllText($record.Target)
        if ([regex]::IsMatch($targetText, '(?m)^\s*#include\s+')) {
            Add-VerificationFailure -Message "$($record.SourceRelative):$($record.Line) creates a nested include through $($record.TargetRelative)."
        }
    }

    if ($script:verificationFailures.Count -eq $startingFailureCount) {
        Write-Output "[PASS] Include graph is relative, direct, exact-case, and complete ($($script:includeRecords.Count) includes)."
    }
}

function Test-GitWhitespace {
    if ($null -eq (Get-Command git -ErrorAction SilentlyContinue)) {
        Add-VerificationFailure -Message 'Git is unavailable; whitespace validation could not run.'
        return
    }

    $safeDirectory = $script:repositoryRoot.Replace('\', '/')
    Push-Location -LiteralPath $script:repositoryRoot
    try {
        $gitOutput = & git -c "safe.directory=$safeDirectory" diff --check 2>&1
        $gitExitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
    if ($gitExitCode -ne 0) {
        Add-VerificationFailure -Message ('git diff --check failed: ' + (($gitOutput | ForEach-Object { $_.ToString() }) -join ' '))
        return
    }

    Write-Output '[PASS] Working-tree diff contains no whitespace errors.'
}

function Resolve-CalcPadCli {
    if (-not [string]::IsNullOrWhiteSpace($script:CalcPadCli)) {
        return [System.IO.Path]::GetFullPath($script:CalcPadCli)
    }

    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        return Join-Path $env:LOCALAPPDATA 'Programs\CalcpadCE\cli\Cli.exe'
    }

    return $null
}

function Test-CalcPadWorksheets {
    $startingFailureCount = $script:verificationFailures.Count
    $resolvedCli = Resolve-CalcPadCli
    if ([string]::IsNullOrWhiteSpace($resolvedCli) -or -not (Test-Path -LiteralPath $resolvedCli -PathType Leaf)) {
        Add-VerificationFailure -Message 'CalcPad CE CLI was not found. Pass -CalcPadCli or use -SkipCalcPad for static checks only.'
        return
    }

    $script:calcPadOutputRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('drat-calcpad-verify-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $script:calcPadOutputRoot | Out-Null

    $worksheetFiles = [System.Collections.Generic.List[object]]::new()
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Tests') -Recurse -File -Filter '*.cpd' | Sort-Object FullName) {
        $worksheetFiles.Add([pscustomobject]@{ Kind = 'test'; File = $file })
    }
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Examples') -Recurse -File -Filter '*.cpd' | Sort-Object FullName) {
        $worksheetFiles.Add([pscustomobject]@{ Kind = 'example'; File = $file })
    }
    $worksheetFiles.Add([pscustomobject]@{
        Kind = 'template'
        File = Get-Item -LiteralPath (Join-Path $script:repositoryRoot 'Templates\EngineeringCalculationTemplate.cpd')
    })

    $assertionCount = 0
    foreach ($worksheet in $worksheetFiles) {
        $relativePath = Get-RepositoryRelativePath -Path $worksheet.File.FullName
        $safeName = [regex]::Replace("$($worksheet.Kind)-$relativePath", '[^A-Za-z0-9_.-]', '_')
        $outputPath = Join-Path $script:calcPadOutputRoot ([System.IO.Path]::ChangeExtension($safeName, '.html'))

        try {
            & $resolvedCli $worksheet.File.FullName $outputPath -s
            $calcPadExitCode = $LASTEXITCODE
        }
        catch {
            Add-VerificationFailure -Message "$relativePath could not start CalcPad CE: $($_.Exception.Message)"
            continue
        }
        if ($calcPadExitCode -ne 0) {
            Add-VerificationFailure -Message "$relativePath returned CalcPad CLI exit code $calcPadExitCode."
            continue
        }

        if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
            Add-VerificationFailure -Message "$relativePath did not generate HTML output."
            continue
        }

        $html = [System.IO.File]::ReadAllText($outputPath)
        $errorPatterns = @(
            '<span class="err">Error in',
            'Undefined variable or units',
            'Invalid syntax:',
            'Parser error',
            'ζMAT_'
        )
        $matchedError = $errorPatterns | Where-Object { $html.Contains($_) } | Select-Object -First 1
        if ($null -ne $matchedError) {
            Add-VerificationFailure -Message "$relativePath contains a CalcPad parser or runtime error. Output: $outputPath"
            continue
        }

        $sourceText = [System.IO.File]::ReadAllText($worksheet.File.FullName)
        if ([regex]::IsMatch($sourceText, '(?m)^\s*all_tests\s*=')) {
            $assertionCount++
            $resultMatches = [regex]::Matches($html, '(?s)<var>all</var><sub>tests</sub>.*?</span></p>')
            if ($resultMatches.Count -eq 0) {
                Add-VerificationFailure -Message "$relativePath defines all_tests but does not render its result."
                continue
            }

            $resultHtml = $resultMatches[$resultMatches.Count - 1].Value
            $resultText = [System.Net.WebUtility]::HtmlDecode([regex]::Replace($resultHtml, '<[^>]+>', ' '))
            $resultText = [regex]::Replace($resultText, '\s+', ' ').Trim()
            if ($resultText -notmatch '=\s*1\s*$') {
                Add-VerificationFailure -Message "$relativePath failed: $resultText"
            }
        }
    }

    if ($script:verificationFailures.Count -eq $startingFailureCount) {
        Write-Output "[PASS] CalcPad generated $($worksheetFiles.Count) worksheets without parser/runtime errors; $assertionCount all_tests results passed."
    }
}

function Remove-CalcPadOutput {
    if ([string]::IsNullOrWhiteSpace($script:calcPadOutputRoot) -or -not (Test-Path -LiteralPath $script:calcPadOutputRoot)) {
        return
    }

    $tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    $outputRoot = [System.IO.Path]::GetFullPath($script:calcPadOutputRoot)
    $outputLeaf = Split-Path -Leaf $outputRoot
    $safeToRemove = $outputRoot.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase) -and $outputLeaf.StartsWith('drat-calcpad-verify-', [System.StringComparison]::Ordinal)

    if (-not $safeToRemove) {
        Add-VerificationFailure -Message "Refusing to remove unexpected output directory: $outputRoot"
        return
    }

    Remove-Item -LiteralPath $outputRoot -Recurse -Force
}

Write-Output "Verifying $repositoryRoot"
Test-CoreBundle
Test-ApiVersions
Test-IncludeGraph
Test-GitWhitespace
Test-DistributionTooling

if ($SkipCalcPad) {
    Write-Output '[SKIP] CalcPad worksheet execution was skipped.'
}
else {
    Test-CalcPadWorksheets
}

if ($verificationFailures.Count -eq 0) {
    if ($KeepOutput -and -not [string]::IsNullOrWhiteSpace($calcPadOutputRoot)) {
        Write-Output "CalcPad output retained at: $calcPadOutputRoot"
    }
    elseif (-not $SkipCalcPad) {
        Remove-CalcPadOutput
    }
}

if ($verificationFailures.Count -gt 0) {
    Write-Output ''
    Write-Output "Verification failed with $($verificationFailures.Count) issue(s):"
    foreach ($failure in $verificationFailures) {
        Write-Output "- $failure"
    }
    if (-not [string]::IsNullOrWhiteSpace($calcPadOutputRoot) -and (Test-Path -LiteralPath $calcPadOutputRoot)) {
        Write-Output "CalcPad output retained at: $calcPadOutputRoot"
    }
    exit 1
}

Write-Output ''
Write-Output 'Repository verification passed.'
exit 0
