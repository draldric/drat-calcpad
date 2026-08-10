# Library-authoring guide

Use `Templates/PropertyLibraryTemplate.cpd` as the starting point for a numeric property library.

## Loading contract

Libraries never include Core or another library.
The consuming worksheet must load every dependency directly and in order:

```text
#include ../Core/DratCore.cpd
#include ../Libraries/Example/ExampleProperties.cpd
```

Wrap the entire library body in Core and component API guards:

```text
#if and(DRAT_CORE_API ≥ 10000; DRAT_CORE_API < 20000)
#if and(DRAT_DATA_WRAPPER_API ≥ 302; DRAT_DATA_WRAPPER_API < 1000)
#hide

'<!-- Library definitions. -->

#show
#else
'<div class="library-load-error"><strong>DRAT library load error:</strong> This library requires DataWrapper API 0.3.2 or newer.</div>
#end if
#else
'<div class="library-load-error"><strong>DRAT library load error:</strong> This library requires DRAT core API 1.x.</div>
#end if
```

Choose the narrowest compatible ranges the library actually supports.
If a guard fails, skip every dependent definition and render a concise compatibility message.

## Required metadata

Publish readable library metadata as macros:

```text
#def ExampleLibraryName$ = Example Property Library
#def ExampleLibraryRevision$ = 1.0.0
#def ExampleLibraryDate$ = 2026-08-09
#def ExampleLibraryScope$ = Describe the dataset, conditions, and exclusions.
```

The scope must say whether values are typical, screening, minimum specified, or design allowables.
It must also state material condition, temperature assumptions, and other important applicability limits.

## Stable identifiers

Use stable numeric constants for items and properties, plus readable aliases:

```text
ITEM_A = 101
Item_A = ITEM_A

EX_P_DENSITY = 1
EX_DENSITY = EX_P_DENSITY

ExampleItemIDs = [101]
ExamplePropertyIDs = [1]
```

Do not reuse a published ID for a different meaning.
Aliases may be added without changing the underlying ID.

Use a library-specific prefix for public identifiers to avoid collisions when several libraries are loaded.

## Numeric data model

### Constant property tables

A constant-property table normally uses one row per item and one column per property:

```text
ExampleData = [item_id; property_1; property_2]
```

Use `DB_MISSING` where a property is unavailable.
Never substitute zero for missing engineering data unless zero is the documented physical value.

### Curves

A curve table uses `[curve_key; x; y]` rows:

```text
ExampleCurveData = [DBKey(item; property); x_1; y_1|DBKey(item; property); x_2; y_2]
```

Curves require at least two points.
Keep x values ordered and ensure x and y vectors have matching lengths.

### Metadata and provenance

Store enough metadata to reproduce and review each property result.
At minimum, retain source ID and dataset revision.
For curves, also retain valid minimum and maximum query values.

The Engineering Materials library uses one metadata row per material because all properties for that record currently share a source and revision.
Use per-property metadata when sources or revisions differ by property.
Its category and availability indexes are derived from the same material and property registries used by public lookups.
Its current populated values are classified as screening data; stronger classifications require supporting source data rather than a reporting-only label change.

## Public lookup contract

Expose a status function and a value function:

```text
ExamplePROPStatus(item; property) = ...
ExamplePROP(item; property) = ...
```

The status function must distinguish unknown items, unknown properties, missing values, invalid methods, and out-of-range behavior.
The value function must return a non-finite result for fatal statuses.

Apply units only at the public boundary:

```text
ExampleApplyUnits(property; value) = switch(
    property ≡ EX_P_DENSITY; setunits(value; kg/m^3);
    0/0)
```

Store raw table values in documented units and keep the conversion mapping in one function.

Convenience functions may wrap property IDs:

```text
ExampleDensity(item) = ExamplePROP(item; EX_P_DENSITY)
```

## Reporting contract

Provide macros that report:

- Library name, revision, date, and scope.
- Selected item name and numeric ID.
- Property name, units, value, and lookup status.
- Source and data revision.
- Valid query range and bounds handling when applicable.

Keep calculation and reporting tied to the same IDs and lookup functions.
Do not duplicate property values inside display macros.

## Testing

Add a deterministic worksheet under `Tests/Core/` for reusable Core changes or under `Tests/Libraries/` for library behavior.
Cover:

- Nominal lookup.
- Every public alias that is part of the contract.
- Unknown item and property IDs.
- Missing data.
- Units.
- Source and revision metadata.
- Strict, clamp, and extrapolate policies for curves.
- Minimum supported Core and component APIs.
- Rendered compatibility errors for incompatible APIs.

Add or update a complete example when introducing a new public library workflow.

Run `Tools/VerifyRepository.ps1` and manually render the affected example in the CalcPad CE GUI before requesting review.
