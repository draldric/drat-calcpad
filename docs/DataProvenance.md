# Engineering dataset provenance and release disposition

This audit covers every distributed DRAT engineering dataset as of 2026-08-20. A dataset status of `DB_OK` proves the embedded table's internal shape and IDs; it does not prove technical accuracy, legal redistribution rights, or design applicability.

## Dataset inventory

| Runtime dataset | Source and revision | Raw-input disposition | Generated-output disposition | Qualification state |
|---|---|---|---|---|
| Engineering Materials 1.4.0 | Repository workbook 1.0.0, 2026-08-07; 11 row-level source portals | Committed under `Data/Sources/EngineeringMaterials`; excluded from runtime packages | Packaged as screening data | Blocked: property-level citations and source revisions are incomplete |
| AISC W shapes 0.1.0 | AISC Shapes Database v16.0, August 2023; SHA-256 `82d0ceb96a0d938ae1a6bd9637cb10a1e269225b5d668dce5b0bdc8d86013496` | Externally downloaded; not committed or packaged | Embedded transformed values retained for qualification | Blocked: obtain and record AISC redistribution permission or remove the dataset |
| AISC HSS 0.1.0 | Same AISC workbook | Externally downloaded; not committed or packaged | Embedded transformed values retained for qualification | Same redistribution blocker |
| AISC C/MC channels 0.1.0 | Same AISC workbook | Externally downloaded; not committed or packaged | Embedded transformed values retained for qualification | Same redistribution blocker |
| AISC single angles 0.1.0 | Same AISC workbook | Externally downloaded; not committed or packaged | Embedded transformed values retained for qualification | Same redistribution blocker |
| Thermophysical Properties 0.1.0 | CoolProp samples migrated through SMath plugin build `6.4.8214.13502`, captured 2026-08-14 | Repository JSON under `Data/Sources/Thermophysical`; excluded from runtime packages | Packaged with CoolProp MIT notice | Blocked: exact CoolProp version/input pairs and independent property validation are incomplete |

## AISC verification

The official AISC landing page identifies v16.0 as the Excel shapes database consistent with the 16th Edition Steel Construction Manual. Qualification used the official AISC download and recorded its hash without committing it.

All four generators were run in `--check` mode against that workbook. The complete generated W, HSS, C/MC, and L outputs matched the committed libraries byte for byte. This full-output comparison confirms the selected workbook columns, missing markers, record order, aliases, units, and numeric values used by the generators.

The generators additionally enforce:

- required `Database v16.0` and `Readme` worksheets;
- required label, type, and family-specific property columns;
- 289 W, 714 HSS, 32 C, 40 MC, and 137 L records;
- unique supported labels and deterministic IDs;
- numeric finite property cells, with positive non-missing weight and area;
- explicit `DB_MISSING` output for blank and dash markers;
- verified temporary output followed by atomic replacement;
- read-only stale-output checks and prior-output preservation on validation failure.

AISC's website terms state that site content is proprietary and limit copying and redistribution. Free download is not treated as permission to redistribute the workbook or the transformed embedded table. The raw workbook remains excluded, and public release is blocked pending explicit permission or dataset removal.

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

- AISC values are emitted directly in the source workbook's US-customary units; the generator performs no numeric conversion.
- Engineering Materials values use the workbook's documented SI-oriented units. Elongation is a fraction, CTE is in micrometres per metre-kelvin, and shear/bulk modulus are formula-derived only where documented.
- Thermophysical values use the explicit unit keys in the JSON and CalcPad unit expressions in the generator.
- Blank cells and source dash markers remain missing. No generator replaces a missing value with zero.

## Reproduction

Install compatible dependencies:

```powershell
python -m pip install -r requirements-generators.txt
```

Validate repository-owned inputs:

```powershell
python Tools/ValidateEngineeringMaterialsSource.py Data/Sources/EngineeringMaterials/EngineeringMaterialsDatabase.xlsx
python Tools/GenerateThermophysicalLibrary.py Data/Sources/Thermophysical/ThermophysicalProperties.json Libraries/Thermophysical/ThermophysicalProperties.cpd --check
```

After independently downloading the AISC workbook whose hash is recorded above:

```powershell
python Tools/GenerateAiscWLibrary.py path/to/aisc-shapes-database-v16.0.xlsx Libraries/Steel/StructuralSections.cpd --check
python Tools/GenerateAiscHssLibrary.py path/to/aisc-shapes-database-v16.0.xlsx Libraries/Steel/AiscHssSections.cpd --check
python Tools/GenerateAiscChannelLibrary.py path/to/aisc-shapes-database-v16.0.xlsx Libraries/Steel/AiscChannelSections.cpd --check
python Tools/GenerateAiscAngleLibrary.py path/to/aisc-shapes-database-v16.0.xlsx Libraries/Steel/AiscAngleSections.cpd --check
```

`Tools/VerifyRepository.ps1` runs the repository-owned schema and failure-mode tests. It does not download the external AISC workbook, so the hash-qualified AISC `--check` commands remain an explicit release qualification step.
