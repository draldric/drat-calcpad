# DRAT structural-section source dataset

## Identification

- Publisher: American Institute of Steel Construction (AISC)
- Dataset: AISC Shapes Database v16.0
- Edition basis: AISC Steel Construction Manual, 16th Edition
- Published revision: Version 16.0, August 2023
- Official landing page: https://www.aisc.org/aisc/publications/steel-construction-manual/aisc-shapes-database-v160/
- Official download used for qualification: `https://cloud.aisc.org/biggie_bin/aisc-shapes-database-v160-2.xlsx`
- Retrieved: 2026-08-20
- SHA-256: `82d0ceb96a0d938ae1a6bd9637cb10a1e269225b5d668dce5b0bdc8d86013496`
- Repository source workbook: `DratStructuralSectionsSource.xlsx`
- DRAT dataset revision: 1.0.0, 2026-08-20
- Required worksheets: `README`, `Properties`, `W`, `HSS`, `Channel`, `Angle`, and `QA`

## Repository and redistribution disposition

The official AISC workbook is not committed or redistributed. DRAT instead maintains its own curated workbook containing selected factual geometric values, organized by supported shape family. It omits the official workbook's unused families, SI duplication, and additional parameters.

`DratStructuralSectionsSource.xlsx` is the repository-owned source of truth for generation. The source workbook is committed for review and regeneration but excluded from runtime packages. The generated `.cpd` files contain the same selected factual values in CalcPad form. This disposition does not authorize copying or redistributing the AISC v16 workbook itself.

## Generated coverage

- `StructuralSections.cpd`: 289 W shapes and 16 US-customary property columns.
- `AiscHssSections.cpd`: 714 HSS shapes and 16 US-customary property columns.
- `AiscChannelSections.cpd`: 32 C and 40 MC shapes and 18 US-customary property columns.
- `AiscAngleSections.cpd`: 137 single-angle L shapes and 20 US-customary property columns.

Double angles and every other AISC family are excluded. The libraries contain geometric properties only; they do not contain material strengths, member capacities, connection capacities, or design-code checks.

Missing cells and AISC dash markers remain `DB_MISSING`. No absent property is replaced by zero or inferred. Values are emitted in the workbook's US-customary units without conversion.

## Generation

Install the compatible generator dependencies from `requirements-generators.txt`. Pass `DratStructuralSectionsSource.xlsx` to each `Tools/GenerateAisc*Library.py` command. The generators validate the DRAT dataset identity and revision, exact family sheets, stable IDs, property contract, numeric values, missing values, and expected family counts before producing output.
