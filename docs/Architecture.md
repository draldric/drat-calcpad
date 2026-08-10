# Architecture

## Repository layers

DRAT separates calculation infrastructure from worksheet and library content:

```text
Core/Src/                         Maintained Core modules
        └─ Tools/BuildCore.ps1
Core/DratCore.cpd                 Generated, distributable Core bundle
Libraries/                        Optional engineering data libraries
Templates/                        Starting points for worksheets and libraries
Examples/                         Complete supported workflows
Tests/Core/                       Deterministic Core regression worksheets
Tools/VerifyRepository.ps1       Static and CalcPad verification entry point
```

Edit modules under `Core/Src/`.
Do not edit generated sections in `Core/DratCore.cpd` directly.

## Include contract

A worksheet loads the generated Core bundle first, followed by each optional library it uses:

```text
#include ../Core/DratCore.cpd
#include ../Libraries/Materials/EngineeringMaterials.cpd
```

DRAT intentionally uses a flat, direct include graph:

- Every include originates in the root worksheet.
- Libraries do not include Core or other libraries.
- Include paths are relative to the worksheet, remain inside the repository, and use exact casing.
- The repository verifier rejects absolute, missing, incorrectly cased, external, and nested includes.

This contract avoids relying on ambiguous nested-include path behavior and makes worksheet dependencies visible at the top of the calculation.

## Core build

`Tools/BuildCore.ps1` concatenates these modules in order:

1. `CoreManifest.cpd`
2. `Stylesheet.cpd`
3. `Definitions.cpd`
4. `DataWrapper.cpd`
5. `Checks.cpd`
6. `Database.cpd`
7. `Validation.cpd`
8. `Plotting.cpd`

The order is part of the Core contract because later modules use constants and macros defined earlier.

Run `Tools/BuildCore.ps1` after changing a Core source module.
Run `Tools/BuildCore.ps1 -Check` to compare the committed bundle with the sources without modifying it.

## Trusted calculation flow

The standard worksheet flow is:

1. Save explicit, auditable input assignments.
2. Create structured validation results.
3. Aggregate and render input validation.
4. Calculate demands, capacities, and utilizations.
5. Gate engineering-check statuses on valid inputs.
6. Aggregate check counts, overall status, and governing utilization.
7. Present results, source records, checks, and conclusions.

The validation records and engineering-status vectors are deliberately reused for both calculation decisions and reporting.
This prevents displayed criteria from drifting away from the rules that were evaluated.

## Data libraries

Libraries are consumers of Core APIs.
They must:

- Guard their complete body with compatible Core and component API ranges.
- Define stable numeric IDs and readable aliases.
- Return a value and a separate status.
- Preserve missing data as `DB_MISSING` internally and return non-finite values for fatal public lookups.
- Report library revision, data source, and dataset revision.
- Skip their body and render a compatibility message when a required API is incompatible.

See the [library-authoring guide](LibraryAuthoring.md) for the full contract.

## Verification boundaries

`Tools/VerifyRepository.ps1` checks:

- Generated-Core freshness.
- Core and component API declarations.
- Include existence, casing, location, and directness.
- Git whitespace errors.
- CalcPad parsing and runtime output for tests, examples, and the engineering template.
- Every rendered `all_tests` assertion.

Manual CalcPad CE GUI review remains necessary for print layout, pagination, table alignment, browser controls, and Plotly behavior.
