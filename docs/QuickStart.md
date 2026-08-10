# Quick start

## Requirements

- CalcPad CE for calculating and rendering worksheets.
- PowerShell 7 for rebuilding and verifying the repository.
- Network access when rendering Plotly examples, because the plotting module loads Plotly from a CDN.

## Start a worksheet

Copy `Templates/EngineeringCalculationTemplate.cpd` into a calculation folder one level below the repository root, then retain the direct Core include:

```text
#include ../Core/DratCore.cpd
```

Add optional libraries directly after Core:

```text
#include ../Core/DratCore.cpd
#include ../Libraries/Materials/EngineeringMaterials.cpd
```

Includes must be relative, direct, and match the exact path casing.
Libraries do not load Core or other libraries on behalf of a worksheet.

## Complete the document controls

Replace every placeholder in the copied template:

- Organization, client, project, title, and calculation number.
- Purpose and scope.
- Revision, preparer, checker, approver, and dates.
- References, design criteria, input sources, assumptions, and limitations.

Keep `NOT CHECKED` and `NOT APPROVED` visible until those actions have actually occurred.

## Save and validate inputs

Use explicit CalcPad assignments so issued calculations preserve their selected values.
Create one structured validation result per input, then render those same results:

```text
demand = 80kN
capacity = 100kN
warning_threshold = CHK_DEFAULT_WARNING

#hide
demand_validation = ValidationNonnegativeResult(demand)
capacity_validation = ValidationPositiveResult(capacity)
warning_validation = ValidationRangeResult(warning_threshold; 0; 1)
input_results = join_rows(demand_validation; capacity_validation; warning_validation)
input_statuses = ValidationResultsStatuses(input_results)
inputs_valid = not(ValidationHasErrors(input_statuses))
#show

#novar
BeginValidationSummary$
AddValidationResult$(Demand; demand_validation)
AddValidationResult$(Capacity; capacity_validation)
AddValidationResult$(Warning threshold; warning_validation)
EndValidationResults$(input_results)
#equ
```

Structured results use `[status; value; rule_code; data_1; data_2]`.
The reporting macros derive the displayed value, permitted criterion, and status from that record.

## Calculate and check

Gate each engineering check with the input-validation result:

```text
#hide
utilization = CheckUpperUtilization(demand; capacity)
raw_status = CheckUpperStatus(demand; capacity; warning_threshold)
check_status = CheckGatedStatus(inputs_valid; raw_status)
check_statuses = [check_status]
check_utilizations = [utilization]
overall_status = CheckSummaryStatus(check_statuses; check_utilizations)
#show

#novar
BeginCheckSummary$
AddCheckRow$(Demand check; demand; capacity; utilization; warning_threshold; Demand ≤ capacity; check_status)
EndCheckSummaryWithResult$(check_statuses; check_utilizations; Demand check)
#equ
```

Invalid inputs must produce `CHK_ERROR`; they must not appear as passing engineering checks.

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
See the [Engineering Materials library reference](EngineeringMaterials.md) for category IDs, classification semantics, provenance checks, and reporting tables.

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
