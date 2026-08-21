# Engineering Materials source record

## Identification

- Repository input: `EngineeringMaterialsDatabase.xlsx`
- Repository revision: 1.0.0, dated 2026-08-07 inside the workbook
- Coverage: 126 material records, 18 properties, and 2,011 populated material-property values
- Classification: screening values only
- Reference condition: nominal or representative values near 20-25 C unless a record note states otherwise

## Ownership and packaging

The workbook is the repository-maintained compilation input. It is not needed at CalcPad runtime and is excluded from runtime distributions. The generated `Libraries/Materials/EngineeringMaterials.cpd` is the only packaged artifact.

## Provenance qualification

Each material record identifies one broad source and URL. That row-level link is useful for source discovery but does not identify an edition, table, page, product-data-sheet revision, or individual property record for every populated value. The current workbook therefore does not yet provide a complete auditable provenance path for all 2,011 values.

All populated values remain classified as `MAT_CLASS_SCREENING`. None may be represented as a specified minimum, certified property, or design allowable. Missing cells remain blank in the workbook and `DB_MISSING` in CalcPad; they must not be inferred or replaced by zero.

Before this dataset can pass the first-release provenance gate, each retained value or defensible property group needs a record-level citation with source revision and locator. Values that cannot be supported and redistributed must be removed. The detailed release disposition is tracked in `docs/DataProvenance.md`.

## Workbook schema

Required worksheets are `Dataset Contract`, `README`, `Materials`, `Property Dictionary`, `Sources`, `Categories`, `Aliases`, `CPD Numeric Export`, `Selector`, and `QA`. The contract identifies every generator-owned sheet and the generated-library metadata. Material and property IDs must be unique and stable. Numeric export order must match the property dictionary. Formula-derived shear and bulk moduli are allowed only for isotropic rows and use the documented `E` and Poisson-ratio relationships.

Routine record maintenance is workbook-only: add or update the `Materials` row and matching `CPD Numeric Export` row, then run the generator. Categories and public aliases are maintained on their own sheets. The validator derives record and populated-value counts and validates the entire workbook before the generator atomically replaces `Libraries/Materials/EngineeringMaterials.cpd`.

```powershell
python Tools/GenerateEngineeringMaterialsLibrary.py Data/Sources/EngineeringMaterials/EngineeringMaterialsDatabase.xlsx Libraries/Materials/EngineeringMaterials.cpd
python Tools/GenerateEngineeringMaterialsLibrary.py Data/Sources/EngineeringMaterials/EngineeringMaterialsDatabase.xlsx Libraries/Materials/EngineeringMaterials.cpd --check
```
