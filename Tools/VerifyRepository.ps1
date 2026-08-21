[CmdletBinding()]
param(
    [string]$CalcPadCli,
    [string]$PythonPath,
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
    $startingFailureCount = $script:verificationFailures.Count
    $buildScript = Join-Path $script:repositoryRoot 'Tools\BuildCore.ps1'
    $buildTest = Join-Path $script:repositoryRoot 'Tests\Tooling\BuildCoreTest.ps1'
    foreach ($requiredPath in @($buildScript, $buildTest)) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            Add-VerificationFailure -Message "Core build tooling is missing: $(Get-RepositoryRelativePath -Path $requiredPath)"
        }
    }
    if ($script:verificationFailures.Count -ne $startingFailureCount) {
        return
    }

    $powerShellPath = (Get-Process -Id $PID).Path
    $buildOutput = & $powerShellPath -NoProfile -File $buildScript -Check 2>&1
    $buildExitCode = $LASTEXITCODE

    if ($buildExitCode -ne 0) {
        Add-VerificationFailure -Message ('Generated Core check failed: ' + (($buildOutput | ForEach-Object { $_.ToString() }) -join ' '))
        return
    }

    $testOutput = & $powerShellPath -NoProfile -File $buildTest 2>&1
    if ($LASTEXITCODE -ne 0) {
        Add-VerificationFailure -Message ('Atomic Core build tests failed: ' + (($testOutput | ForEach-Object { $_.ToString() }) -join ' '))
        return
    }

    Write-Output '[PASS] Generated Core bundle is current.'
    Write-Output '[PASS] Core generation is atomic, failure-safe, and regression tested.'
}

function Resolve-PythonExecutable {
    if (-not [string]::IsNullOrWhiteSpace($script:PythonPath)) {
        $resolvedPath = [System.IO.Path]::GetFullPath($script:PythonPath)
        if (Test-Path -LiteralPath $resolvedPath -PathType Leaf) {
            return $resolvedPath
        }
        return $null
    }

    foreach ($commandName in @('python', 'python3')) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $command -and -not [string]::IsNullOrWhiteSpace($command.Source)) {
            return $command.Source
        }
    }

    return $null
}

function Test-ThermophysicalGenerator {
    $startingFailureCount = $script:verificationFailures.Count
    $python = Resolve-PythonExecutable
    if ([string]::IsNullOrWhiteSpace($python)) {
        Add-VerificationFailure -Message 'Python 3 was not found. Pass -PythonPath to verify the generated thermophysical library.'
        return
    }

    $generatorPath = Join-Path $script:repositoryRoot 'Tools\GenerateThermophysicalLibrary.py'
    $sourcePath = Join-Path $script:repositoryRoot 'Data\Sources\Thermophysical\ThermophysicalProperties.json'
    $outputPath = Join-Path $script:repositoryRoot 'Libraries\Thermophysical\ThermophysicalProperties.cpd'
    $testPath = Join-Path $script:repositoryRoot 'Tests\Tooling\ThermophysicalGeneratorTest.py'
    foreach ($requiredPath in @($generatorPath, $sourcePath, $outputPath, $testPath)) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            Add-VerificationFailure -Message "Thermophysical generation input is missing: $(Get-RepositoryRelativePath -Path $requiredPath)"
        }
    }
    if ($script:verificationFailures.Count -ne $startingFailureCount) {
        return
    }

    $generatorOutput = & $python $generatorPath $sourcePath $outputPath --check 2>&1
    if ($LASTEXITCODE -ne 0) {
        Add-VerificationFailure -Message ('Thermophysical generated-library check failed: ' + (($generatorOutput | ForEach-Object { $_.ToString() }) -join ' '))
        return
    }
    $testOutput = & $python $testPath 2>&1
    if ($LASTEXITCODE -ne 0) {
        Add-VerificationFailure -Message ('Thermophysical generator schema tests failed: ' + (($testOutput | ForEach-Object { $_.ToString() }) -join ' '))
        return
    }

    Write-Output '[PASS] Thermophysical raw-data schema, generator regressions, and committed CalcPad library are current.'
}

function Test-AiscGenerators {
    $startingFailureCount = $script:verificationFailures.Count
    $python = Resolve-PythonExecutable
    if ([string]::IsNullOrWhiteSpace($python)) {
        Add-VerificationFailure -Message 'Python 3 was not found. Pass -PythonPath to verify the AISC dataset generators.'
        return
    }

    $sourcePath = Join-Path $script:repositoryRoot 'Data\Sources\AiscShapesV16\DratStructuralSectionsSource.xlsx'
    $testPath = Join-Path $script:repositoryRoot 'Tests\Tooling\AiscGeneratorTest.py'
    $checks = @(
        @{ Generator = 'Tools\GenerateAiscWLibrary.py'; Output = 'Libraries\Steel\StructuralSections.cpd' },
        @{ Generator = 'Tools\GenerateAiscHssLibrary.py'; Output = 'Libraries\Steel\AiscHssSections.cpd' },
        @{ Generator = 'Tools\GenerateAiscChannelLibrary.py'; Output = 'Libraries\Steel\AiscChannelSections.cpd' },
        @{ Generator = 'Tools\GenerateAiscAngleLibrary.py'; Output = 'Libraries\Steel\AiscAngleSections.cpd' }
    )
    foreach ($requiredPath in @($sourcePath, $testPath)) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            Add-VerificationFailure -Message "AISC generation input is missing: $(Get-RepositoryRelativePath -Path $requiredPath)"
        }
    }
    foreach ($check in $checks) {
        foreach ($relativePath in @($check.Generator, $check.Output)) {
            $requiredPath = Join-Path $script:repositoryRoot $relativePath
            if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
                Add-VerificationFailure -Message "AISC generation input is missing: $relativePath"
            }
        }
    }
    if ($script:verificationFailures.Count -ne $startingFailureCount) {
        return
    }

    foreach ($check in $checks) {
        $generatorPath = Join-Path $script:repositoryRoot $check.Generator
        $outputPath = Join-Path $script:repositoryRoot $check.Output
        $generatorOutput = & $python $generatorPath $sourcePath $outputPath --check 2>&1
        if ($LASTEXITCODE -ne 0) {
            Add-VerificationFailure -Message ('AISC generated-library check failed: ' + (($generatorOutput | ForEach-Object { $_.ToString() }) -join ' '))
            return
        }
    }
    $testOutput = & $python $testPath 2>&1
    if ($LASTEXITCODE -ne 0) {
        Add-VerificationFailure -Message ('AISC generator schema tests failed: ' + (($testOutput | ForEach-Object { $_.ToString() }) -join ' '))
        return
    }

    Write-Output '[PASS] Curated AISC source schema, stable IDs, deterministic generators, and committed CalcPad libraries are current.'
}

function Test-EngineeringMaterialsSource {
    $python = Resolve-PythonExecutable
    if ([string]::IsNullOrWhiteSpace($python)) {
        Add-VerificationFailure -Message 'Python 3 was not found. Pass -PythonPath to verify the Engineering Materials source workbook.'
        return
    }

    $sourcePath = Join-Path $script:repositoryRoot 'Data\Sources\EngineeringMaterials\EngineeringMaterialsDatabase.xlsx'
    $validatorPath = Join-Path $script:repositoryRoot 'Tools\ValidateEngineeringMaterialsSource.py'
    $testPath = Join-Path $script:repositoryRoot 'Tests\Tooling\EngineeringMaterialsSourceTest.py'
    foreach ($requiredPath in @($sourcePath, $validatorPath, $testPath)) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            Add-VerificationFailure -Message "Engineering Materials source-validation input is missing: $(Get-RepositoryRelativePath -Path $requiredPath)"
        }
    }
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf) -or -not (Test-Path -LiteralPath $validatorPath -PathType Leaf) -or -not (Test-Path -LiteralPath $testPath -PathType Leaf)) {
        return
    }

    $validationOutput = & $python $validatorPath $sourcePath 2>&1
    if ($LASTEXITCODE -ne 0) {
        Add-VerificationFailure -Message ('Engineering Materials source validation failed: ' + (($validationOutput | ForEach-Object { $_.ToString() }) -join ' '))
        return
    }
    $testOutput = & $python $testPath 2>&1
    if ($LASTEXITCODE -ne 0) {
        Add-VerificationFailure -Message ('Engineering Materials source tests failed: ' + (($testOutput | ForEach-Object { $_.ToString() }) -join ' '))
        return
    }

    Write-Output '[PASS] Engineering Materials schema, IDs, numeric types, source links, derived values, and CPD export are consistent.'
}

function Test-DatasetSourceLayout {
    $requirementsPath = Join-Path $script:repositoryRoot 'requirements-generators.txt'
    $noticesPath = Join-Path $script:repositoryRoot 'THIRD-PARTY-NOTICES.md'
    $auditPath = Join-Path $script:repositoryRoot 'docs\DataProvenance.md'
    foreach ($requiredPath in @($requirementsPath, $noticesPath, $auditPath)) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            Add-VerificationFailure -Message "Dataset provenance file is missing: $(Get-RepositoryRelativePath -Path $requiredPath)"
        }
    }

    if (Test-Path -LiteralPath $requirementsPath -PathType Leaf) {
        $requirements = [System.IO.File]::ReadAllText($requirementsPath)
        foreach ($dependency in @('pandas', 'openpyxl')) {
            if ($requirements -notmatch "(?m)^$dependency[<>=]") {
                Add-VerificationFailure -Message "requirements-generators.txt does not constrain $dependency."
            }
        }
    }

    $rawRuntimeInputs = @(
        Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Libraries') -File -Recurse |
            Where-Object Extension -In @('.xlsx', '.xls', '.json')
    )
    foreach ($file in $rawRuntimeInputs) {
        Add-VerificationFailure -Message "Raw generator input must be outside Libraries: $(Get-RepositoryRelativePath -Path $file.FullName)"
    }

    $unexpectedAiscWorkbooks = @(
        Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Data\Sources\AiscShapesV16') -File -Recurse |
            Where-Object { $_.Extension -In @('.xlsx', '.xls') -and $_.Name -cne 'DratStructuralSectionsSource.xlsx' }
    )
    foreach ($file in $unexpectedAiscWorkbooks) {
        Add-VerificationFailure -Message "Only the curated DRAT structural-section workbook may be committed: $(Get-RepositoryRelativePath -Path $file.FullName)"
    }

    if ($rawRuntimeInputs.Count -eq 0 -and $unexpectedAiscWorkbooks.Count -eq 0) {
        Write-Output '[PASS] Raw dataset inputs are separated from runtime libraries; the official AISC workbook remains uncommitted.'
    }
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
        'Stylesheet.cpd' = 'DRAT_STYLESHEET_API'
        'Definitions.cpd' = 'DRAT_DEFINITIONS_API'
        'DataWrapper.cpd' = 'DRAT_DATA_WRAPPER_API'
        'Checks.cpd' = 'DRAT_CHECKS_API'
        'Database.cpd' = 'DRAT_DATABASE_API'
        'Validation.cpd' = 'DRAT_VALIDATION_API'
        'CheckRegistry.cpd' = 'DRAT_CHECK_REGISTRY_API'
        'CalculationStatus.cpd' = 'DRAT_CALCULATION_STATUS_API'
        'Reporting.cpd' = 'DRAT_REPORTING_API'
        'Authoring.cpd' = 'DRAT_AUTHORING_API'
        'ReviewSummary.cpd' = 'DRAT_REVIEW_SUMMARY_API'
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

    $coreApiDocumentationPath = Join-Path $script:repositoryRoot 'docs\CoreApi.md'
    if (-not (Test-Path -LiteralPath $coreApiDocumentationPath -PathType Leaf)) {
        Add-VerificationFailure -Message 'docs\CoreApi.md is missing.'
    }
    else {
        $coreApiDocumentation = [System.IO.File]::ReadAllText($coreApiDocumentationPath)
        foreach ($apiName in $apiValues.Keys | Sort-Object) {
            $documentedApiMatch = [regex]::Match(
                $coreApiDocumentation,
                '(?m)^\|\s*`' + [regex]::Escape($apiName) + '`\s*\|\s*`(?<value>\d+)`\s*\|'
            )
            if (-not $documentedApiMatch.Success) {
                Add-VerificationFailure -Message "docs\CoreApi.md does not document $apiName in the compatibility table."
            }
            elseif ([int]$documentedApiMatch.Groups['value'].Value -ne $apiValues[$apiName]) {
                Add-VerificationFailure -Message "docs\CoreApi.md lists $apiName as $($documentedApiMatch.Groups['value'].Value), but CoreManifest.cpd declares $($apiValues[$apiName])."
            }
        }
    }

    if ($script:verificationFailures.Count -eq $startingFailureCount) {
        Write-Output "[PASS] Core and component API declarations are consistent ($($componentApis.Count + 1) checked)."
    }
}

function Test-DistributionTooling {
    $distributionPassMarker = '[PASS] Distribution archive, declaration-backed metadata and hashes, overlap rejection, retained update, stable Current path, and moved current-version projects.'
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
    $testOutputText = @($testOutput | ForEach-Object { $_.ToString() })
    if (-not ($testOutputText -contains $distributionPassMarker)) {
        Add-VerificationFailure -Message 'Distribution verification exited successfully without its final PASS marker.'
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

function Test-ArtifactConventions {
    $startingFailureCount = $script:verificationFailures.Count
    $pascalCaseName = '^[A-Z][A-Za-z0-9]*\.cpd$'

    $artifactRoots = @('Examples', 'Templates', 'Tests')
    foreach ($artifactRoot in $artifactRoots) {
        $rootPath = Join-Path $script:repositoryRoot $artifactRoot
        foreach ($file in Get-ChildItem -LiteralPath $rootPath -Recurse -File -Filter '*.cpd' | Sort-Object FullName) {
            if ($file.Name -cnotmatch $pascalCaseName) {
                Add-VerificationFailure -Message "$(Get-RepositoryRelativePath -Path $file.FullName) does not use a PascalCase worksheet filename."
            }
        }
    }

    $exampleRequirements = [ordered]@{
        'Markdown mode' = '(?m)^#md on\s*$'
        'Organization' = '(?m)^#def\s+Organization\$\s*=\s*\S'
        'Client' = '(?m)^#def\s+Client\$\s*=\s*\S'
        'Project' = '(?m)^#def\s+Project\$\s*=\s*\S'
        'Title' = '(?m)^#def\s+Title\$\s*=\s*\S'
        'Purpose' = '(?m)^#def\s+Purpose\$\s*=\s*\S'
        'Scope' = '(?m)^#def\s+Scope\$\s*=\s*\S'
        'Calculation number' = '(?m)^#def\s+Calculation\$\s*=\s*\S'
        'Standard header' = '(?m)^CreateHeader\$\s*$'
        'Standard title' = '(?m)^CreateTitle\$\s*$'
        'Purpose block' = '(?m)^CreatePurpose\$\s*$'
        'Scope block' = '(?m)^CreateScope\$\s*$'
        'Revision history' = '(?m)^BeginRevisions\$\s*$'
        'Conclusions section' = '(?m)^(?:BeginConclusions\$|"Conclusions|''##\s+Conclusions)\s*$'
    }

    $exampleFiles = Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Examples') -File -Filter '*.cpd' | Sort-Object Name
    foreach ($file in $exampleFiles) {
        $relativePath = Get-RepositoryRelativePath -Path $file.FullName
        $sourceText = [System.IO.File]::ReadAllText($file.FullName)
        foreach ($requirement in $exampleRequirements.GetEnumerator()) {
            if (-not [regex]::IsMatch($sourceText, $requirement.Value)) {
                Add-VerificationFailure -Message "$relativePath is missing its $($requirement.Key)."
            }
        }
        if ([regex]::IsMatch($sourceText, '(?i)<h[1-6](?:\s|>)')) {
            Add-VerificationFailure -Message "$relativePath uses raw HTML headings instead of the standard Markdown report hierarchy."
        }
        if ([regex]::IsMatch($sourceText, '(?m)^#def\s+(?:Title|Purpose|Scope)\$\s*=.*''')) {
            Add-VerificationFailure -Message "$relativePath uses an apostrophe in document text defined by #def; CalcPad may parse the remainder as formatted output."
        }
    }

    $expectedFailureFixtureDirectory = [System.IO.Path]::GetFullPath((Join-Path $script:repositoryRoot 'Tests\FailureModes\Fixtures')).TrimEnd('\', '/')
    $testFiles = Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Tests') -Recurse -File -Filter '*.cpd' | Sort-Object FullName
    foreach ($file in $testFiles) {
        $relativePath = Get-RepositoryRelativePath -Path $file.FullName
        $sourceText = [System.IO.File]::ReadAllText($file.FullName)
        if (-not $sourceText.Contains('TEST PURPOSE:')) {
            Add-VerificationFailure -Message "$relativePath does not state the maintained behavior it verifies."
        }

        $definesAssertion = [regex]::IsMatch($sourceText, '(?m)^\s*all_tests\s*=')
        $isBrowserDiagnostic = $sourceText.Contains('TEST TYPE: BROWSER DIAGNOSTIC')
        $declaresExpectedFailure = $sourceText.Contains('TEST TYPE: EXPECTED FAILURE DIAGNOSTIC')
        $isExpectedFailureFixture = $file.DirectoryName.Equals($expectedFailureFixtureDirectory, [System.StringComparison]::OrdinalIgnoreCase)
        if ($declaresExpectedFailure -and -not $isExpectedFailureFixture) {
            Add-VerificationFailure -Message "$relativePath declares an expected failure outside Tests\FailureModes\Fixtures."
        }
        if ($isExpectedFailureFixture -and -not $declaresExpectedFailure) {
            Add-VerificationFailure -Message "$relativePath is an expected-failure fixture but does not declare TEST TYPE: EXPECTED FAILURE DIAGNOSTIC."
        }
        $isExpectedFailureDiagnostic = $declaresExpectedFailure -and $isExpectedFailureFixture
        if (-not $definesAssertion -and -not $isBrowserDiagnostic -and -not $isExpectedFailureDiagnostic) {
            Add-VerificationFailure -Message "$relativePath must define all_tests or explicitly declare itself a maintained diagnostic."
        }
    }

    $generalTemplate = Join-Path $script:repositoryRoot 'Templates\EngineeringCalculationTemplate.cpd'
    $topLevelTemplates = Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Templates') -File -Filter '*.cpd'
    foreach ($file in $topLevelTemplates) {
        if (-not $file.FullName.Equals($generalTemplate, [System.StringComparison]::OrdinalIgnoreCase)) {
            Add-VerificationFailure -Message "$(Get-RepositoryRelativePath -Path $file.FullName) must be placed in a calculation- or library-specific template category."
        }
    }

    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Templates') -Recurse -File -Filter '*.cpd' | Sort-Object FullName) {
        if (-not [System.IO.File]::ReadAllText($file.FullName).Contains('TEMPLATE PURPOSE:')) {
            Add-VerificationFailure -Message "$(Get-RepositoryRelativePath -Path $file.FullName) does not state its intended use."
        }
    }

    $unresolvedPlaceholders = @(
        'ORGANIZATION NAME',
        'CLIENT NAME',
        'PROJECT NAME',
        'ENGINEERING CALCULATION TITLE',
        'STATE THE PURPOSE AND REQUIRED DECISION.',
        'DEFINE WHAT THE CALCULATION INCLUDES AND EXCLUDES.',
        'CALCULATION NUMBER',
        'PREPARER NAME',
        'YYYY-MM-DD',
        'GOVERNING STANDARD',
        'STANDARD TITLE',
        'EDITION / REVISION',
        'APPLICABLE CLAUSE',
        'PRIMARY DESIGN CRITERION',
        'STATE THE REQUIRED LIMIT OR ACCEPTANCE CONDITION.',
        'STATE THE ENGINEERING ASSUMPTION.',
        'STATE THE BOUND, EXCLUSION, OR CONDITION OF USE.'
    )
    $templatePrefix = (Join-Path $script:repositoryRoot 'Templates').TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    $artifactPrefix = (Join-Path $script:repositoryRoot 'artifacts').TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    foreach ($file in Get-ChildItem -LiteralPath $script:repositoryRoot -Recurse -File -Filter '*.cpd' | Sort-Object FullName) {
        if ($file.FullName.StartsWith($templatePrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
            $file.FullName.StartsWith($artifactPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            continue
        }
        $sourceText = [System.IO.File]::ReadAllText($file.FullName)
        foreach ($placeholder in $unresolvedPlaceholders) {
            if ($sourceText.Contains($placeholder, [System.StringComparison]::Ordinal)) {
                Add-VerificationFailure -Message "$(Get-RepositoryRelativePath -Path $file.FullName) contains unresolved template placeholder '$placeholder'."
            }
        }
    }

    $coverHeadingMacros = @('CreateHeader$', 'CreateTitle$', 'CreatePurpose$', 'CreateScope$', 'BeginRevisions$')
    $explicitHeadingMacros = @('H3$', 'H4$', 'H5$', 'H6$')
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Core\Src') -File -Filter '*.cpd' | Sort-Object Name) {
        $activeMacro = $null
        $lineNumber = 0
        foreach ($line in [System.IO.File]::ReadAllLines($file.FullName)) {
            $lineNumber++
            $definitionMatch = [regex]::Match($line, '^\s*#def\s+(?<name>[A-Za-z][A-Za-z0-9]*\$)')
            if ($definitionMatch.Success) {
                $activeMacro = $definitionMatch.Groups['name'].Value
            }

            if ($null -ne $activeMacro) {
                $trimmedLine = $line.TrimStart()
                $emitsHtmlHeading = [regex]::IsMatch($line, "'<h[1-6](?:\s|>)", [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
                $emitsMarkdownHeading = [regex]::IsMatch($line, "^\s*'#{1,6}\s") -or $trimmedLine.StartsWith('"', [System.StringComparison]::Ordinal)
                $isApprovedHeadingMacro = $activeMacro -in $coverHeadingMacros -or ($file.Name -ceq 'Authoring.cpd' -and $activeMacro -in $explicitHeadingMacros)
                if (($emitsHtmlHeading -or $emitsMarkdownHeading) -and -not $isApprovedHeadingMacro) {
                    Add-VerificationFailure -Message "$(Get-RepositoryRelativePath -Path $file.FullName):$lineNumber emits an H1-H6 heading from non-cover, non-authoring macro $activeMacro. Worksheet source must own the report hierarchy."
                }
            }

            if ([regex]::IsMatch($line, '^\s*#end\s+def\s*$') -or ($definitionMatch.Success -and $line.Contains('='))) {
                $activeMacro = $null
            }
        }
    }

    $singleTextAuthoringMacros = @(
        'H3', 'H4', 'H5', 'H6',
        'SectionIntro', 'CalculationStep',
        'Note', 'Basis', 'Important', 'Warning', 'ErrorMessage',
        'AddBullet', 'AddNumberedItem', 'EmptyState'
    )
    $singleTextAuthoringPattern = '(?<![A-Za-z0-9_])(?<macro>' + (($singleTextAuthoringMacros | ForEach-Object { [regex]::Escape($_) }) -join '|') + ')\$\([^\r\n)]*;[^\r\n)]*\)'
    foreach ($file in Get-ChildItem -LiteralPath $script:repositoryRoot -Recurse -File -Filter '*.cpd' | Sort-Object FullName) {
        $lineNumber = 0
        foreach ($line in [System.IO.File]::ReadAllLines($file.FullName)) {
            $lineNumber++
            $argumentMatch = [regex]::Match($line, $singleTextAuthoringPattern)
            if ($argumentMatch.Success) {
                Add-VerificationFailure -Message "$(Get-RepositoryRelativePath -Path $file.FullName):$lineNumber passes a semicolon to single-text macro $($argumentMatch.Groups['macro'].Value)`$. CalcPad interprets it as another argument."
            }
        }
    }

    $generalTemplateText = [System.IO.File]::ReadAllText($generalTemplate)
    $generalTemplateRequirements = @(
        'BeginReferences$',
        'BeginDesignCriteria$',
        'BeginAssumptions$',
        'BeginLimitations$',
        'BeginVariables$',
        'BeginValidationSummary$',
        'BeginCheckRegistry$',
        'ShowDocumentReviewSummary$',
        'BeginConclusions$'
    )
    foreach ($requiredMacro in $generalTemplateRequirements) {
        if (-not $generalTemplateText.Contains($requiredMacro)) {
            Add-VerificationFailure -Message "Templates\EngineeringCalculationTemplate.cpd is missing required workflow macro $requiredMacro."
        }
    }

    $generalTemplateHeadingRequirements = @(
        'H3$(References)',
        'H4$(Design Criteria)',
        'H4$(Assumptions)',
        'H4$(Applicability and Limitations)',
        'H4$(Reporting Registry Summary)',
        'H3$(Definitions and Variables)',
        'H3$(Conclusions)'
    )
    foreach ($requiredHeading in $generalTemplateHeadingRequirements) {
        if (-not $generalTemplateText.Contains($requiredHeading)) {
            Add-VerificationFailure -Message "Templates\EngineeringCalculationTemplate.cpd is missing caller-owned heading $requiredHeading."
        }
    }

    if ($script:verificationFailures.Count -eq $startingFailureCount) {
        Write-Output "[PASS] Artifact conventions for $($exampleFiles.Count) examples, $($testFiles.Count) tests, and $((Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Templates') -Recurse -File -Filter '*.cpd').Count) templates."
    }
}

function Test-CiConfiguration {
    $startingFailureCount = $script:verificationFailures.Count
    $workflowPath = Join-Path $script:repositoryRoot '.github\workflows\verify.yml'
    if (-not (Test-Path -LiteralPath $workflowPath -PathType Leaf)) {
        Add-VerificationFailure -Message '.github\workflows\verify.yml is missing.'
        return
    }

    $workflowText = [System.IO.File]::ReadAllText($workflowPath)
    $requirements = [ordered]@{
        'pull-request trigger' = '(?m)^\s{2}pull_request:\s*$'
        'push trigger' = '(?m)^\s{2}push:\s*$'
        'manual trigger' = '(?m)^\s{2}workflow_dispatch:\s*$'
        'develop branch' = '(?m)^\s{6}- develop\s*$'
        'main branch' = '(?m)^\s{6}- main\s*$'
        'read-only contents permission' = '(?ms)^permissions:\s*\r?\n\s{2}contents:\s*read\s*$'
        'stable job ID' = '(?m)^\s{2}static-verification:\s*$'
        'stable job name' = '(?m)^\s{4}name:\s*Windows static and distribution verification\s*$'
        'Windows hosted runner' = '(?m)^\s{4}runs-on:\s*windows-latest\s*$'
        'full checkout history' = '(?m)^\s{10}fetch-depth:\s*0\s*$'
        'immutable checkout pin' = '(?m)^\s{8}uses:\s*actions/checkout@[0-9a-f]{40}\s+#\s+v\d+\.\d+\.\d+\s*$'
        'changed-file whitespace check' = 'git diff --check'
        'generator dependency installation' = 'python -m pip install -r requirements-generators\.txt'
        'clean-checkout guard' = 'git status --porcelain --untracked-files=all'
        'hosted verifier command' = '(?m)^\s*\./Tools/VerifyRepository\.ps1\s+-SkipCalcPad\s*$'
        'job summary boundary' = 'GITHUB_STEP_SUMMARY'
        'CalcPad skip disclosure' = 'It did not execute CalcPad CE'
    }
    foreach ($requirement in $requirements.GetEnumerator()) {
        if (-not [regex]::IsMatch($workflowText, $requirement.Value)) {
            Add-VerificationFailure -Message ".github\workflows\verify.yml is missing its $($requirement.Key)."
        }
    }

    foreach ($line in [System.IO.File]::ReadAllLines($workflowPath)) {
        if ($line.Contains('VerifyRepository.ps1', [System.StringComparison]::Ordinal) -and -not $line.Contains('-SkipCalcPad', [System.StringComparison]::Ordinal)) {
            Add-VerificationFailure -Message '.github\workflows\verify.yml invokes VerifyRepository.ps1 without the explicit -SkipCalcPad boundary.'
        }
    }

    $automationDocumentationPath = Join-Path $script:repositoryRoot 'docs\Automation.md'
    if (-not (Test-Path -LiteralPath $automationDocumentationPath -PathType Leaf)) {
        Add-VerificationFailure -Message 'docs\Automation.md is missing.'
    }
    else {
        $automationDocumentation = [System.IO.File]::ReadAllText($automationDocumentationPath)
        foreach ($requiredText in @('Windows static and distribution verification', 'VerifyRepository.ps1 -SkipCalcPad', 'does not install or execute CalcPad CE', 'self-hosted Windows runner')) {
            if (-not $automationDocumentation.Contains($requiredText, [System.StringComparison]::Ordinal)) {
                Add-VerificationFailure -Message "docs\Automation.md is missing required boundary text '$requiredText'."
            }
        }
    }

    if ($script:verificationFailures.Count -eq $startingFailureCount) {
        Write-Output '[PASS] GitHub Actions runs pinned Windows static verification and documents the CalcPad qualification boundary.'
    }
}

function Test-PublicApi {
    $startingFailureCount = $script:verificationFailures.Count
    $configurationPath = Join-Path $script:repositoryRoot 'Tools\PublicApiAudit.psd1'
    $rulesPath = Join-Path $script:repositoryRoot 'Tools\PublicApiAuditRules.ps1'
    if (-not (Test-Path -LiteralPath $configurationPath -PathType Leaf)) {
        Add-VerificationFailure -Message 'Tools\PublicApiAudit.psd1 is missing.'
        return
    }
    if (-not (Test-Path -LiteralPath $rulesPath -PathType Leaf)) {
        Add-VerificationFailure -Message 'Tools\PublicApiAuditRules.ps1 is missing.'
        return
    }

    try {
        $configuration = Import-PowerShellDataFile -LiteralPath $configurationPath
        . $rulesPath
    }
    catch {
        Add-VerificationFailure -Message "Public API audit configuration or rules could not be loaded: $($_.Exception.Message)"
        return
    }

    $macroLocalPrefixes = $configuration.MacroLocalPrefixes
    $approvedGlobalAssignments = $configuration.ApprovedGlobalMacroAssignments
    $internalHelpers = $configuration.InternalHelpers
    $definitionOnlyHelpers = $configuration.DefinitionOnlyPublicHelpers
    if ($macroLocalPrefixes -isnot [System.Collections.IDictionary]) {
        Add-VerificationFailure -Message 'PublicApiAudit.psd1 must define a MacroLocalPrefixes dictionary.'
        return
    }
    if ($approvedGlobalAssignments -isnot [System.Collections.IDictionary]) {
        Add-VerificationFailure -Message 'PublicApiAudit.psd1 must define an ApprovedGlobalMacroAssignments dictionary.'
        return
    }
    if ($internalHelpers -isnot [System.Collections.IDictionary]) {
        Add-VerificationFailure -Message 'PublicApiAudit.psd1 must define an InternalHelpers dictionary.'
        return
    }
    if ($definitionOnlyHelpers -isnot [System.Collections.IDictionary]) {
        Add-VerificationFailure -Message 'PublicApiAudit.psd1 must define a DefinitionOnlyPublicHelpers dictionary.'
        return
    }

    $ruleTestPath = Join-Path $script:repositoryRoot 'Tests\Tooling\PublicApiAuditTest.ps1'
    if (-not (Test-Path -LiteralPath $ruleTestPath -PathType Leaf)) {
        Add-VerificationFailure -Message 'Tests\Tooling\PublicApiAuditTest.ps1 is missing.'
    }
    else {
        $powerShellPath = (Get-Process -Id $PID).Path
        $ruleTestOutput = & $powerShellPath -NoProfile -File $ruleTestPath 2>&1
        if ($LASTEXITCODE -ne 0) {
            Add-VerificationFailure -Message ('Public API audit rule tests failed: ' + (($ruleTestOutput | ForEach-Object { $_.ToString() }) -join ' '))
        }
    }

    $macroFiles = @(
        Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Core\Src') -Recurse -File -Filter '*.cpd'
        Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Libraries') -Recurse -File -Filter '*.cpd'
    ) | Sort-Object FullName -Unique
    $macroAssignments = [System.Collections.Generic.List[object]]::new()
    foreach ($file in $macroFiles) {
        $source = (Get-RepositoryRelativePath -Path $file.FullName).Replace('\', '/')
        foreach ($assignment in Get-CalcPadMacroAssignments -Lines ([System.IO.File]::ReadAllLines($file.FullName)) -Source $source) {
            $macroAssignments.Add($assignment)
        }
    }

    $assignmentKeys = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    $approvedAssignmentCount = 0
    foreach ($assignment in $macroAssignments) {
        $null = $assignmentKeys.Add("$($assignment.Name)|$($assignment.Source)|$($assignment.Macro)")
        if (-not $macroLocalPrefixes.Contains($assignment.Source)) {
            Add-VerificationFailure -Message "$($assignment.Source):$($assignment.Line) assigns $($assignment.Name) inside $($assignment.Macro), but the module has no macro-local namespace prefix."
            continue
        }

        if ($approvedGlobalAssignments.Contains($assignment.Name)) {
            $approval = $approvedGlobalAssignments[$assignment.Name]
            if (-not (Test-CalcPadApprovedGlobalAssignment -Assignment $assignment -Approval $approval)) {
                Add-VerificationFailure -Message "$($assignment.Source):$($assignment.Line) writes global $($assignment.Name) from unapproved macro $($assignment.Macro)."
            }
            else {
                $approvedAssignmentCount++
            }
            continue
        }

        $prefix = [string]$macroLocalPrefixes[$assignment.Source]
        if (-not (Test-CalcPadMacroLocalName -Name $assignment.Name -Prefix $prefix)) {
            Add-VerificationFailure -Message "$($assignment.Source):$($assignment.Line) macro-local $($assignment.Kind) $($assignment.Name) must use the ζ${prefix}_name namespace."
        }
    }

    foreach ($entry in $macroLocalPrefixes.GetEnumerator() | Sort-Object Key) {
        $source = [string]$entry.Key
        $prefix = [string]$entry.Value
        if ([string]::IsNullOrWhiteSpace($prefix) -or $prefix -cnotmatch '^[A-Z][A-Z0-9]*$') {
            Add-VerificationFailure -Message "Macro namespace inventory has invalid prefix '$prefix' for $source."
        }
        $sourcePath = Join-Path $script:repositoryRoot $source.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
            Add-VerificationFailure -Message "Macro namespace inventory contains missing source $source."
        }
        if (($macroAssignments | Where-Object Source -CEQ $source).Count -eq 0) {
            Add-VerificationFailure -Message "Macro namespace inventory contains stale source $source with no multiline macro assignments."
        }
    }

    foreach ($entry in $approvedGlobalAssignments.GetEnumerator() | Sort-Object Key) {
        $name = [string]$entry.Key
        $approval = $entry.Value
        if ([string]::IsNullOrWhiteSpace([string]$approval.Purpose)) {
            Add-VerificationFailure -Message "Approved global macro assignment $name has no purpose."
        }
        if ([string]::IsNullOrWhiteSpace([string]$approval.Source) -or @($approval.Macros).Count -eq 0) {
            Add-VerificationFailure -Message "Approved global macro assignment $name has no complete source and macro inventory."
            continue
        }
        foreach ($macro in @($approval.Macros)) {
            $key = "$name|$($approval.Source)|$macro"
            if (-not $assignmentKeys.Contains($key)) {
                Add-VerificationFailure -Message "Approved global macro assignment inventory contains stale entry $key."
            }
        }
    }

    $definitions = [System.Collections.Generic.List[object]]::new()
    $sourceRoot = Join-Path $script:repositoryRoot 'Core\Src'
    foreach ($file in Get-ChildItem -LiteralPath $sourceRoot -File -Filter '*.cpd' | Sort-Object Name) {
        $lines = [System.IO.File]::ReadAllLines($file.FullName)
        for ($lineIndex = 0; $lineIndex -lt $lines.Count; $lineIndex++) {
            $line = $lines[$lineIndex]
            $functionMatch = [regex]::Match($line, '^\s*(?<name>[A-Z][A-Za-z0-9_]*)\s*\([^)]*\)\s*=')
            if ($functionMatch.Success) {
                $definitions.Add([pscustomobject]@{
                    Name = $functionMatch.Groups['name'].Value
                    Kind = 'function'
                    Source = Get-RepositoryRelativePath -Path $file.FullName
                    Line = $lineIndex + 1
                })
                continue
            }

            $macroMatch = [regex]::Match($line, '^\s*#def\s+(?<name>[A-Za-z][A-Za-z0-9_]*\$)(?:\s*\([^)]*\))?(?:\s*=|\s*$)')
            if ($macroMatch.Success) {
                $definitions.Add([pscustomobject]@{
                    Name = $macroMatch.Groups['name'].Value
                    Kind = 'macro'
                    Source = Get-RepositoryRelativePath -Path $file.FullName
                    Line = $lineIndex + 1
                })
            }
        }
    }

    foreach ($duplicate in $definitions | Group-Object Name | Where-Object Count -gt 1 | Sort-Object Name) {
        $locations = ($duplicate.Group | ForEach-Object { "$($_.Source):$($_.Line)" }) -join ', '
        Add-VerificationFailure -Message "Public helper $($duplicate.Name) is defined more than once: $locations"
    }

    $definitionByName = @{}
    foreach ($definition in $definitions) {
        $definitionByName[$definition.Name] = $definition
    }

    foreach ($entry in $internalHelpers.GetEnumerator() | Sort-Object Key) {
        if ([string]::IsNullOrWhiteSpace([string]$entry.Value)) {
            Add-VerificationFailure -Message "Internal helper $($entry.Key) has no implementation-purpose explanation."
        }
        if (-not $definitionByName.ContainsKey([string]$entry.Key)) {
            Add-VerificationFailure -Message "Internal helper inventory contains unknown name $($entry.Key)."
        }
    }

    $publicDefinitions = @($definitions | Where-Object { -not $internalHelpers.Contains($_.Name) } | Sort-Object Name)
    $codeFiles = @(
        Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Core\Src') -Recurse -File -Filter '*.cpd'
        Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Libraries') -Recurse -File -Filter '*.cpd'
        Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Examples') -Recurse -File -Filter '*.cpd'
        Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Templates') -Recurse -File -Filter '*.cpd'
        Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Tests') -Recurse -File -Filter '*.cpd'
    ) | Sort-Object FullName -Unique
    $documentationFiles = @(
        Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'docs') -Recurse -File -Filter '*.md'
        Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Examples') -Recurse -File -Filter '*.cpd'
        Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Templates') -Recurse -File -Filter '*.cpd'
    ) | Sort-Object FullName -Unique

    $codeText = [string]::Join("`n", @($codeFiles | ForEach-Object { [System.IO.File]::ReadAllText($_.FullName) }))
    $documentationText = [string]::Join("`n", @($documentationFiles | ForEach-Object { [System.IO.File]::ReadAllText($_.FullName) }))
    $actualDefinitionOnly = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)

    foreach ($definition in $publicDefinitions) {
        $pattern = '(?<![A-Za-z0-9_])' + [regex]::Escape($definition.Name) + '(?![A-Za-z0-9_])'
        $codeOccurrences = [regex]::Matches($codeText, $pattern).Count
        $documentationOccurrences = [regex]::Matches($documentationText, $pattern).Count

        if ($documentationOccurrences -eq 0) {
            Add-VerificationFailure -Message "$($definition.Source):$($definition.Line) public $($definition.Kind) $($definition.Name) is not documented or demonstrated."
        }

        if ($codeOccurrences -eq 1) {
            $null = $actualDefinitionOnly.Add($definition.Name)
            if (-not $definitionOnlyHelpers.Contains($definition.Name)) {
                Add-VerificationFailure -Message "$($definition.Source):$($definition.Line) public $($definition.Kind) $($definition.Name) has no maintained call site and is not allowlisted."
            }
        }
    }

    foreach ($entry in $definitionOnlyHelpers.GetEnumerator() | Sort-Object Key) {
        $name = [string]$entry.Key
        if ([string]::IsNullOrWhiteSpace([string]$entry.Value)) {
            Add-VerificationFailure -Message "Definition-only helper $name has no documented end-user purpose."
        }
        if (-not $definitionByName.ContainsKey($name)) {
            Add-VerificationFailure -Message "Definition-only helper allowlist contains unknown name $name."
            continue
        }
        if (-not $actualDefinitionOnly.Contains($name)) {
            Add-VerificationFailure -Message "Definition-only helper allowlist contains stale entry $name."
        }

        $pattern = '(?<![A-Za-z0-9_])' + [regex]::Escape($name) + '(?![A-Za-z0-9_])'
        $documentationOccurrences = [regex]::Matches($documentationText, $pattern).Count
        if ($documentationOccurrences -eq 0) {
            Add-VerificationFailure -Message "Definition-only helper $name is allowlisted but has no documentation or demonstration."
        }
    }

    if ($script:verificationFailures.Count -eq $startingFailureCount) {
        $localAssignmentCount = $macroAssignments.Count - $approvedAssignmentCount
        Write-Output "[PASS] Public API audit found $($publicDefinitions.Count) documented helpers; $($internalHelpers.Count) implementation helpers and $($definitionOnlyHelpers.Count) intentional definition-only entry points are explained. $localAssignmentCount macro locals use module namespaces; $approvedAssignmentCount global registry writes are approved."
    }
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
    $failureFixtureRoot = [System.IO.Path]::GetFullPath((Join-Path $script:repositoryRoot 'Tests\FailureModes\Fixtures')).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $script:repositoryRoot 'Tests') -Recurse -File -Filter '*.cpd' | Where-Object { -not $_.FullName.StartsWith($failureFixtureRoot, [System.StringComparison]::OrdinalIgnoreCase) } | Sort-Object FullName) {
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
            'Unexpected error:',
            'ζMAT_'
        )
        $matchedError = $errorPatterns | Where-Object { $html.Contains($_) } | Select-Object -First 1
        if ($null -ne $matchedError) {
            Add-VerificationFailure -Message "$relativePath contains a CalcPad parser or runtime error. Output: $outputPath"
            continue
        }

        if ($relativePath -ceq 'Tests\Core\FailureModesTest.cpd') {
            $requiredEvidence = @(
                'Failure-mode reference',
                'Duplicate failure-mode reference',
                'Missing linked reference',
                'Span outside permitted range',
                'Duplicate span input ID',
                'Zero-capacity engineering check',
                'Duplicate engineering check ID',
                'failure-mode-corrupt-review-marker',
                'Corrupted reporting registry review evidence')
            foreach ($requiredText in $requiredEvidence) {
                if (-not $html.Contains($requiredText, [System.StringComparison]::Ordinal)) {
                    Add-VerificationFailure -Message "$relativePath did not render required failure evidence '$requiredText'."
                }
            }
            foreach ($requiredId in @(501, 502, 601, 701)) {
                if (-not [regex]::IsMatch($html, ">\s*$requiredId\s*<")) {
                    Add-VerificationFailure -Message "$relativePath did not render failure ID $requiredId."
                }
            }
            $corruptMarkerIndex = $html.IndexOf('failure-mode-corrupt-review-marker', [System.StringComparison]::Ordinal)
            $corruptEvidence = if ($corruptMarkerIndex -ge 0) { $html.Substring($corruptMarkerIndex) } else { '' }
            if (-not $corruptEvidence.Contains('INVALID REGISTRY', [System.StringComparison]::Ordinal) -or -not $corruptEvidence.Contains('<span class="review-status-label review-status-error">REVIEW ERROR</span>', [System.StringComparison]::Ordinal)) {
                Add-VerificationFailure -Message "$relativePath did not render the corrupt reporting registry as a blocking review error."
            }
        }

        if ($relativePath -ceq 'Tests\Libraries\Analysis\BeamAnalysisFailureModesTest.cpd') {
            $beamMarkerIndex = $html.IndexOf('failure-mode-invalid-beam-marker', [System.StringComparison]::Ordinal)
            $beamEvidence = if ($beamMarkerIndex -ge 0) { $html.Substring($beamMarkerIndex) } else { '' }
            foreach ($requiredText in @('Invalid beam model report evidence', 'Sampled extrema', 'Screening check', 'Beam model status', '<span class="err">CHECK ERROR</span>')) {
                if (-not $beamEvidence.Contains($requiredText, [System.StringComparison]::Ordinal)) {
                    Add-VerificationFailure -Message "$relativePath did not render required invalid-model evidence '$requiredText'."
                }
            }
            if ($beamEvidence.Contains('<span class="ok">PASS</span>', [System.StringComparison]::Ordinal)) {
                Add-VerificationFailure -Message "$relativePath rendered a passing screening status for an invalid beam model."
            }
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

function Test-FailureModeFixtures {
    $startingFailureCount = $script:verificationFailures.Count
    $resolvedCli = Resolve-CalcPadCli
    if ([string]::IsNullOrWhiteSpace($resolvedCli) -or -not (Test-Path -LiteralPath $resolvedCli -PathType Leaf)) {
        return
    }

    $testPath = Join-Path $script:repositoryRoot 'Tests\FailureModes\FailureModeRuntimeTest.ps1'
    if (-not (Test-Path -LiteralPath $testPath -PathType Leaf)) {
        Add-VerificationFailure -Message 'Tests\FailureModes\FailureModeRuntimeTest.ps1 is missing.'
        return
    }

    $outputRoot = if ([string]::IsNullOrWhiteSpace($script:calcPadOutputRoot)) {
        Join-Path ([System.IO.Path]::GetTempPath()) ('drat-calcpad-verify-' + [guid]::NewGuid().ToString('N'))
    }
    else {
        Join-Path $script:calcPadOutputRoot 'failure-modes'
    }
    if ([string]::IsNullOrWhiteSpace($script:calcPadOutputRoot)) {
        $script:calcPadOutputRoot = $outputRoot
    }

    $powerShellPath = (Get-Process -Id $PID).Path
    $testOutput = & $powerShellPath -NoProfile -File $testPath -CalcPadCli $resolvedCli -OutputRoot $outputRoot 2>&1
    if ($LASTEXITCODE -ne 0) {
        Add-VerificationFailure -Message ('Negative CalcPad failure-mode fixtures failed: ' + (($testOutput | ForEach-Object { $_.ToString() }) -join ' '))
        return
    }

    if ($script:verificationFailures.Count -eq $startingFailureCount) {
        $testOutput | ForEach-Object { Write-Output $_.ToString() }
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
Test-ThermophysicalGenerator
Test-AiscGenerators
Test-EngineeringMaterialsSource
Test-DatasetSourceLayout
Test-ApiVersions
Test-IncludeGraph
Test-ArtifactConventions
Test-PublicApi
Test-CiConfiguration
Test-GitWhitespace
Test-DistributionTooling

if ($SkipCalcPad) {
    Write-Output '[SKIP] CalcPad worksheet execution was skipped.'
}
else {
    Test-CalcPadWorksheets
    Test-FailureModeFixtures
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
