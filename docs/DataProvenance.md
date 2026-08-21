# Engineering dataset provenance and release disposition

This audit covers every distributed DRAT engineering dataset as of 2026-08-20. A dataset status of `DB_OK` proves the embedded table's internal shape and IDs; it does not prove technical accuracy, legal redistribution rights, or design applicability.

## Dataset inventory

| Runtime dataset | Source and revision | Raw-input disposition | Generated-output disposition | Qualification state |
|---|---|---|---|---|
| Engineering Materials 1.4.0 | Repository workbook 1.0.0, 2026-08-07; 11 row-level source portals | Committed under `Data/Sources/EngineeringMaterials`; excluded from runtime packages | Packaged as screening data | Blocked: property-level citations and source revisions are incomplete |
| AISC W shapes 0.1.0 | DRAT structural-section source 1.0.0; values based on AISC Shapes Database v16.0, August 2023 | Repository workbook committed under `Data/Sources/AiscShapesV16`; excluded from runtime packages | Embedded selected factual values packaged | Qualified against the recorded source hash and deterministic generation checks |
| AISC HSS 0.1.0 | Same DRAT workbook and AISC source basis | Same repository workbook | Embedded selected factual values packaged | Same qualification state |
| AISC C/MC channels 0.1.0 | Same DRAT workbook and AISC source basis | Same repository workbook | Embedded selected factual values packaged | Same qualification state |
| AISC single angles 0.1.0 | Same DRAT workbook and AISC source basis | Same repository workbook | Embedded selected factual values packaged | Same qualification state |
| Thermophysical Properties 0.1.0 | CoolProp samples migrated through SMath plugin build `6.4.8214.13502`, captured 2026-08-14 | Repository JSON under `Data/Sources/Thermophysical`; excluded from runtime packages | Packaged with CoolProp MIT notice | Blocked: exact CoolProp version/input pairs and independent property validation are incomplete |

## AISC verification

The official AISC landing page identifies v16.0 as the Excel shapes database consistent with the 16th Edition Steel Construction Manual. The official download was used to prepare and qualify the repository-owned DRAT compilation; its hash is recorded without committing or redistributing that workbook.

`Data/Sources/AiscShapesV16/DratStructuralSectionsSource.xlsx` contains separate W, HSS, Channel, and Angle sheets plus an explicit property contract. It retains only the records and US-customary geometric properties used by the current DRAT APIs. It omits other shape families, SI duplicates, and unused source fields.

All four generators run in `--check` mode against the committed DRAT workbook. The complete generated W, HSS, C/MC, and L outputs match the committed libraries byte for byte. This full-output comparison confirms the selected columns, missing values, record order, aliases, units, and numeric values used by the generators.

The generators additionally enforce:

- required `README`, `Properties`, and family worksheets;
- dataset ID `DRAT_STRUCTURAL_SECTIONS`, dataset revision 1.0.0, and the recorded AISC source basis;
- exact family-specific property names, IDs, units, and source-column mappings;
- 289 W, 714 HSS, 32 C, 40 MC, and 137 L records;
- unique supported labels and ordered contiguous stable IDs;
- numeric finite property cells, with positive non-missing weight and area;
- explicit `DB_MISSING` output for blank and dash markers;
- verified temporary output followed by atomic replacement;
- read-only stale-output checks and prior-output preservation on validation failure.

The project disposition is to publish DRAT's own curated compilation of factual shape values while neither copying nor redistributing the AISC v16 workbook. Attribution, version identification, the qualification hash, and the narrower field scope remain documented. The official workbook remains excluded from the repository and all packages.

## Engineering Materials verification

The committed workbook validator checks all seven required worksheets, 126 unique material IDs, 18 stable property IDs, 11 source IDs, CPD constant syntax and uniqueness, numeric types, finite values, row source links, formula-derived shear and bulk modulus, numeric-export order, missing-value preservation, and all 2,011 populated values.

The workbook currently assigns one broad source portal to an entire material row. It does not retain a source edition and locator for each populated property or defensible property group. Its 48 `Representative` and 78 `Approximate` records are therefore retained only as screening data. The CalcPad library correctly applies `MAT_CLASS_SCREENING` to every populated value.

Release qualification requires one of these dispositions for every populated value:

1. add a source edition, revision, table/page/product-record locator, units, and applicability basis;
2. replace it with a better-supported value and record the change;
3. leave it explicitly missing; or
4. remove the affected record or dataset when sourcing or redistribution is inadequate.

No value may be promoted from screening merely because it resembles a handbook, portal, or manufacturer value.

## Thermophysical verification

The JSON schema and generator enforce source, fluid, property, and curve IDs; supported CalcPad units; unique public functions; finite numeric values; equal temperature/value axes; strictly increasing temperature; metadata linkage; deterministic output; and failure-safe replacement.

The dataset reproduces the migrated worksheet's CoolProp samples but lacks the exact CoolProp version and complete input-pair calls. It therefore does not claim an independent IAPWS basis or a general equation-of-state capability. CoolProp's MIT notice is included in `THIRD-PARTY-NOTICES.md`.

## Units, conversions, and missing values

- Structural-section values are emitted directly from the DRAT workbook's documented US-customary units; the generator performs no numeric conversion.
- Engineering Materials values use the workbook's documented SI-oriented units. Elongation is a fraction, CTE is in micrometres per metre-kelvin, and shear/bulk modulus are formula-derived only where documented.
- Thermophysical values use the explicit unit keys in the JSON and CalcPad unit expressions in the generator.
- Blank cells and source dash markers remain missing. No generator replaces a missing value with zero.

## Reproduction

Install compatible dependencies:

```powershell
python -m pip install -r requirements-generators.txt
```

Validate repository-owned inputs and generated outputs:

```powershell
python Tools/ValidateEngineeringMaterialsSource.py Data/Sources/EngineeringMaterials/EngineeringMaterialsDatabase.xlsx
python Tools/GenerateThermophysicalLibrary.py Data/Sources/Thermophysical/ThermophysicalProperties.json Libraries/Thermophysical/ThermophysicalProperties.cpd --check
python Tools/GenerateAiscWLibrary.py Data/Sources/AiscShapesV16/DratStructuralSectionsSource.xlsx Libraries/Steel/StructuralSections.cpd --check
python Tools/GenerateAiscHssLibrary.py Data/Sources/AiscShapesV16/DratStructuralSectionsSource.xlsx Libraries/Steel/AiscHssSections.cpd --check
python Tools/GenerateAiscChannelLibrary.py Data/Sources/AiscShapesV16/DratStructuralSectionsSource.xlsx Libraries/Steel/AiscChannelSections.cpd --check
python Tools/GenerateAiscAngleLibrary.py Data/Sources/AiscShapesV16/DratStructuralSectionsSource.xlsx Libraries/Steel/AiscAngleSections.cpd --check
```

`Tools/VerifyRepository.ps1` runs the repository-owned schema and failure-mode tests plus all four structural-section `--check` commands. It does not download or require the external AISC workbook.
