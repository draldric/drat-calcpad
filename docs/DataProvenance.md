# Engineering dataset provenance and release disposition

This audit covers every distributed DRAT engineering dataset as of 2026-08-23. A dataset status of `DB_OK` proves the embedded table's internal shape and IDs; it does not prove technical accuracy, legal redistribution rights, or design applicability.

## Dataset inventory

| Runtime dataset | Source and revision | Raw-input disposition | Generated-output disposition | Qualification state |
|---|---|---|---|---|
| Engineering Materials 1.7.0 | Repository workbook 1.3.0, 2026-08-23; 15 citation records and 1,993 property mappings | Committed under `Data/Sources/EngineeringMaterials`; excluded from runtime packages | Packaged as screening data | Blocked: 30 mappings are property-record qualified across Forta DX 2205 and Core 304/304L; 1,963 mappings remain source-only |
| AISC W shapes 0.1.0 | DRAT structural-section source 1.0.0; values based on AISC Shapes Database v16.0, August 2023 | Repository workbook committed under `Data/Sources/AiscShapesV16`; excluded from runtime packages | Embedded selected factual values packaged | Qualified against the recorded source hash and deterministic generation checks |
| AISC HSS 0.1.0 | Same DRAT workbook and AISC source basis | Same repository workbook | Embedded selected factual values packaged | Same qualification state |
| AISC C/MC channels 0.1.0 | Same DRAT workbook and AISC source basis | Same repository workbook | Embedded selected factual values packaged | Same qualification state |
| AISC single angles 0.1.0 | Same DRAT workbook and AISC source basis | Same repository workbook | Embedded selected factual values packaged | Same qualification state |
| Thermophysical Properties 0.6.0 | CoolProp samples, IAPWS R7-97(2012), twelve pure-fluid reference equations, and Melinder MEG/MPG correlations curated from pinned CoolProp revision `5b9c32a` | Repository JSON under `Data/Sources/Thermophysical`; excluded from runtime packages | Generated equations and unified `ThermoProps` plus concentration-aware `GlycolPROP` interfaces packaged with CoolProp and IAPWS attribution | IF97 equations qualified against official tables; pure-fluid and aqueous-glycol equations regression-checked against CoolProp 8.0.0; older sampled water curves retain their earlier qualification limitation |

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

The committed workbook validator reads the declared dataset contract and validates all required worksheets, unique stable IDs, source/citation/category/alias registries, CPD constant syntax, numeric types, finite values, row source links, exact property-provenance coverage, citation qualification, formula-derived shear and bulk modulus, numeric-export order, and missing-value preservation. Record, source, citation, provenance, and populated-value totals are derived rather than encoded in validation code.

Ordinary validation and generation accept explicitly incomplete level 1 records so maintenance remains atomic and auditable. `ValidateEngineeringMaterialsSource.py --release` separately enforces the workbook's minimum release level and currently fails because only 30 of 1,993 values have level 3 property-record citations. This failure remains expected until real editions and locators are entered for the other records.

The workbook maps every populated property to a citation record, but most migrated citation records still represent broad source portals and do not retain editions or property-record locators. Forta DX 2205 records Outokumpu CMS revision `a7abe2a9-7ebb-45aa-88bf-ce0e9d4aca12`; Core 304/4301 and Core 304L/4307 record revision `025e9931-a1d5-4c8f-8ff5-f881d38916da`. Both batches retain table locators, property-specific evidence, conversions, product-form applicability, and any lower-bound choice. Their values remain screening data, and the CalcPad library reports the release-provenance gap separately.

Release qualification requires one of these dispositions for every populated value:

1. add a source edition, revision, table/page/product-record locator, units, and applicability basis;
2. replace it with a better-supported value and record the change;
3. leave it explicitly missing; or
4. remove the affected record or dataset when sourcing or redistribution is inadequate.

No value may be promoted from screening merely because it resembles a handbook, portal, or manufacturer value.

## Thermophysical verification

The JSON schemas and generator enforce source, fluid, property, and curve IDs; supported CalcPad units; unique public functions; finite numeric values; equal temperature/value axes; strictly increasing temperature; fixed IF97 coefficient counts; supported Helmholtz term families; aligned equation coefficient arrays; metadata linkage; deterministic output; and failure-safe replacement.

The remaining water curve records reproduce the migrated worksheet's CoolProp samples but lack the exact CoolProp version and complete input-pair calls. They remain a migration baseline rather than an independently qualified equation-of-state basis. The legacy 50% ethylene-glycol API now dispatches to equations rather than those sampled points.

The IF97 records separately reproduce the official Region 1 and Region 2 fundamental equations, the Region 4 saturation-pressure and saturation-temperature equations, and the B23 boundary equation. CalcPad regression checks cover all published verification points applicable to those equations. Region 3, Region 5, metastable steam, and two-phase quality states are explicitly rejected rather than evaluated with an adjacent region.

The twelve pure-fluid records are curated from full upstream CoolProp fluid records at one pinned Git revision. The importer selects the configured default EOS, restricts accepted citation keys and implemented ideal/residual term families, and records each upstream file hash. The runtime library evaluates the fundamental Helmholtz equations and analytic derivatives; it does not interpolate sampled thermodynamic property values for these fluids. CalcPad regressions compare representative properties for every equation record with pinned CoolProp 8.0.0 values, with broader gas, liquid, and supercritical coverage for nitrogen and carbon dioxide. The pure propylene-glycol EOS supplies thermodynamic properties but not transport properties. R744 is an alias of the carbon-dioxide record. R401A remains excluded because its zeotropic blend behavior requires mixture reducing and departure functions plus bubble/dew handling.

The aqueous MEG and MPG records preserve the Melinder polynomial and exponential-polynomial coefficients, concentration and temperature bases, freezing correlations, mass-fraction basis, pinned revision, and upstream hashes. Runtime density, specific heat, viscosity, and conductivity are evaluated from those equations for 0 to 60% glycol by mass and rejected below the correlated freezing point. Pure ethylene glycol is not represented because the pinned source has no pure-fluid EOS and the aqueous equations do not authorize extrapolation to 100%.

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
python Tools/GenerateEngineeringMaterialsLibrary.py Data/Sources/EngineeringMaterials/EngineeringMaterialsDatabase.xlsx Libraries/Materials/EngineeringMaterials.cpd --check
python Tools/GenerateThermophysicalLibrary.py Data/Sources/Thermophysical/ThermophysicalProperties.json Libraries/Thermophysical/ThermophysicalProperties.cpd --helmholtz-source Data/Sources/Thermophysical/HelmholtzFluids.json --glycol-source Data/Sources/Thermophysical/IncompressibleGlycols.json --check
python Tools/GenerateAiscWLibrary.py Data/Sources/AiscShapesV16/DratStructuralSectionsSource.xlsx Libraries/Steel/StructuralSections.cpd --check
python Tools/GenerateAiscHssLibrary.py Data/Sources/AiscShapesV16/DratStructuralSectionsSource.xlsx Libraries/Steel/AiscHssSections.cpd --check
python Tools/GenerateAiscChannelLibrary.py Data/Sources/AiscShapesV16/DratStructuralSectionsSource.xlsx Libraries/Steel/AiscChannelSections.cpd --check
python Tools/GenerateAiscAngleLibrary.py Data/Sources/AiscShapesV16/DratStructuralSectionsSource.xlsx Libraries/Steel/AiscAngleSections.cpd --check
```

`Tools/VerifyRepository.ps1` runs the repository-owned schema and failure-mode tests plus Engineering Materials and all four structural-section `--check` commands. It does not download or require the external AISC workbook.
