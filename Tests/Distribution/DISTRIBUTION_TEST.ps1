[CmdletBinding()]
param(
    [string]$CalcPadCli
)

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('drat-distribution-test-' + [guid]::NewGuid().ToString('N'))
$outputRoot = Join-Path $testRoot 'output'
$installRoot = Join-Path $testRoot 'install'
$projectRoot = Join-Path $testRoot 'project'

function Assert-DistributionTest {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

try {
    New-Item -ItemType Directory -Path $testRoot -Force | Out-Null

    & (Join-Path $repositoryRoot 'Tools\BuildDistribution.ps1') -OutputDirectory $outputRoot -Archive
    $packageRoot = Get-ChildItem -LiteralPath $outputRoot -Directory | Select-Object -First 1
    Assert-DistributionTest -Condition ($null -ne $packageRoot) -Message 'Distribution directory was not created.'

    $manifestPath = Join-Path $packageRoot.FullName 'manifest.json'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    Assert-DistributionTest -Condition ($manifest.product -eq 'DRAT CalcpadCE') -Message 'Distribution product identifier is invalid.'
    Assert-DistributionTest -Condition ($manifest.version -match '^\d+\.\d+\.\d+$') -Message 'Distribution version is invalid.'
    Assert-DistributionTest -Condition ($manifest.core_api -gt 0) -Message 'Distribution Core API is invalid.'
    Assert-DistributionTest -Condition ($manifest.libraries.Count -ge 1) -Message 'Distribution library compatibility records are missing.'
    Assert-DistributionTest -Condition (Test-Path -LiteralPath (Join-Path $packageRoot.FullName 'Core\DratCore.cpd') -PathType Leaf) -Message 'Generated Core is missing from the distribution.'
    Assert-DistributionTest -Condition (-not (Test-Path -LiteralPath (Join-Path $packageRoot.FullName 'Core\Src'))) -Message 'Core source modules must not be included in the runtime distribution.'
    $archivePath = Join-Path $outputRoot ($packageRoot.Name + '.zip')
    Assert-DistributionTest -Condition (Test-Path -LiteralPath $archivePath -PathType Leaf) -Message 'Distribution archive was not created.'

    foreach ($record in $manifest.files) {
        $filePath = Join-Path $packageRoot.FullName $record.path.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        Assert-DistributionTest -Condition (Test-Path -LiteralPath $filePath -PathType Leaf) -Message "Manifest file is missing: $($record.path)"
        $actualHash = (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
        Assert-DistributionTest -Condition ($actualHash -ceq $record.sha256) -Message "Manifest hash mismatch: $($record.path)"
    }

    $extractionRoot = Join-Path $testRoot 'extracted'
    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractionRoot
    $extractedPackageRoot = Join-Path $extractionRoot $packageRoot.Name
    Assert-DistributionTest -Condition (Test-Path -LiteralPath (Join-Path $extractedPackageRoot 'manifest.json') -PathType Leaf) -Message 'Extracted distribution manifest is missing.'

    $tamperedPackageRoot = Join-Path $testRoot 'tampered-package'
    Copy-Item -LiteralPath $extractedPackageRoot -Destination $tamperedPackageRoot -Recurse
    Add-Content -LiteralPath (Join-Path $tamperedPackageRoot 'Core\DratCore.cpd') -Value "`n' tampered"
    $tamperRejected = $false
    try {
        & (Join-Path $repositoryRoot 'Tools\InstallDratCalcpad.ps1') -PackagePath $tamperedPackageRoot -DestinationPath (Join-Path $testRoot 'tampered-install')
    }
    catch {
        $tamperRejected = $true
    }
    Assert-DistributionTest -Condition $tamperRejected -Message 'Installer accepted a package with a modified file.'

    $installerPath = Join-Path $repositoryRoot 'Tools\InstallDratCalcpad.ps1'
    & $installerPath -PackagePath $extractedPackageRoot -DestinationPath $installRoot
    & $installerPath -PackagePath $extractedPackageRoot -DestinationPath $installRoot

    $versionRoot = Join-Path $installRoot ('versions\' + $manifest.version)
    $currentRoot = Join-Path $installRoot 'Current'
    Assert-DistributionTest -Condition (Test-Path -LiteralPath (Join-Path $versionRoot '.drat-managed-install.json') -PathType Leaf) -Message 'Versioned installation marker is missing.'
    Assert-DistributionTest -Condition (Test-Path -LiteralPath (Join-Path $currentRoot '.drat-managed-install.json') -PathType Leaf) -Message 'Current installation marker is missing.'
    Assert-DistributionTest -Condition ((Get-FileHash -LiteralPath (Join-Path $currentRoot 'Core\DratCore.cpd') -Algorithm SHA256).Hash -ceq (Get-FileHash -LiteralPath (Join-Path $packageRoot.FullName 'Core\DratCore.cpd') -Algorithm SHA256).Hash) -Message 'Installed Core does not match the package.'

    & (Join-Path $repositoryRoot 'Tools\NewDratProject.ps1') -InstallationPath $currentRoot -DestinationPath $projectRoot -IncludeMaterials
    $worksheetPath = Join-Path $projectRoot 'Calculations\EngineeringCalculation.cpd'
    $worksheetText = [System.IO.File]::ReadAllText($worksheetPath)
    Assert-DistributionTest -Condition ($worksheetText.Contains('#include ../Core/DratCore.cpd')) -Message 'Portable project Core include is invalid.'
    Assert-DistributionTest -Condition ($worksheetText.Contains('#include ../Libraries/Materials/EngineeringMaterials.cpd')) -Message 'Portable project Materials include is invalid.'
    Assert-DistributionTest -Condition (Test-Path -LiteralPath (Join-Path $projectRoot 'Core\DratCore.cpd') -PathType Leaf) -Message 'Portable project Core is missing.'
    Assert-DistributionTest -Condition (Test-Path -LiteralPath (Join-Path $projectRoot 'Libraries\Materials\EngineeringMaterials.cpd') -PathType Leaf) -Message 'Portable project Materials library is missing.'

    if (-not [string]::IsNullOrWhiteSpace($CalcPadCli)) {
        $calcPadOutputPath = Join-Path $testRoot 'portable-project.html'
        & $CalcPadCli $worksheetPath $calcPadOutputPath -s
        Assert-DistributionTest -Condition ($LASTEXITCODE -eq 0) -Message 'CalcPad could not render the portable project worksheet.'
        Assert-DistributionTest -Condition (Test-Path -LiteralPath $calcPadOutputPath -PathType Leaf) -Message 'CalcPad did not create portable-project output.'
        $calcPadOutput = [System.IO.File]::ReadAllText($calcPadOutputPath)
        Assert-DistributionTest -Condition (-not $calcPadOutput.Contains('Error in &quot;')) -Message 'The portable project contains a CalcPad parser or runtime error.'
    }

    Write-Output '[PASS] Distribution build, manifest hashes, installation, update, and portable-project creation.'
}
finally {
    $resolvedTestRoot = [System.IO.Path]::GetFullPath($testRoot)
    $temporaryRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    if ($resolvedTestRoot.StartsWith($temporaryRoot, [System.StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $resolvedTestRoot).StartsWith('drat-distribution-test-')) {
        Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
