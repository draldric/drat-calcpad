# CalcpadCE Engineering Framework

Modular framework for reusable engineering calculations.

## Core and libraries

Worksheets load the generated core bundle before any optional libraries:

```text
#include ../Core/DratCore.cpd
#include ../Libraries/Materials/EngineeringMaterials.cpd
```

Maintain the individual core modules in `Core/Src/`.
Run `Tools/BuildCore.ps1` after changing a core source module, and commit the regenerated `Core/DratCore.cpd`.
Run `Tools/BuildCore.ps1 -Check` to verify that the committed bundle is current.
Run `Tools/VerifyRepository.ps1` before opening a pull request to verify the generated Core, API versions, include graph, whitespace, Core tests, examples, and engineering template.
Pass `-SkipCalcPad` when only static checks are available, or `-CalcPadCli <path>` when CalcPad CE is installed outside its default location.

Libraries do not include their own dependencies.
Each library checks the core API and its required component APIs before loading its definitions.
If a required API is missing or incompatible, the library skips its body and renders a compatibility error.

## Core calculation helpers

`Checks.cpd` classifies engineering utilization ratios as `CHK_PASS`, `CHK_WARN`, `CHK_FAIL`, or `CHK_ERROR`.
Use `CheckUpperStatus` when demand must not exceed capacity, and `CheckLowerStatus` when a provided value must meet a minimum requirement.
The default warning threshold is available as `CHK_DEFAULT_WARNING`.
Use `BeginCheckSummary$`, `AddCheckRow$`, and `EndCheckSummary$` for expanded comparison tables containing demand or required value, capacity or provided value, utilization, warning threshold, acceptance criterion, and status.
Use `EndCheckSummaryWithResult$` with matching status and utilization vectors to add pass, warning, fail, and error counts, the overall status, and the governing check.
`CheckGoverningIndex` selects the first maximum utilization when values tie, and `CheckGatedStatus` forces a check error when its validated inputs are not usable.

`Validation.cpd` validates numeric ranges, positive and nonnegative inputs, integers, and vector or matrix lengths.
Each validator returns a `VAL_*` status code, and `ValidationStatus$` or `ShowValidation$` can render that status in a worksheet.
Use `BeginValidationSummary$`, `AddValidationRow$`, and `EndValidationSummary$` for compact input, permitted-criterion, error-count, and status reporting.

`Database.cpd` provides column-safe lookup, status, fallback, metadata, and registry helpers for general matrices.
It shares the `DB_*` status codes and missing-value sentinel defined by `DataWrapper.cpd`.

Focused regression worksheets are in `Tests/Core/`.

## Starting a calculation

Copy `Templates/EngineeringCalculationTemplate.cpd` to start a calculation.
Replace its document-control placeholders, references, assumptions, saved inputs, validation calls, calculations, and conclusions.
The template deliberately uses explicit CalcPad assignments instead of browser controls so selected design inputs remain part of the auditable source file.
Its standard structure covers purpose and scope, references, design criteria, input sources, assumptions, limitations, saved inputs, validation, methodology, calculations, results, engineering checks, and conclusions.
Numbered H3 sections begin on new pages when printed or exported to PDF; H4 and H5 headings remain numbered subsections on the current page.
Required organization, client, project, calculation, and preparation metadata uses direct, readable placeholders, while unchecked and unapproved states remain visible in the document header.

`Examples/FactorOfSafety.cpd` demonstrates the complete workflow with categorical factor validation, a recommended minimum factor of safety, and a check against the saved design value.
