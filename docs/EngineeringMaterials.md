# Engineering Materials Library

`Libraries/Materials/EngineeringMaterials.cpd` provides nominal room-temperature screening values for common engineering materials.
Load the generated Core first, then load the library directly from the worksheet:

```text
#include ../Core/DratCore.cpd
#include ../Libraries/Materials/EngineeringMaterials.cpd
```

## Discovery

The catalog exposes stable numeric material, category, and property IDs.
Use the discovery helpers to inspect the dataset before selecting a value:

```text
glass_materials = MatItemsByCategory(MAT_CAT_GLASS)
a36_properties = MatAvailablePropertyIDs(STEEL_ASTM_A36)
yield_materials = MatItemsWithProperty(MAT_P_YIELD_STRENGTH)
```

The public discovery functions are:

- `MatCategory(item)` and `MatCategoryStatus(item)` return a material's category and lookup status.
- `MatItemsByCategory(category)` and `MatCategoryCount(category)` filter the catalog by category.
- `MatAvailablePropertyIDs(item)` and `MatAvailablePropertyCount(item)` report populated properties for one material.
- `MatItemsWithProperty(property)` and `MatPropertyAvailableCount(property)` report materials with a populated property.
- `MatPropertyAvailable(item; property)` tests one material-property pair.
- `MatItemCompleteness(item)` and `MatPropertyCompleteness(property)` return ratios from zero to one for valid IDs.

Unknown category and property filters return empty vectors.
Use the corresponding status functions when an unknown ID must be distinguished from an empty result.

## Candidate selection and ranking

Build candidate lists from a category and the properties that must be populated:

```text
required_properties = [MAT_P_DENSITY; MAT_P_YOUNGS_MODULUS; MAT_P_YIELD_STRENGTH]
steel_candidates = MatCandidateItems(MAT_CAT_FERROUS_METAL; required_properties)
candidate_status = MatCandidateStatus(MAT_CAT_FERROUS_METAL; required_properties)
```

Use `MAT_CAT_ALL` when the search should span every category.
`MatCandidateCount` returns the number of matching records, while `MatCandidateStatus` distinguishes a valid result from an unknown category, invalid property set, or a valid search with no populated candidates.
Every candidate must have a populated value for every requested property.

Rank candidates by one populated property with `MatRankCandidates` or use `MatRankByProperty` when no additional required-property filter is needed:

```text
ranking = MatRankCandidates(MAT_CAT_FERROUS_METAL; required_properties; MAT_P_YIELD_STRENGTH; MAT_RANK_DESCENDING)
ranking_status = MatRankingResultStatus(ranking)
ranked_items = MatRankedItems(ranking)
ranked_raw_values = MatRankedRawValues(ranking)
```

The ranking result contains one `[status; material_id; raw_property_value]` row per candidate.
The raw property value uses the dataset's documented unit and is intended for sorting and programmatic access; use `MatPROP` or the reporting macros for unit-aware displayed values.
An invalid ranking request returns one status row, so check `MatRankingResultStatus` before consuming its item or value columns.

The supported directions are `MAT_RANK_ASCENDING` and `MAT_RANK_DESCENDING`.
Use `MatItemsAtLeast`, `MatItemsAtMost`, and `MatItemsBetween` for unit-aware property thresholds:

```text
high_yield_steel = MatItemsAtLeast(MAT_CAT_FERROUS_METAL; MAT_P_YIELD_STRENGTH; 1000MPa)
service_range = MatItemsBetween(MAT_CAT_ALL; MAT_P_MAX_SERVICE_TEMPERATURE; 100°C; 250°C)
```

Thresholds must be dimensionally compatible with the selected property.
These helpers return empty vectors for invalid requests or an empty result; use the ranking and property status helpers when the reason must be reported separately.
Selection and ranking are transparent screening operations only.
The library does not calculate a hidden weighted score or identify a universally best material; project-specific constraints, governing standards, environment, fabrication, availability, and verified design values still control final selection.

## Categories

The initial category registry contains:

- `MAT_CAT_FERROUS_METAL`
- `MAT_CAT_NONFERROUS_METAL`
- `MAT_CAT_POLYMER`
- `MAT_CAT_ELASTOMER`
- `MAT_CAT_GLASS`
- `MAT_CAT_CERAMIC_RELATED`
- `MAT_CAT_COMPOSITE`
- `MAT_CAT_WOOD`
- `MAT_CAT_CONSTRUCTION`

`EngineeringMaterialCatalog` stores `[material_id; category_id]` rows.
`EngineeringMaterialItemIDs`, `EngineeringMaterialCategoryIDs`, and `EngineeringMaterialPropertyIDs` provide the stable registries used by the discovery functions.

## Engineering-value classification

Every populated value in the current dataset is classified as `MAT_CLASS_SCREENING`.
Missing values return `MAT_CLASS_UNKNOWN`.
The registry also reserves `MAT_CLASS_TYPICAL`, `MAT_CLASS_SPECIFIED_MINIMUM`, and `MAT_CLASS_DESIGN_ALLOWABLE` for datasets that can substantiate those meanings.

Use `MatClassification(item; property)` to retrieve the classification and `MatClassificationStatus(item; property)` to distinguish a valid classification from an unknown item, unknown property, or missing value.
A screening value is not a specified minimum or a design allowable and must be checked against the governing code, specification, certificate, or approved project data before design use.

## Provenance and integrity

The repository-owned workbook is maintained at `Data/Sources/EngineeringMaterials/EngineeringMaterialsDatabase.xlsx` and is excluded from runtime distributions. `Tools/ValidateEngineeringMaterialsSource.py` validates its worksheets, IDs, numeric types, derived moduli, source links, missing values, and complete CPD numeric export.

The current workbook provides one broad source portal per material row, not an edition and locator for every populated property. Consequently, `MatProvenanceStatus` proves that a record has a known internal source ID and revision; it does not independently certify that each value was traced to a specific source record. This gap is a first-release blocker documented in the [dataset provenance audit](DataProvenance.md).

`MatProvenanceStatus(item)` validates the source and dataset revision for a material record.
`MatPropertyProvenanceStatus(item; property)` applies that validation to an available property.
`MatPropertyRecordStatus(item; property)` combines value availability, category, provenance, and classification checks into one status.

The library calculates these dataset-wide checks when it loads:

- `EngineeringMaterialCatalogOK`
- `EngineeringMaterialCategoriesOK`
- `EngineeringMaterialSourcesOK`
- `EngineeringMaterialRevisionsOK`
- `EngineeringMaterialClassificationsOK`
- `EngineeringMaterialCompletenessOK`
- `EngineeringMaterialDatasetStatus`

`EngineeringMaterialPropertyAvailableCounts`, `EngineeringMaterialAvailableValueCount`, `EngineeringMaterialPossibleValueCount`, and `EngineeringMaterialDatasetCompleteness` make coverage auditable.
The regression worksheet locks the expected counts so a changed record layout, category boundary, or missing-value pattern is visible during verification.

## Reporting tables

The predefined reporting macros are:

- `ShowMatDatasetSummary$` for library scope, coverage, classification, and overall status.
- `ShowMatCatalog$` for the complete material catalog.
- `ShowMatCategory$(category)` for a category-filtered material table.
- `ShowMatProperties$` for property coverage and classification.
- `ShowMatRecord$(item)` for one selected material record.
- `ShowMatPROP$(item; property)` for one retrieved property, its classification, revision, and source.
- `ShowMatRanking$(ranking_result; property; limit)` for a ranked candidate table.
- `ShowMatComparison$(items; properties)` for a side-by-side property comparison.
- `ShowMatPropertyComparisonPlot$(id; items; property)` for a horizontal single-property comparison.
- `ShowMatPropertyTradeoffPlot$(id; items; x_property; y_property)` for an x-y trade-off scatter plot.

`ShowMatCatalog$` renders all 126 records and is intended for catalog review or dedicated reference sheets.
Use `ShowMatCategory$` in ordinary calculations when a shorter selection table is more useful.
Assign item and property vectors to variables before passing them to reporting macros; inline vector semicolons can be interpreted as macro argument separators by CalcPad.

## Property comparison plots

Use the same explicit item vector for the table and plots so the reported shortlist remains auditable:

```text
plot_items = first(MatRankedItems(ranking); 5)

#novar
ShowMatPropertyComparisonPlot$(yieldComparison; plot_items; MAT_P_YIELD_STRENGTH)
ShowMatPropertyTradeoffPlot$(densityYieldTradeoff; plot_items; MAT_P_DENSITY; MAT_P_YIELD_STRENGTH)
#equ
```

Each plot ID must be unique within the rendered worksheet.
The comparison plot uses documented raw dataset units and states those units on its axis.
The trade-off plot requires every selected material to contain both requested properties.
Plot requests fail visibly for empty item vectors, unknown material or property IDs, and missing property values; they do not silently drop incomplete records.

Plots load Plotly from the network through Core, so an online connection is required when the worksheet renders.
Engineering Materials 1.4 requires Plotting API 3.2 or newer in the loaded Core bundle.
Hover labels include the material name and stable material ID.
As with the tables and ranking helpers, plots compare screening values and do not select a design material automatically.
