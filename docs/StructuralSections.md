# Structural Sections Library

`Libraries/Steel/StructuralSections.cpd` provides tabulated geometric properties for the 289 W-shapes in the AISC Shapes Database v16.0.
`Libraries/Steel/AiscHssSections.cpd` provides the 714 square, rectangular, and round HSS records from the same source.
`Libraries/Steel/AiscChannelSections.cpd` provides the 32 standard C and 40 miscellaneous MC channels.
`Libraries/Steel/AiscAngleSections.cpd` provides 137 single-angle L sections; double angles are intentionally excluded.
Load the generated Core first, then load the library directly from the worksheet:

```text
#include ../Core/DratCore.cpd
#include ../Libraries/Steel/StructuralSections.cpd
#include ../Libraries/Steel/AiscHssSections.cpd
#include ../Libraries/Steel/AiscChannelSections.cpd
#include ../Libraries/Steel/AiscAngleSections.cpd
```

## Scope and provenance

The initial release contains the AISC W-shape, HSS, C/MC channel, and single-angle families in US customary units.
Each record stores nominal weight, area, dimensions, strong- and weak-axis elastic and plastic section properties, radii of gyration, and torsional properties.

`StructuralSectionsLibrarySource$`, `StructuralSectionsLibraryRevision$`, and `StructuralSectionsLibraryScope$` expose the dataset basis in a worksheet.
The source basis is the AISC Shapes Database v16.0, August 2023. The official workbook used to prepare and qualify the DRAT compilation has SHA-256 `82d0ceb96a0d938ae1a6bd9637cb10a1e269225b5d668dce5b0bdc8d86013496`.

The official workbook is neither committed nor redistributed. DRAT maintains `Data/Sources/AiscShapesV16/DratStructuralSectionsSource.xlsx`, its own family-sheet compilation of the factual values used by these APIs. It contains only the supported W, HSS, C/MC channel, and single-angle records and the properties listed below. See the [dataset provenance audit](DataProvenance.md).

This is a geometric-property lookup library only.
It does not provide steel grade, material strength, member resistance, connection resistance, load combinations, or a code-based design check.
Verify the selected section and governing AISC edition against the project requirements before design use.

## Lookup API

Use either the AISC-prefixed identifier or the short designation alias:

```text
selected_section = W14X90
area = AiscWArea(selected_section)
Sx = AiscWSx(selected_section)
```

The stable property IDs are:

- `AISC_W_P_WEIGHT`, `AISC_W_P_AREA`
- `AISC_W_P_D`, `AISC_W_P_BF`, `AISC_W_P_TW`, `AISC_W_P_TF`
- `AISC_W_P_IX`, `AISC_W_P_ZX`, `AISC_W_P_SX`, `AISC_W_P_RX`
- `AISC_W_P_IY`, `AISC_W_P_ZY`, `AISC_W_P_SY`, `AISC_W_P_RY`
- `AISC_W_P_J`, `AISC_W_P_CW`

`AiscWProperty(item; property)` returns a unit-aware value.
`AiscWPropertyStatus(item; property)` returns `DB_OK`, `DB_ERR_NAME`, `DB_ERR_PROPERTY`, or a missing-value status.
`AiscWPropertyRaw(item; property)` is available for sorting and other programmatic operations in the documented source units.

Use `AiscWItemsAtLeast(property; minimum)` to make a transparent unit-aware screening list:

```text
candidate_sections = AiscWItemsAtLeast(AISC_W_P_SX; 140in^3)
```

The selector does not establish adequacy.
It only returns records satisfying the stated geometric-property threshold.

The HSS module follows the parallel `AiscHss*` API.
Use identifiers such as `HSS12X8X3_8` for the AISC label `HSS12X8X3/8`, and `HSS12P750X0P375` for `HSS12.750X0.375`.
`AiscHssProperty`, `AiscHssPropertyStatus`, and `AiscHssItemsAtLeast` provide the same unit-aware lookup, status, and screening behavior.
HSS-specific property IDs include `AISC_HSS_P_HT`, `AISC_HSS_P_B`, `AISC_HSS_P_OD`, and `AISC_HSS_P_TDES`.
Height and width are unavailable for round HSS, while outside diameter is unavailable for square and rectangular HSS; the corresponding status is `DB_ERR_MISSING`.

The channel module follows the parallel `AiscChannel*` API and supports both `C15X50` and `MC12X50` aliases.
In addition to dimensions and conventional section properties, it provides centroid x-coordinate (`AISC_CHANNEL_P_X`) and shear-center eccentricity (`AISC_CHANNEL_P_EO`) for this asymmetric family.

## Reporting

- `ShowAiscWDatasetSummary$` reports library scope, source, record count, and dataset status.
- `ShowAiscWRecord$(item)` reports one selected section and its provenance.
- `ShowAiscWProperties$(item)` renders all tabulated properties for one selected section.
- `ShowAiscHssDatasetSummary$`, `ShowAiscHssRecord$(item)`, and `ShowAiscHssProperties$(item)` provide corresponding HSS reports.
- `ShowAiscChannelDatasetSummary$`, `ShowAiscChannelRecord$(item)`, and `ShowAiscChannelProperties$(item)` provide the matching channel reports.
- `ShowAiscAngleDatasetSummary$`, `ShowAiscAngleRecord$(item)`, and `ShowAiscAngleProperties$(item)` provide the matching single-angle reports.

All values in the reporting tables are right aligned, while descriptions remain left aligned.
The full worksheet example is `Examples/StructuralSectionsDemo.cpd`.

## Regeneration and verification

`Tools/GenerateAiscWLibrary.py`, `Tools/GenerateAiscHssLibrary.py`, `Tools/GenerateAiscChannelLibrary.py`, and `Tools/GenerateAiscAngleLibrary.py` are the auditable source-data transformations for the committed CalcPad libraries.
They validate the repository workbook's dataset revision, exact property contract, stable IDs, columns, numeric cells, unique labels, and family counts before generating. Output is written to a verified temporary file and atomically replaces the maintained library only after validation succeeds. `--check` is read-only.
The curated source workbook is committed under `Data/Sources/` and excluded from runtime packages. The official AISC workbook is not committed.

Run `Tests/Libraries/Steel/StructuralSectionsTest.cpd`, `Tests/Libraries/Steel/AiscHssSectionsTest.cpd`, and `Tests/Libraries/Steel/AiscChannelSectionsTest.cpd` in CalcPad CE and confirm `all_tests` is true.
The regression tests lock record count, data-table dimensions, aliases, representative AISC values, lookup statuses, and unit-aware `Sx` screening queries.
