# CalcpadCE Engineering Framework

Modular framework for reusable engineering calculations.

## Documentation

- [Quick start](docs/QuickStart.md)
- [Architecture](docs/Architecture.md)
- [Core API reference](docs/CoreApi.md)
- [Engineering Materials library](docs/EngineeringMaterials.md)
- [Structural Sections library](docs/StructuralSections.md)
- [Status-code reference](docs/StatusCodes.md)
- [Library-authoring guide](docs/LibraryAuthoring.md)
- [Versioning policy](docs/Versioning.md)
- [Compatibility matrix](docs/Compatibility.md)
- [Distribution and installation](docs/Distribution.md)
- [Contributor guide](CONTRIBUTING.md)
- [Release checklist](docs/ReleaseChecklist.md)
- [Changelog](CHANGELOG.md)

## Core and libraries

Worksheets load the generated core bundle before any optional libraries:

```text
#include ../Core/DratCore.cpd
#include ../Libraries/Materials/EngineeringMaterials.cpd
```

Maintain the individual core modules in `Core/Src/`.
Run `Tools/BuildCore.ps1` after changing a core source module, and commit the regenerated `Core/DratCore.cpd`.
Run `Tools/BuildCore.ps1 -Check` to verify that the committed bundle is current.

Build a versioned release directory and ZIP archive with `Tools/BuildDistribution.ps1 -Archive`.
Install an extracted release with `Tools/InstallDratCalcpad.ps1`, or create a self-contained calculation folder with `Tools/NewDratProject.ps1`.
See the [distribution guide](docs/Distribution.md) for the managed installation and portable-project workflows.
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

`CalculationStatus.cpd` combines the validation and engineering-check vectors into a document-level `CALC_PASS`, `CALC_WARN`, `CALC_FAIL`, `CALC_INCOMPLETE`, or `CALC_ERROR` result.
Use `ShowCalculationStatus$` for the standard calculation banner and counts.

`Reporting.cpd` provides structured registries for references, design criteria, assumptions, and limitations.
Each entry has a positive integer ID; linked entries validate their source reference, duplicate IDs render inline errors, and `ShowReportingSummary$` reports the registered counts and aggregate registry status.
CalcPad text remains macro content, while the numeric registries preserve the auditable identities and relationships used for validation.

`Validation.cpd` validates defined values, the complete positive/negative/zero sign family, inclusive and open ranges, excluded ranges, one-sided and absolute bounds, integers, vector length and contents, vector ordering and uniqueness, matching vector lengths, matrix row and column counts, square matrices, registered values, available values, and values from registered option sets.
The result constructors return `[status; value; rule_code; data_1; data_2]`, allowing `AddValidationResult$` to render the value, permitted criterion, and status from one result.
Stack results with `join_rows`, obtain their statuses with `ValidationResultsStatuses`, and close the table with `EndValidationResults$`.
The original scalar `Validation*Status` functions and `AddValidationRow$` remain available for compatibility.
`ValidationLengthResult` checks the number of entries in a vector rather than the magnitude of its entries; use `ValidationRangeResult` for a scalar magnitude and `ValidationVectorRangeResult` to check every vector entry.
Use separate `ValidationMatrixRowsResult` and `ValidationMatrixColumnsResult` records for bounded dimensions, or `ValidationMatrixDimensionsResults` to produce both records for an exact matrix shape.

The global `ValidationAllowedRegistry` stores reusable permitted-value sets as `[set_id; value]` rows.
Add a vector of values with `ValidationRegistryAdd`, then create results with `ValidationAllowedSetResult`; calculation and reporting retrieve the same registered values.

```text
ValidationAllowedRegistry = ValidationRegistryAdd(ValidationAllowedRegistry; set_id; [1.1; 1.2; 1.3])
input_result = ValidationAllowedSetResult(input_value; set_id)
input_results = join_rows(input_result)

BeginValidationSummary$
AddValidationResult$(Input prompt; input_result)
EndValidationResults$(input_results)
```

`Database.cpd` provides column-safe lookup, status, fallback, metadata, and registry helpers for general matrices.
It shares the `DB_*` status codes and missing-value sentinel defined by `DataWrapper.cpd`.

Focused regression worksheets are organized under `Tests/Core/` and `Tests/Libraries/`.

## Starting a calculation

Copy `Templates/EngineeringCalculationTemplate.cpd` to start a calculation.
Replace its document-control placeholders, references, assumptions, saved inputs, validation calls, calculations, and conclusions.
The template deliberately uses explicit CalcPad assignments instead of browser controls so selected design inputs remain part of the auditable source file.
Its standard structure covers purpose and scope, references, design criteria, input sources, assumptions, limitations, saved inputs, validation, methodology, calculations, results, engineering checks, and conclusions.
Numbered H3 sections begin on new pages when printed or exported to PDF; H4 and H5 headings remain numbered subsections on the current page.
Required organization, client, project, calculation, and preparation metadata uses direct, readable placeholders, while unchecked and unapproved states remain visible in the document header.

`Examples/FactorOfSafety.cpd` demonstrates the complete workflow with categorical factor validation, a recommended minimum factor of safety, and a check against the saved design value.
`Examples/MaterialAllowableCheck.cpd` demonstrates a complete Engineering Materials lookup, source and revision reporting, unit-aware validation, multiple factored-strength checks, governing-check identification, and engineering conclusions.
Use `ShowMatRecord$` for the selected material metadata and `ShowMatPROP$` for retrieved property values and source status; both predefined tables right-align their value column.
Use `MatItemsByCategory`, `MatAvailablePropertyIDs`, and `MatItemsWithProperty` to discover suitable records without duplicating catalog data in a worksheet.
Use `MatCandidateItems`, `MatRankCandidates`, and the unit-aware threshold helpers to create transparent screening shortlists without an implicit weighted score.
Use `ShowMatDatasetSummary$`, `ShowMatCategory$`, `ShowMatProperties$`, `ShowMatRanking$`, `ShowMatComparison$`, and the material plotting macros to render dataset coverage, ranked candidates, side-by-side selections, and property trade-offs.
Current populated values are explicitly classified as screening values; consult the [Engineering Materials library reference](docs/EngineeringMaterials.md) before using them in a design check.
