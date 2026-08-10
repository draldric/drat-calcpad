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

`ShowMatCatalog$` renders all 126 records and is intended for catalog review or dedicated reference sheets.
Use `ShowMatCategory$` in ordinary calculations when a shorter selection table is more useful.
