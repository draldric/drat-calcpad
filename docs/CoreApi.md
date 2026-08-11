# Core API reference

This reference summarizes the supported public surface in `Core/DratCore.cpd`.
Internal block variables and names beginning with `ζ` are implementation details.

Function arguments are separated with semicolons in CalcPad syntax.
Macro names end with `$`.

## Compatibility manifest

`CoreManifest.cpd` publishes:

| Name | Current value | Purpose |
| --- | ---: | --- |
| `DRAT_CORE_API` | `30000` | Complete generated-Core API |
| `DRAT_DEFINITIONS_API` | `20000` | Worksheet reporting definitions |
| `DRAT_STYLESHEET_API` | `10600` | Shared rendered styles |
| `DRAT_PLOTTING_API` | `30200` | Plotly wrapper |
| `DRAT_DATA_WRAPPER_API` | `302` | Numeric property and curve wrapper |
| `DRAT_CHECKS_API` | `20000` | Engineering check calculations |
| `DRAT_CHECK_REGISTRY_API` | `10000` | Structured engineering-check registry and reporting |
| `DRAT_DATABASE_API` | `10000` | General table and metadata lookups |
| `DRAT_VALIDATION_API` | `10400` | Structured input validation |
| `DRAT_CALCULATION_STATUS_API` | `10100` | Document-level calculation status |
| `DRAT_REPORTING_API` | `10000` | Structured report registries |

`DRATCoreName$` and `DRATCoreVersion$` provide display metadata.
`DBWrapperName$` and `DBWrapperVersion$` identify the bundled DataWrapper implementation.
See [Versioning](Versioning.md) before changing any API value.

## Worksheet definitions

### General formatting

| Macro | Purpose |
| --- | --- |
| `pagebreak$` | Insert an explicit print page break |
| `tab$` | Insert fixed non-breaking horizontal space |
| `err$(message)` | Render error text |
| `ok$(message)` | Render success text |
| `desc$(message)` | Render note text |
| `ref$(message)` | Render reference text |
| `if$(condition; true_text; false_text)` | Render one of two paragraphs |
| `cmt$(content)` | Wrap rendered content in an HTML comment |
| `shide$` / `ehide$` | Open and close an HTML comment |

### Document control

`CreateHeader$`, `CreateTitle$`, `CreatePurpose$`, and `CreateScope$` render the standard document metadata.
The worksheet must first define the `$` macros used by the header, including `Organization$`, `Client$`, `Project$`, `Calculation$`, `Rev$`, preparer/checker/approver fields, `Title$`, `Purpose$`, and `Scope$`.

### Reusable sections

| Begin | Row/item | End | Result |
| --- | --- | --- | --- |
| `BeginRevisions$` | `AddRevision$(revision; description; author; date)` | `EndRevisions$` | Revision-history table |
| `BeginListSection$(heading)` | `AddListItem$(item)` | `EndListSection$` | H4 subsection list |
| `BeginVariables$` | `AddVariable$(symbol; description; units)` | `EndVariables$` | Rendered variable table |
| `BeginConclusions$` | `AddConclusion$(label; value)` | `EndConclusions$` | Conclusions block |

`AddValidationConclusion$(label; status)` and `AddCheckConclusion$(label; status)` add rendered statuses to an open conclusions block.

## Reporting registries

CalcPad calculation matrices do not store arbitrary report text.
The reporting API therefore stores numeric identities and reference relationships in calculation registries while its macros render the associated text when an entry is registered.
This provides enforceable duplicate-ID and source-reference checks without hiding report content in an external data layer.

The generated Core initializes these worksheet registries:

| Registry | Stored calculation fields |
| --- | --- |
| `ReportReferences` | Reference ID |
| `ReportDesignCriteria` | Criterion ID and required reference ID |
| `ReportAssumptions` | Assumption ID and optional reference ID |
| `ReportLimitations` | Limitation ID and optional reference ID |
| `ReportRegistryErrors` | Status returned for every attempted registration |

`RPT_NO_REFERENCE` is permitted for assumptions and limitations.
Design criteria require a previously registered reference.
All ordinary entry IDs must be positive integers and unique within their typed registry.
Rendered reference IDs are document links, so a criterion, assumption, or limitation can be followed directly to its registered source row.

Use the standard report flow:

```text
REF_STANDARD = 1
CRITERION_STRENGTH = 1
ASSUMPTION_STATIC = 1
LIMITATION_TEMPERATURE = 1

BeginReferences$
AddReference$(REF_STANDARD; CSA S16; Design of steel structures; 2024; Clause 13; Governing resistance standard.)
EndReferences$

BeginDesignCriteria$
AddDesignCriterion$(CRITERION_STRENGTH; Member resistance; Demand must not exceed resistance.; REF_STANDARD; Clause 13; Use the applicable resistance equation.)
EndDesignCriteria$

BeginAssumptions$
AddAssumption$(ASSUMPTION_STATIC; Loading; Loads are static.; Dynamic effects are outside the defined scope.; RPT_NO_REFERENCE)
EndAssumptions$

BeginLimitations$
AddLimitation$(LIMITATION_TEMPERATURE; Room-temperature properties only.; Elevated-temperature behavior is excluded.; Reassess for elevated temperature.; RPT_NO_REFERENCE)
EndLimitations$

ShowReportingSummary$
```

The public calculation helpers include:

- `ReportRegistryAddStatus`, `ReportRegistryAdd`, `ReportRegistryEntryExists`, and `ReportRegistryCount` for one-column reference registries;
- `ReportLinkedRegistryAddStatus`, `ReportLinkedRegistryAdd`, `ReportLinkedRegistryReference`, and `ReportLinkedRegistryCount` for linked registries;
- `ReportReferenceKnown` for optional and required source-reference checks;
- `ReportErrorRegistryCount` and `ReportRegistriesStatus` for aggregate reporting integrity; and
- `ReportStatus$` and `ShowReportingSummary$` for status rendering.

An invalid registration is not added.
Its attempted row is still rendered with a prominent inline registry error so the source worksheet remains easy to diagnose.
See [`Examples/ReportingRegistriesDemo.cpd`](../Examples/ReportingRegistriesDemo.cpd) for the complete valid workflow and [`Tests/Core/REPORTING_TEST.cpd`](../Tests/Core/REPORTING_TEST.cpd) for duplicate-ID and invalid-reference coverage.

## Calculation status

`CalculationStatus(validation_statuses; check_statuses)` combines input-validation and engineering-check status vectors into one document-level result.
New worksheets should use `CalculationStatusFromRegistries(validation_results; check_registry; check_registry_errors)` or `CalculationStatusFromGlobalRegistries(validation_results)` so the check-status vector cannot drift from the rendered check table.
Its precedence distinguishes incomplete inputs from a completed calculation that fails an engineering requirement:

| Constant | Meaning |
| --- | --- |
| `CALC_PASS` | All validated inputs and engineering checks pass |
| `CALC_WARN` | The calculation is valid but contains a validation or check warning |
| `CALC_FAIL` | At least one completed engineering check fails |
| `CALC_INCOMPLETE` | Validation or engineering-check results are missing, or inputs contain errors |
| `CALC_ERROR` | Validation/check statuses are unknown or a completed check contains an evaluation error |

Use `CalculationStatus$` for an inline label.
Use `ShowCalculationStatusFromRegistries$(validation_results)` for the standard document banner derived from the global validation and check registries.
`ShowCalculationStatus$` remains available when explicit status vectors are required.
`AddCalculationStatusConclusion$` adds the same status to an open conclusions block.
`CalculationCanBeIssued` returns true for pass and warning statuses; the checker must still decide whether each warning is acceptable before issue.
`CalculationValidationStatusesOK`, `CalculationInputsComplete`, and `CalculationChecksComplete` expose the completeness checks used by the aggregate.

## Engineering checks

### Status and predicates

| Function | Result |
| --- | --- |
| `CheckStatusKnown(status)` | Status is one of the four `CHK_*` values |
| `CheckIsPass(status)` | Status is `CHK_PASS` |
| `CheckIsWarning(status)` | Status is `CHK_WARN` |
| `CheckIsFailure(status)` | Status is failure or error |
| `CheckWarningThresholdOK(threshold)` | Threshold is from zero through one |
| `CheckUtilizationOK(utilization)` | Utilization is finite and nonnegative |
| `CheckStatus(utilization; threshold)` | Classify a utilization |

`CHK_DEFAULT_WARNING` is `0.9`.

### Demand and capacity helpers

| Function | Use |
| --- | --- |
| `CheckUpperUtilization(demand; capacity)` | Demand must not exceed capacity |
| `CheckUpperStatus(demand; capacity; threshold)` | Status for an upper-limit check |
| `CheckLowerUtilization(provided; required)` | Provided value must meet a minimum requirement |
| `CheckLowerStatus(provided; required; threshold)` | Status for a lower-limit check |
| `CheckGatedStatus(inputs_valid; status)` | Force `CHK_ERROR` when inputs are invalid or status is unknown |

Capacities and provided values must be positive after units are cleared.

### Aggregation

| Function | Result |
| --- | --- |
| `CheckPassCount(statuses)` | Passing rows |
| `CheckWarningCount(statuses)` | Warning rows |
| `CheckFailureCount(statuses)` | Failed rows |
| `CheckErrorCount(statuses)` | Error and unknown rows |
| `CheckStatusesOK(statuses)` | Nonempty vector containing only known statuses |
| `CheckUtilizationsOK(utilizations)` | Nonempty vector of finite, nonnegative utilizations |
| `CheckSummaryDataOK(statuses; utilizations)` | Valid, matching status and utilization vectors |
| `CheckOverallStatus(statuses)` | Worst meaningful aggregate status |
| `CheckSummaryStatus(statuses; utilizations)` | Aggregate status with shape and utilization validation |
| `CheckGoverningUtilization(utilizations)` | Maximum valid utilization |
| `CheckGoverningIndex(utilizations)` | First index at the maximum utilization |

`CheckWorst`, `CheckNoFailures`, and `CheckAllPass` are compatibility predicates built on `CheckOverallStatus`.
`CheckCount`, `CheckKnownCount`, and `CheckUnknownCount` provide lower-level status counts.

### Structured check registry and reporting

Use `CheckStatus$(status)` for an inline status or `ShowCheck$(label; utilization; status)` for one small standalone table.
For a calculation, register every rendered check as one structured result:

```text
[id; method; demand_or_required; capacity_or_provided; utilization; warning_threshold; status]
```

The constructors are `CheckUpperResult`, `CheckLowerResult`, and `CheckCustomResult`.
The corresponding accessors are `CheckResultID`, `CheckResultMethod`, `CheckResultDemand`, `CheckResultCapacity`, `CheckResultUtilization`, `CheckResultWarning`, and `CheckResultStatus`.
Check IDs must be positive integers and unique within the worksheet.

The generated Core initializes `EngineeringCheckRegistry` and `EngineeringCheckRegistryErrors`.
The registration macros render the human-readable label and acceptance criterion while storing the numeric result used for aggregation:

```text
CHECK_STRESS = 1
CHECK_DEFLECTION = 2

BeginCheckRegistry$
AddUpperCheck$(CHECK_STRESS; Bending stress; bending_stress; allowable_stress; CHK_DEFAULT_WARNING; Demand must not exceed allowable stress.; inputs_valid)
AddUpperCheck$(CHECK_DEFLECTION; Deflection; deflection; allowable_deflection; CHK_DEFAULT_WARNING; Deflection must not exceed the serviceability limit.; inputs_valid)
EndCheckRegistryWithSummary$

ShowCheckIssues$
ShowCalculationStatusFromRegistries$(validation_results)
```

`AddLowerCheck$` handles minimum-required checks and `AddCustomCheck$` stores a caller-calculated utilization and status.
`AddCheckResult$` registers a preconstructed result.
`EndCheckRegistry$` closes the table without an aggregate footer; `EndCheckRegistryWithSummary$` adds counts, overall status, and a link to the governing check.
`ShowCheckIssues$` lists warnings, failures, and errors with links back to their registered rows.

Registry query helpers include `CheckResultRegistryCount`, `CheckResultRegistryEntryExists`, the `CheckResultRegistry*` vector accessors, `CheckResultRegistrySummaryStatus`, `CheckResultRegistryIssueCount`, and the governing-index, governing-ID, and governing-utilization functions.
`CheckResultRegistryEffectiveStatuses` adds `CHK_ERROR` when any attempted registration failed, ensuring registry-integrity failures propagate into calculation status.
When utilizations tie, the first registered row governs.

See [`Examples/CheckRegistryDemo.cpd`](../Examples/CheckRegistryDemo.cpd), [`Tests/Core/CHECKS_TEST.cpd`](../Tests/Core/CHECKS_TEST.cpd), and [`Tests/Core/CALCULATION_STATUS_TEST.cpd`](../Tests/Core/CALCULATION_STATUS_TEST.cpd).

## Validation

### Preferred structured results

Structured constructors return:

```text
[status; value; rule_code; data_1; data_2]
```

The accessors are `ValidationResultStatus`, `ValidationResultValue`, `ValidationResultRule`, `ValidationResultData1`, and `ValidationResultData2`.
`ValidationResultStatus` also rejects malformed, unknown, and stale registered-set results.

The status-only compatibility functions use the same rule names with a `Status` suffix:

- Scalar: `ValidationDefinedStatus`, `ValidationPositiveStatus`, `ValidationNonnegativeStatus`, `ValidationNegativeStatus`, `ValidationNonpositiveStatus`, `ValidationNonzeroStatus`, `ValidationZeroStatus`, `ValidationIntegerStatus`, `ValidationRangeStatus`, `ValidationOpenRangeStatus`, `ValidationOutsideRangeStatus`, `ValidationMinimumStatus`, `ValidationMaximumStatus`, `ValidationAbsoluteMaximumStatus`, `ValidationAllowedStatus`, and `ValidationLengthStatus`.
- Vector: `ValidationVectorRangeStatus`, `ValidationVectorPositiveStatus`, `ValidationVectorNonnegativeStatus`, `ValidationVectorNegativeStatus`, `ValidationVectorNonpositiveStatus`, `ValidationVectorDefinedStatus`, `ValidationIncreasingStatus`, `ValidationNondecreasingStatus`, `ValidationUniqueStatus`, and `ValidationMatchingLengthStatus`.
- Matrix: `ValidationMatrixRowsStatus`, `ValidationMatrixColumnsStatus`, and `ValidationSquareMatrixStatus`.

### Scalar result constructors

| Constructor | Permitted value |
| --- | --- |
| `ValidationDefinedResult(value)` | Defined and finite |
| `ValidationPositiveResult(value)` | Greater than zero |
| `ValidationNonnegativeResult(value)` | At least zero |
| `ValidationNegativeResult(value)` | Less than zero |
| `ValidationNonpositiveResult(value)` | At most zero |
| `ValidationNonzeroResult(value; tolerance)` | Absolute value greater than tolerance |
| `ValidationZeroResult(value; tolerance)` | Absolute value at most tolerance |
| `ValidationIntegerResult(value)` | Integer within `VAL_INTEGER_TOLERANCE` |
| `ValidationRangeResult(value; minimum; maximum)` | Inclusive range |
| `ValidationOpenRangeResult(value; minimum; maximum)` | Exclusive range |
| `ValidationOutsideRangeResult(value; minimum; maximum)` | Outside an inclusive excluded range |
| `ValidationMinimumResult(value; minimum)` | At least the minimum |
| `ValidationMaximumResult(value; maximum)` | At most the maximum |
| `ValidationAbsoluteMaximumResult(value; maximum)` | Absolute value at most the maximum |
| `ValidationAvailableResult(value)` | Available and finite lookup value |
| `ValidationRegisteredResult(value; registered)` | Caller-supplied registration predicate is true |

### Vector and matrix result constructors

| Constructor | Rule |
| --- | --- |
| `ValidationLengthResult(values; minimum; maximum)` | Vector length is within bounds |
| `ValidationVectorRangeResult(values; minimum; maximum)` | Every entry is within an inclusive range |
| `ValidationVectorPositiveResult(values)` | Every entry is positive |
| `ValidationVectorNonnegativeResult(values)` | Every entry is nonnegative |
| `ValidationVectorNegativeResult(values)` | Every entry is negative |
| `ValidationVectorNonpositiveResult(values)` | Every entry is nonpositive |
| `ValidationVectorDefinedResult(values)` | Every entry is finite |
| `ValidationIncreasingResult(values)` | Entries are strictly increasing |
| `ValidationNondecreasingResult(values)` | Entries never decrease |
| `ValidationUniqueResult(values)` | No duplicate entries |
| `ValidationMatchingLengthResult(first; second)` | Vector lengths match |
| `ValidationMatrixRowsResult(matrix; minimum; maximum)` | Row count is within bounds |
| `ValidationMatrixColumnsResult(matrix; minimum; maximum)` | Column count is within bounds |
| `ValidationSquareMatrixResult(matrix)` | Row and column counts match |
| `ValidationMatrixDimensionsResults(matrix; rows; columns)` | Two result rows for an exact shape |

`ValidationLengthResult` checks the number of entries, while `ValidationVectorRangeResult` checks entry magnitudes.

### Allowed-value registry

`ValidationAllowedRegistry` is a global two-column `[set_id; value]` registry.
Set IDs must be positive integers and each set must contain unique values.

```text
ValidationAllowedRegistry = ValidationRegistryAdd(ValidationAllowedRegistry; 101; [1.0; 1.1; 1.4])
factor_result = ValidationAllowedSetResult(factor; 101)
```

Use `ValidationAllowedSetValues`, `ValidationAllowedSetExists`, `ValidationAllowedSetCount`, and `ValidationAllowedSetStatus` to inspect or validate global sets.
The lower-level `ValidationRegistryAdd`, `ValidationRegistryValues`, and related functions can operate on an explicitly passed registry.

### Aggregation and reporting

Stack results with `join_rows`, extract statuses with `ValidationResultsStatuses`, and use `ValidationHasErrors`, `ValidationWarningCount`, `ValidationErrorCount`, or `ValidationOverallStatus` for decisions.

```text
BeginValidationSummary$
AddValidationResult$(Input label; result)
EndValidationResults$(results)
```

`AddValidationRow$` and the scalar `Validation*Status` functions remain available for compatibility, but new worksheets should prefer structured results.
`ShowValidation$` renders one compatibility result table, and `EndValidationSummary$` closes a manually populated summary using an explicit status vector.

### Low-level validation helpers

- Value predicates: `ValidationIsFinite`, `ValidationIsInteger`, `ValidationValuesUnique`, `ValidationStatusKnown`, and `ValidationRuleKnown`.
- Registry helpers: `ValidationRegistryAddStatus`, `ValidationRegistrySetExists`, `ValidationRegistrySetCount`, and `ValidationRegistrySetStatus`.
- Result-integrity helpers: `ValidationResultShapeOK`, `ValidationResultSafe`, `ValidationResultStoredStatus`, `ValidationResultAllowedSetCurrent`, and `ValidationResultRegistryOK`.
- Aggregate helpers: `ValidationWorst`, `ValidationCount`, and `ValidationAllOK`.
- Rendering macros: `ValidationStatus$`, `ValidationSummaryStatus$`, `ValidationPermitted$`, and `ValidationResultValue$`.

## Database and property wrappers

### General table helpers

`Database.cpd` provides:

- `DBColumnOK(table; column)`
- `DBLookupExists(table; key; key_column)`
- `DBLookupStatus(table; key; key_column; value_column)`
- `DBLookupRaw(table; key; key_column; value_column)`
- `DBLookupOr(table; key; key_column; value_column; fallback)`
- `DBMetadataSource(metadata; item)`
- `DBMetadataRevision(metadata; item)`
- `DBRegistryStatus(ids; id)`
- `DBRegistryCount(ids)`

`DBLookupRaw` returns a non-finite value unless the lookup status is `DB_OK`.

### Property and curve helpers

`DataWrapper.cpd` provides stable keys, table lookup, interpolation, range-policy, and status helpers:

- `DBKey(item; property)` combines IDs using `DB_PROPERTY_FACTOR`.
- `DBHasID(ids; id)` tests membership in an ID registry.
- `DBIsMissing(value)`, `DBIsFatal(status)`, and `DBIsWarning(status)` classify stored values and statuses.
- `DBMethodOK(method)` and `DBPolicyOK(bounds_policy)` validate query options.
- `DBTableStatus` and `DBTableRaw` read numeric property tables.
- `DBCurveExists(curve_table; curve_key)` tests for curve rows.
- `DBRangeStatus(x; minimum; maximum; policy)` classifies bounds handling.
- `DBCurveStatus` and `DBCurveRaw` read keyed `[key; x; y]` curve tables.
- `DBLinear` and `DBNearest` implement interpolation selection.
- `DB_STRICT`, `DB_CLAMP`, and `DB_EXTRAPOLATE` select bounds behavior.
- `DBStatus$(status)` renders a status message.

Call the status function and value function separately when a worksheet must report data quality or bounds handling.

## Plotting

Plotting follows an initialize, configure, add traces, render sequence:

```text
figure$(plot_id)
figureSize$(plot_id; 900; 450)
plot$(plot_id; x_values; y_values; #005ea8; Series name)
render$(plot_id; Figure title; X axis; Y axis)
```

### Configuration macros

- Ranges: `xRange$`, `yRange$`, `y2Range$`, `y2Axis$`.
- Legend: `legendTop$`, `legendRight$`, `hideLegend$`.
- Behavior: `hoverUnified$`, `barMode$`, `logX$`, `logY$`.
- Size: `figureSize$`.

### Trace macros

- Lines: `plot$`, `plotY2$`, `plotDashed$`, `plotMarkers$`.
- Points: `scatter$`, `scatterY2$`.
- Filled data: `bar$`, `area$`.

### Shapes and annotations

Use `hline$`, `vline$`, `yBand$`, `xBand$`, and `annotate$` after initialization and before `render$`.

`sampleData$` samples a scalar function into two output vectors.
`sampleParametric$` samples independent x and y functions over a parameter range.
Both enforce a minimum of two points.

Plot values are passed to JavaScript after `clrunits`, so axis labels must state the intended display units.
The current wrapper loads Plotly 2.26.0 from the network.
