# Engineering Materials source record

## Identification

- Repository input: `EngineeringMaterialsDatabase.xlsx`
- Repository revision: 1.3.0, dated 2026-08-23 inside the workbook
- Coverage: 126 material records, 18 properties, and 1,993 populated material-property values
- Classification: screening values only
- Reference condition: nominal or representative values near 20-25 C unless a record note states otherwise

## Ownership and packaging

The workbook is the repository-maintained compilation input. It is not needed at CalcPad runtime and is excluded from runtime distributions. The generated `Libraries/Materials/EngineeringMaterials.cpd` is the only packaged artifact.

## Provenance qualification

The `Property Provenance` sheet contains exactly one row for every populated value and links it to the `Citations` registry. Most migrated records remain explicitly level 1 `Source-only`: the broad portal is useful for discovery, but does not identify an edition, table, page, product-data-sheet revision, or individual property record. Forta DX 2205 has 12 level 3 property records, while Core 304/4301 and Core 304L/4307 add 18, all tied to stable Outokumpu datasheet revisions and exact tables. The workbook therefore distinguishes complete mapping coverage from citation qualification.

For Forta DX 2205, the workbook now uses ASTM A240 plate, sheet, and strip minimums from Outokumpu Table 6 and physical properties from Tables 9 and 11. Tensile strength, thermal conductivity, and resistivity were corrected to the cited values. Unsupported fracture toughness, transition temperature, maximum service temperature, and Vickers hardness values were removed rather than inferred.

For Core 304/4301 and Core 304L/4307, the workbook uses EN 10088-2 solution-annealed cold-rolled coil and sheet properties from Outokumpu Table 5 and room-temperature physical properties from Table 7. The single tensile-strength field stores the cited range lower bound. Fourteen unsupported legacy values were removed across the pair, including Poisson-derived shear and bulk moduli.

All populated values remain classified as `MAT_CLASS_SCREENING`. None may be represented as a specified minimum, certified property, or design allowable. Missing cells remain blank in the workbook and `DB_MISSING` in CalcPad; they must not be inferred or replaced by zero.

Before this dataset can pass its current level 3 release gate, each retained value needs a property-record citation with source revision and locator. A defensible property group can be recorded at level 2 if the contract's release threshold is deliberately changed. Values that cannot be supported and redistributed must be removed. The detailed release disposition is tracked in `docs/DataProvenance.md`.

## Workbook schema

Required worksheets are `Dataset Contract`, `README`, `Materials`, `Property Dictionary`, `Sources`, `Citations`, `Property Provenance`, `Categories`, `Aliases`, `CPD Numeric Export`, `Selector`, and `QA`. The contract identifies every generator-owned sheet, the generated-library metadata, and the release provenance threshold. Material, property, source, and citation IDs must be stable. Numeric export order must match the property dictionary. Formula-derived shear and bulk moduli are allowed only for isotropic rows and use the documented `E` and Poisson-ratio relationships.

Routine record maintenance is workbook-only: add or update the `Materials` row, matching `CPD Numeric Export` row, and provenance rows for every populated property, then run the generator. Citations, categories, and public aliases are maintained on their own sheets. The validator derives record and populated-value counts, requires exact provenance coverage, and validates the entire workbook before the generator atomically replaces `Libraries/Materials/EngineeringMaterials.cpd`.

```powershell
python Tools/GenerateEngineeringMaterialsLibrary.py Data/Sources/EngineeringMaterials/EngineeringMaterialsDatabase.xlsx Libraries/Materials/EngineeringMaterials.cpd
python Tools/GenerateEngineeringMaterialsLibrary.py Data/Sources/EngineeringMaterials/EngineeringMaterialsDatabase.xlsx Libraries/Materials/EngineeringMaterials.cpd --check
python Tools/ValidateEngineeringMaterialsSource.py Data/Sources/EngineeringMaterials/EngineeringMaterialsDatabase.xlsx --release
```
