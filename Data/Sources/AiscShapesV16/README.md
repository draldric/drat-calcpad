# AISC Shapes Database v16.0 source record

## Identification

- Publisher: American Institute of Steel Construction (AISC)
- Dataset: AISC Shapes Database v16.0
- Edition basis: AISC Steel Construction Manual, 16th Edition
- Published revision: Version 16.0, August 2023
- Official landing page: https://www.aisc.org/aisc/publications/steel-construction-manual/aisc-shapes-database-v160/
- Official download used for qualification: `https://cloud.aisc.org/biggie_bin/aisc-shapes-database-v160-2.xlsx`
- Retrieved: 2026-08-20
- SHA-256: `82d0ceb96a0d938ae1a6bd9637cb10a1e269225b5d668dce5b0bdc8d86013496`
- Required worksheets: `Database v16.0` and `Readme`

## Repository and redistribution disposition

The official workbook is externally obtained and is not committed. AISC makes the workbook available for download, but its website terms restrict copying and redistribution. DRAT therefore records the authoritative download and hash while excluding the workbook from the repository and runtime packages.

The committed `.cpd` files contain selected nominal geometric properties transformed from the workbook. Their public redistribution requires an explicit AISC permission decision before the first release. Until that decision is recorded, the four generated AISC libraries are a release blocker; free public download is not treated as redistribution permission.

## Generated coverage

- `StructuralSections.cpd`: 289 W shapes and 16 US-customary property columns.
- `AiscHssSections.cpd`: 714 HSS shapes and 16 US-customary property columns.
- `AiscChannelSections.cpd`: 32 C and 40 MC shapes and 18 US-customary property columns.
- `AiscAngleSections.cpd`: 137 single-angle L shapes and 20 US-customary property columns.

Double angles and every other AISC family are excluded. The libraries contain geometric properties only; they do not contain material strengths, member capacities, connection capacities, or design-code checks.

Missing cells and AISC dash markers remain `DB_MISSING`. No absent property is replaced by zero or inferred. Values are emitted in the workbook's US-customary units without conversion.

## Generation

Install the compatible generator dependencies from `requirements-generators.txt`. Pass the independently downloaded workbook to each `Tools/GenerateAisc*Library.py` command. The generators validate the workbook schema and expected family counts before producing output.
