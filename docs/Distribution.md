# Distribution and installation

DRAT supports a versioned user installation and portable calculation projects.
The portable-project workflow is recommended for calculations that will be archived, reviewed on another computer, or shared with another engineer.

## Build a release bundle

From the repository root:

```powershell
pwsh -File Tools/BuildDistribution.ps1 -Archive
```

The script verifies that `Core/DratCore.cpd` is current and creates:

```text
artifacts/
├── DRAT-Calcpad-VERSION/
└── DRAT-Calcpad-VERSION.zip
```

The bundle contains the generated Core, supported libraries, templates, examples, documentation, install tools, changelog, and license.
It intentionally excludes the modular Core source and repository tests.

`manifest.json` records the Core version, component APIs, library compatibility requirements, packaged file paths, and SHA-256 hashes.
The installer rejects missing or modified package files.

Use `-Force` only to replace an existing bundle with the same version:

```powershell
pwsh -File Tools/BuildDistribution.ps1 -Archive -Force
```

## Install or update DRAT

Extract the release archive, then run its installer:

```powershell
pwsh -File Tools/InstallDratCalcpad.ps1
```

The default installation root is:

```text
%LOCALAPPDATA%\DRAT-Calcpad
```

Each release is retained under `versions/VERSION`.
`Current` is a managed copy of the most recently installed release and provides a stable path for local worksheets.
The installer verifies every packaged file before installing and refuses to replace directories that do not contain a DRAT managed-install marker.

Use `-DestinationPath` for a different user-controlled location:

```powershell
pwsh -File Tools/InstallDratCalcpad.ps1 -DestinationPath D:\Engineering\DRAT-Calcpad
```

Installing the same package again is idempotent.
Use `-Force` only to replace a damaged managed copy of the same version.

## Create a portable project

Create a calculation folder containing its own generated Core and optional libraries:

```powershell
pwsh -File "$env:LOCALAPPDATA\DRAT-Calcpad\Current\Tools\NewDratProject.ps1" `
    -DestinationPath C:\Engineering\Project-123\DRAT `
    -IncludeMaterials
```

The project layout is:

```text
DRAT/
├── Calculations/
│   └── EngineeringCalculation.cpd
├── Core/
│   └── DratCore.cpd
├── Libraries/
│   └── Materials/
└── drat-project.json
```

The worksheet uses direct relative includes, so moving or archiving the complete project folder does not change its dependencies.
`drat-project.json` records the DRAT and Core API versions copied into the project.

Updating an installed DRAT release does not silently modify existing portable projects.
Review and replace their copied Core or libraries deliberately, then rerun the worksheet verification appropriate to that calculation.

## Use installed files directly

For local-only worksheets, the installer prints the absolute Core and Materials include lines for the `Current` installation.
Absolute includes are machine- and user-specific and should not be used for calculations that need to remain portable.

CalcPad does not reliably resolve environment variables or nested include paths.
Do not place `%LOCALAPPDATA%` literally inside a worksheet include and do not create a library that loads Core on the worksheet's behalf.
