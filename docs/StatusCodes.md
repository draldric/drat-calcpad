# Status-code reference

Status codes are numeric so they can be stored in CalcPad vectors and matrices.
Use the associated predicate or rendering macro instead of embedding numeric literals in worksheets.

## Document calculation status

| Constant | Value | Meaning |
| --- | ---: | --- |
| `CALC_PASS` | 0 | Inputs are valid and every engineering check passes |
| `CALC_WARN` | 10 | The calculation is valid with one or more warnings |
| `CALC_FAIL` | 20 | At least one engineering check fails |
| `CALC_INCOMPLETE` | 30 | Validation/check results are missing, or input validation contains errors |
| `CALC_ERROR` | 40 | A status is unknown or an engineering check contains an evaluation error |

`CalculationStatus` derives the document status from validation and check vectors.
`CalculationStatusFromRegistries` and `CalculationStatusFromGlobalRegistries` derive the check vector and registry-integrity state from structured check results.
Invalid inputs produce `CALC_INCOMPLETE` even when their gated engineering checks return `CHK_ERROR`.
This keeps an unfinished worksheet distinct from a valid calculation that fails its acceptance criteria.

## Engineering checks

| Constant | Value | Meaning |
| --- | ---: | --- |
| `CHK_PASS` | 0 | Utilization is below the warning threshold |
| `CHK_WARN` | 10 | Utilization is at or above the warning threshold and not above one |
| `CHK_FAIL` | 20 | Utilization is above one |
| `CHK_ERROR` | 30 | Inputs, status, utilization, or summary data are invalid |

`CheckStatusKnown` identifies the four defined codes.
`CheckStatus$` renders their user-facing labels.

Aggregate precedence is error, fail, warning, then pass.
Unknown status values count as errors.

## Check registry integrity

| Constant | Value | Meaning |
| --- | ---: | --- |
| `CHECK_REG_OK` | 0 | Check result was registered successfully |
| `CHECK_REG_ERR_BAD_REGISTRY` | 10 | Existing registry has an invalid shape or sentinel row |
| `CHECK_REG_ERR_BAD_RESULT` | 20 | Structured result is malformed or incompatible with the rendered row |
| `CHECK_REG_ERR_BAD_ID` | 30 | Check ID is not a positive integer |
| `CHECK_REG_ERR_DUPLICATE_ID` | 40 | Check ID is already registered |
| `CHECK_REG_ERR_BAD_METHOD` | 50 | Check method is not upper, lower, or custom |

`CheckRegistryErrorCount` and `CheckRegistryErrorsOK` summarize attempted registrations.
Any registry error contributes an effective `CHK_ERROR`, so it propagates to the check summary and document calculation status even though the invalid result is not added.

## Input validation

| Constant | Value | Meaning |
| --- | ---: | --- |
| `VAL_OK` | 0 | Validation passed |
| `VAL_WARN` | 10 | Validation passed with a warning |
| `VAL_ERR_UNDEFINED` | 20 | Value is undefined or non-finite |
| `VAL_ERR_BELOW_RANGE` | 21 | Value is below a permitted bound |
| `VAL_ERR_ABOVE_RANGE` | 22 | Value is above a permitted bound |
| `VAL_ERR_BAD_RANGE` | 23 | Rule bounds or tolerance are invalid |
| `VAL_ERR_NONPOSITIVE` | 24 | Positive value required |
| `VAL_ERR_NEGATIVE` | 25 | Nonnegative value required |
| `VAL_ERR_NOT_INTEGER` | 26 | Integer value required |
| `VAL_ERR_LENGTH` | 27 | Vector length, matrix extent, or matching length is invalid |
| `VAL_ERR_NOT_ALLOWED` | 28 | Value is absent from the permitted set |
| `VAL_ERR_UNKNOWN` | 29 | Aggregate validation contains an error or status is unknown |
| `VAL_ERR_BAD_RESULT` | 30 | Structured result is malformed or incompatible |
| `VAL_ERR_BAD_SET` | 31 | Permitted set is invalid, duplicated, missing, or changed |
| `VAL_ERR_NOT_REGISTERED` | 32 | Value is not registered |
| `VAL_ERR_NONNEGATIVE` | 33 | Negative value required |
| `VAL_ERR_POSITIVE` | 34 | Nonpositive value required |
| `VAL_ERR_ZERO` | 35 | Nonzero value required outside a tolerance |
| `VAL_ERR_DIMENSIONS` | 36 | Matrix dimensions are invalid |
| `VAL_ERR_ORDER` | 37 | Vector ordering is invalid |
| `VAL_ERR_DUPLICATE` | 38 | Vector contains duplicates |
| `VAL_ERR_INSIDE_RANGE` | 39 | Value lies inside an excluded range |
| `VAL_ERR_NONZERO` | 40 | Zero value required within a tolerance |

`ValidationStatusKnown` identifies defined codes.
`ValidationIsError` treats values of 20 or greater as errors.
`ValidationStatus$` renders the detailed user-facing result.

## Database and property lookup

| Constant | Value | Meaning |
| --- | ---: | --- |
| `DB_OK` | 0 | Lookup or interpolation succeeded |
| `DB_ERR_NAME` | 10 | Item name or ID is unknown |
| `DB_ERR_PROPERTY` | 11 | Property name or ID is unknown |
| `DB_ERR_MISSING` | 12 | Required property or curve value is missing |
| `DB_ERR_BELOW_RANGE` | 13 | Strict query is below the valid range |
| `DB_ERR_ABOVE_RANGE` | 14 | Strict query is above the valid range |
| `DB_ERR_BAD_COLUMN` | 15 | Requested table column is invalid |
| `DB_ERR_BAD_METHOD` | 16 | Interpolation method is unsupported |
| `DB_ERR_INSUFFICIENT_DATA` | 17 | Curve has fewer than two usable points |
| `DB_ERR_BAD_POLICY` | 18 | Bounds policy is unsupported |
| `DB_ERR_BAD_RANGE` | 19 | Declared valid range is invalid |
| `DB_WARN_CLAMP_LOW` | 20 | Query was clamped to the lower bound |
| `DB_WARN_CLAMP_HIGH` | 21 | Query was clamped to the upper bound |
| `DB_WARN_EXTRAP_LOW` | 22 | Query was extrapolated below the range |
| `DB_WARN_EXTRAP_HIGH` | 23 | Query was extrapolated above the range |

`DBIsFatal` identifies errors from 10 through 19.
`DBIsWarning` identifies values of 20 or greater.
`DBStatusKnown` and `DBStatus$` validate and render the codes.

`DB_MISSING` is an internal numeric sentinel, not a display value.
Public lookup functions return a non-finite value for fatal results and require the caller to retain the separate status for reporting.

## Bounds and interpolation policies

| Constant | Value | Behavior |
| --- | ---: | --- |
| `DB_NEAREST` | 0 | Use the nearest curve point |
| `DB_LINEAR` | 1 | Linearly interpolate or extrapolate |
| `DB_STRICT` | 0 | Reject out-of-range queries |
| `DB_CLAMP` | 1 | Evaluate at the nearest valid bound and return a warning |
| `DB_EXTRAPOLATE` | 2 | Evaluate outside the valid range and return a warning |

Warnings remain valid numerical results, but the engineering worksheet must decide whether clamping or extrapolation is acceptable for its governing method.
