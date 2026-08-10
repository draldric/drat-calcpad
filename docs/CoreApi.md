# Core API reference

This reference summarizes the supported public surface in `Core/DratCore.cpd`.
Internal block variables and names beginning with `ζ` are implementation details.

Function arguments are separated with semicolons in CalcPad syntax.
Macro names end with `$`.

## Compatibility manifest

`CoreManifest.cpd` publishes:

| Name | Current value | Purpose |
| --- | ---: | --- |
| `DRAT_CORE_API` | `10600` | Complete generated-Core API |
| `DRAT_DEFINITIONS_API` | `10201` | Worksheet reporting definitions |
| `DRAT_STYLESHEET_API` | `10400` | Shared rendered styles |
| `DRAT_PLOTTING_API` | `30200` | Plotly wrapper |
| `DRAT_DATA_WRAPPER_API` | `302` | Numeric property and curve wrapper |
| `DRAT_CHECKS_API` | `10200` | Engineering checks and summaries |
| `DRAT_DATABASE_API` | `10000` | General table and metadata lookups |
| `DRAT_VALIDATION_API` | `10400` | Structured input validation |

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
| `BeginReferences$` | `AddReference$(reference)` | `EndReferences$` | Numbered reference list |
| `BeginRevisions$` | `AddRevision$(revision; description; author; date)` | `EndRevisions$` | Revision-history table |
| `BeginInitialConditions$` | `AddInitialCondition$(condition)` | `EndInitialConditions$` | Design-basis list |
| `BeginListSection$(heading)` | `AddListItem$(item)` | `EndListSection$` | H4 subsection list |
| `BeginVariables$` | `AddVariable$(symbol; description; units)` | `EndVariables$` | Rendered variable table |
| `BeginConclusions$` | `AddConclusion$(label; value)` | `EndConclusions$` | Conclusions block |

`AddValidationConclusion$(label; status)` and `AddCheckConclusion$(label; status)` add rendered statuses to an open conclusions block.

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

### Reporting

Use `CheckStatus$(status)` for an inline status or `ShowCheck$(label; utilization; status)` for a small table.
For a calculation summary:

```text
BeginCheckSummary$
AddCheckRow$(label; demand; capacity; utilization; warning_threshold; criterion; status)
EndCheckSummaryWithResult$(statuses; utilizations; governing_label)
```

Use `EndCheckSummary$` when aggregate counts and governing results are not required.
The caller supplies `governing_label`; `CheckGoverningIndex` selects the first row when utilizations tie.

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
