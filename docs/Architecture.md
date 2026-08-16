# Architecture

## Repository layers

DRAT separates calculation infrastructure from worksheet and library content:

```text
Core/Src/                         Maintained Core modules
        └─ Tools/BuildCore.ps1
Core/DratCore.cpd                 Generated, distributable Core bundle
Libraries/                        Optional engineering data libraries
Libraries/Thermophysical/Data/   Maintained raw property data
Libraries/Thermophysical/*.cpd   Generated runtime library
Templates/                        General calculation and categorized specialized templates
Examples/                         Complete supported workflows
Tests/Core/                       Deterministic Core regression worksheets
Tests/Libraries/                  Deterministic library regression worksheets
Tools/VerifyRepository.ps1       Static and CalcPad verification entry point
Tools/GenerateThermophysical...  Raw-data validation and library generation
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
8. `CheckRegistry.cpd`
9. `CalculationStatus.cpd`
10. `Reporting.cpd`
11. `ReviewSummary.cpd`
12. `Plotting.cpd`

The order is part of the Core contract because later modules use constants and macros defined earlier.

Run `Tools/BuildCore.ps1` after changing a Core source module.
Run `Tools/BuildCore.ps1 -Check` to compare the committed bundle with the sources without modifying it.

## Trusted calculation flow

The standard worksheet flow is:

1. Save explicit, auditable input assignments.
2. Create structured validation results and assign stable input IDs.
3. Register and render each validation result once.
4. Calculate demands and capacities.
5. Register each engineering check once with its stable ID, method, warning threshold, acceptance criterion, and input-validity gate.
6. Derive status vectors, issue counts, overall status, and governing utilization from the check registry.
7. Derive the document-level calculation status directly from the global validation-result and check registries.
8. Combine calculation status and reporting integrity into the document-review state.
9. Present results, source records, checks, the linked review summary, and conclusions.

The reporting registries separately preserve the identities and source relationships for references, design criteria, assumptions, and limitations.
Their human-readable text is rendered by macros because CalcPad calculation matrices are numeric and unit-valued rather than general string containers.

The validation-result and check-result registries are deliberately reused for both calculation decisions and reporting.
This prevents displayed values, criteria, statuses, and governing summaries from drifting away from the rules that were evaluated.
The final review summary uses all three registry families and distinguishes a calculation that is ready for checking from one that is clean enough for issue.

## Data libraries

Libraries are consumers of Core APIs.
They must:

- Guard their complete body with compatible Core and component API ranges.
- Define stable numeric IDs and readable aliases.
- Return a value and a separate status.
- Preserve missing data as `DB_MISSING` internally and return non-finite values for fatal public lookups.
- Report library revision, data source, and dataset revision.
- Keep imported or sampled raw data separate from generated CalcPad source and validate its schema before generation.
- Skip their body and render a compatibility message when a required API is incompatible.

See the [library-authoring guide](LibraryAuthoring.md) for the full contract.

## Verification boundaries

`Tools/VerifyRepository.ps1` checks:

- Generated-Core freshness.
- Thermophysical raw-data schema tests and generated-library freshness.
- Core and component API declarations.
- Include existence, casing, location, and directness.
- Git whitespace errors.
- CalcPad parsing and runtime output for tests, examples, and the engineering template.
- Every rendered `all_tests` assertion.
- Example report structure and focused-purpose metadata.
- Test-purpose declarations and explicit browser-diagnostic exceptions.
- PascalCase artifact names and categorized template placement.
- Public Core helper documentation, implementation-helper inventory, and intentional definition-only entry points.

Manual CalcPad CE GUI review remains necessary for print layout, pagination, table alignment, browser controls, and Plotly behavior.

CalcPad CE does not expose a catchable predicate for arbitrary dimensional compatibility.
Its documented `getunits` function returns a unit-valued expression, but comparing that expression with a unitless value raises `Inconsistent units` before a custom function can branch or return `CHK_ERROR`; clearing the units also removes the dimensional identity needed for the test.
Consequently, incompatible demand/capacity units and unit-bearing numeric metadata remain an explicit engine boundary: maintained negative fixtures must assert CalcPad's native unit diagnostic and confirm that no check or model status is rendered.
A release criterion requiring those cases to return `CHK_ERROR` before division is not currently satisfiable and must be revised rather than reported as met, unless CalcPad adds a safe compatibility predicate.
