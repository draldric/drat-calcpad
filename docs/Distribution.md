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

The schema-version-2 `manifest.json` records the Core version, every component API, every packaged library identity and revision, required and optional compatibility ranges, packaged file paths, and SHA-256 hashes.
The installer rejects missing, modified, duplicated, unsafe, or unlisted package files and rejects metadata that differs from the declarations inside the packaged Core or libraries.

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
Package and installation paths cannot be equal or nested inside one another.

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

Omit `-IncludeMaterials` for a Core-only project.
Before creating any destination files, the generator verifies the manifest entry, physical file, and SHA-256 hash for `EngineeringMaterials.cpd` when Materials are requested.

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
`drat-project.json` records the DRAT and Core API versions, selected optional libraries, and SHA-256 hashes for every copied project file.
The generator verifies each source file against the installed release manifest before copying it.
Installation and project paths cannot be equal or nested inside one another, including when a junction or symbolic-link alias resolves into either tree.

Updating an installed DRAT release does not silently modify existing portable projects.
Review and replace their copied Core or libraries deliberately, then rerun the worksheet verification appropriate to that calculation.

## Use installed files directly

For local-only worksheets, the installer prints the absolute Core and Materials include lines for the `Current` installation.
Absolute includes are machine- and user-specific and should not be used for calculations that need to remain portable.

CalcPad does not reliably resolve environment variables or nested include paths.
Do not place `%LOCALAPPDATA%` literally inside a worksheet include and do not create a library that loads Core on the worksheet's behalf.

## Qualify the complete workflow

Run the deterministic distribution regression from the repository root:

```powershell
pwsh -File Tests/Distribution/DISTRIBUTION_TEST.ps1
```

This static qualification:

- builds and extracts the versioned archive;
- checks the required package inventory and exact manifest coverage and hashes;
- rejects modified and unlisted package files and missing optional-library entrypoints before project creation;
- validates the complete Core and library metadata contract, including table-driven tampering of component APIs, identities, revisions, and required and optional API guards;
- rejects overlapping build, package/install, and installation/project paths before copying, including junction aliases and destinations below an uncreated path segment;
- installs an internally consistent prior-version fixture, then the actual current package, entirely with tools from the extracted package;
- confirms the previous version remains unchanged and `Current` identifies the current manifest version;
- confirms a prior-version portable project is not changed by the update;
- creates separate Core-only and Materials-enabled projects from the newly installed current package;
- confirms installation updates do not alter either portable project; and
- moves both projects and rejects absolute includes or development, installation, and source-package paths in their worksheets and metadata.

The qualification script exits nonzero on any native CalcPad launch failure and emits its final PASS marker only after every required check succeeds.

When CalcPad CE is installed, include its CLI to render both projects after their original installation and extracted-package paths have been made unavailable:

```powershell
pwsh -File Tests/Distribution/DISTRIBUTION_TEST.ps1 `
    -CalcPadCli "$env:LOCALAPPDATA\Programs\CalcpadCE\cli\Cli.exe"
```

The GitHub-hosted repository-verification job starts from a clean checkout and runs this test through `Tools/VerifyRepository.ps1 -SkipCalcPad`.
That hosted result proves the static build, archive, installation, update, integrity, and relocation paths without claiming CalcPad execution.
