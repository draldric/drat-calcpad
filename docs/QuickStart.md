# Quick start

## Requirements

- CalcPad CE for calculating and rendering worksheets.
- PowerShell 7 for rebuilding and verifying the repository.
- Python 3 for validating and regenerating data-backed libraries.
- Network access when rendering Plotly examples, because the plotting module loads Plotly from a CDN.

## Start a worksheet

For an installed release, create a portable calculation project:

```powershell
pwsh -File "$env:LOCALAPPDATA\DRAT-Calcpad\Current\Tools\NewDratProject.ps1" `
    -DestinationPath C:\Engineering\MyCalculation `
    -IncludeMaterials
```

Within a repository checkout, copy `Templates/EngineeringCalculationTemplate.cpd` into a calculation folder one level below the repository root, then retain the direct Core include:

```text
#include ../Core/DratCore.cpd
```

Add optional libraries directly after Core:

```text
#include ../Core/DratCore.cpd
#include ../Libraries/Materials/EngineeringMaterials.cpd
#include ../Libraries/Thermophysical/ThermophysicalProperties.cpd
```

Includes must be relative, direct, and match the exact path casing.
Libraries do not load Core or other libraries on behalf of a worksheet.
See [Distribution and installation](Distribution.md) for installed and portable workflows.

## Complete the document controls

Replace every placeholder in the copied template:

- Organization, client, project, title, and calculation number.
- Purpose and scope.
- Revision, preparer, checker, approver, and dates.
- References, design criteria, input sources, assumptions, and limitations.

Keep `NOT CHECKED` and `NOT APPROVED` visible until those actions have actually occurred.

## Register the design basis

Assign stable positive integer IDs, register references first, and then link design criteria, assumptions, and limitations to those references.
Use `RPT_NO_REFERENCE` only where an assumption or limitation genuinely has no external source.

```text
REF_STANDARD = 1
CRITERION_PRIMARY = 1

'## References
BeginReferences$
AddReference$(REF_STANDARD; GOVERNING STANDARD; STANDARD TITLE; EDITION; CLAUSE; APPLICATION NOTES)
EndReferences$

'#### Design Criteria
BeginDesignCriteria$
AddDesignCriterion$(CRITERION_PRIMARY; PRIMARY CRITERION; REQUIRED LIMIT; REF_STANDARD; CLAUSE; APPLICATION NOTES)
EndDesignCriteria$

'#### Reporting Registry Summary
ShowReportingSummary$
```

Duplicate IDs and unknown reference links are rendered as reporting errors and are counted in the summary.

## Save and validate inputs

Use explicit CalcPad assignments so issued calculations preserve their selected values.
Create one structured validation result per input, then render those same results:

```text
demand = 80kN
capacity = 100kN
warning_threshold = CHK_DEFAULT_WARNING

INPUT_DEMAND = 1
INPUT_CAPACITY = 2
INPUT_WARNING_THRESHOLD = 3

#hide
demand_validation = ValidationNonnegativeResult(demand)
capacity_validation = ValidationPositiveResult(capacity)
warning_validation = ValidationRangeResult(warning_threshold; 0; 1)
#show

BeginValidationSummary$
AddValidationResult$(INPUT_DEMAND; Demand; demand_validation)
AddValidationResult$(INPUT_CAPACITY; Capacity; capacity_validation)
AddValidationResult$(INPUT_WARNING_THRESHOLD; Warning threshold; warning_validation)
EndValidationResults$
'#### Input Items Requiring Review
ShowValidationIssues$

#hide
inputs_valid = ValidationResultRegistryInputsValid(InputValidationRegistry; InputValidationRegistryErrors)
#show
```

Structured results use `[status; value; rule_code; data_1; data_2]`.
The reporting macros derive the displayed value, permitted criterion, and status from that record.

## Calculate and check

Assign a stable ID and register each engineering check once.
The check macro calculates utilization and status, applies the input-validity gate, renders the row, and stores the same result for governing and document-status reporting:

```text
CHECK_DEMAND = 1

BeginCheckRegistry$
AddUpperCheck$(CHECK_DEMAND; Demand check; demand; capacity; warning_threshold; Demand ≤ capacity; inputs_valid)
EndCheckRegistryWithSummary$

ShowCalculationStatusFromRegistries$
'#### Document Review Summary
ShowDocumentReviewSummary$
```

Invalid inputs must produce `CHK_ERROR`; they must not appear as passing engineering checks.
The document review summary consolidates validation, check, and reporting issues and links each stored issue back to its source row. Worksheet Markdown owns these headings; non-cover Core macros render content only.
`Ready for Check` permits an otherwise complete calculation with warnings, while `Ready for Issue` requires a clean `REVIEW_READY` result.

## Use the materials library

Retrieve both the property value and its status, and report the selected record and source:

```text
material = STEEL_ASTM_A36
yield_strength = MatYield(material)
yield_status = MatPROPStatus(material; MAT_P_YIELD_STRENGTH)
available_properties = MatAvailablePropertyIDs(material)

ShowMatRecord$(material)
ShowMatPROP$(material; MAT_P_YIELD_STRENGTH)
```

The current Engineering Materials values are nominal room-temperature screening data.
Confirm that a value is suitable for the governing design basis before treating it as a specified minimum or design allowable.
Use `MatItemsByCategory` to browse one material family and `MatItemsWithProperty` to filter records by data availability.
For a multi-property shortlist, rank, and comparison table:

```text
#hide
required_properties = [MAT_P_DENSITY; MAT_P_YOUNGS_MODULUS; MAT_P_YIELD_STRENGTH]
candidate_ranking = MatRankCandidates(MAT_CAT_FERROUS_METAL; required_properties; MAT_P_YIELD_STRENGTH; MAT_RANK_DESCENDING)
comparison_items = first(MatRankedItems(candidate_ranking); 5)
comparison_properties = [MAT_P_DENSITY; MAT_P_YOUNGS_MODULUS; MAT_P_YIELD_STRENGTH]
#show

#novar
ShowMatRanking$(candidate_ranking; MAT_P_YIELD_STRENGTH; 10)
ShowMatComparison$(comparison_items; comparison_properties)
ShowMatPropertyComparisonPlot$(yieldComparison; comparison_items; MAT_P_YIELD_STRENGTH)
ShowMatPropertyTradeoffPlot$(densityYieldTradeoff; comparison_items; MAT_P_DENSITY; MAT_P_YIELD_STRENGTH)
#equ
```

The ranking is a screening aid, not a design recommendation or substituted design allowable.
Material plots require network access because Core loads Plotly from a CDN.
See the [Engineering Materials library reference](EngineeringMaterials.md) for category IDs, classification semantics, provenance checks, and reporting tables.

## Use the thermophysical-properties library

Query a typed property with a unit-aware temperature and retain its status:

```text
T_process = 60°C
rho_eg = Eg50DensityT(T_process)
rho_status = Eg50DensityTStatus(T_process)
P_sat = WaterSaturationPressureT(T_process)

ShowThermoFluidRecord$(THERMO_EG_50)
ShowThermoProperty$(THERMO_EG_50; THERMO_P_DENSITY; T_process)
```

The initial dataset is limited to water and 50% ethylene glycol curves from 10 °C through 95 °C.
An out-of-range or unavailable property returns an error status and a dimensioned undefined value.
See the [Thermophysical Properties library reference](ThermophysicalProperties.md) before applying a sampled curve to a design state.

## Verify the work

Open and render the worksheet in the CalcPad CE GUI.
Before opening a pull request, run:

```powershell
pwsh -File Tools/VerifyRepository.ps1
```

Use `-SkipCalcPad` only when the CalcPad CLI is unavailable:

```powershell
pwsh -File Tools/VerifyRepository.ps1 -SkipCalcPad
```

Static-only verification does not replace GUI review of layout, pagination, tables, or interactive plots.
