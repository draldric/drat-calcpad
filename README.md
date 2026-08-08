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

Libraries do not include their own dependencies.
Each library checks the core API and its required component APIs before loading its definitions.
If a required API is missing or incompatible, the library skips its body and renders a compatibility error.

## Core calculation helpers

`Checks.cpd` classifies engineering utilization ratios as `CHK_PASS`, `CHK_WARN`, `CHK_FAIL`, or `CHK_ERROR`.
Use `CheckUpperStatus` when demand must not exceed capacity, and `CheckLowerStatus` when a provided value must meet a minimum requirement.
The default warning threshold is available as `CHK_DEFAULT_WARNING`.

`Validation.cpd` validates numeric ranges, positive and nonnegative inputs, integers, and vector or matrix lengths.
Each validator returns a `VAL_*` status code, and `ValidationStatus$` or `ShowValidation$` can render that status in a worksheet.

`Database.cpd` provides column-safe lookup, status, fallback, metadata, and registry helpers for general matrices.
It shares the `DB_*` status codes and missing-value sentinel defined by `DataWrapper.cpd`.

Focused regression worksheets are in `Tests/Core/`.

## Starting a calculation

Copy `Templates/EngineeringCalculationTemplate.cpd` to start a calculation.
Replace its document-control placeholders, references, assumptions, saved inputs, validation calls, calculations, and conclusions.
The template deliberately uses explicit CalcPad assignments instead of browser controls so selected design inputs remain part of the auditable source file.

`Examples/FactorOfSafety.cpd` demonstrates the complete workflow with categorical factor validation, a recommended minimum factor of safety, and a check against the saved design value.
