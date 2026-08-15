# Release checklist

## Scope and versions

- [ ] Define the release scope and target Core version.
- [ ] Confirm every public change is backward compatible or documented as a breaking change.
- [ ] Update component header versions and matching manifest API values.
- [ ] Update `DRATCoreVersion$` and `DRAT_CORE_API` when required.
- [ ] Update library revisions for data or library-interface changes.
- [ ] Update `CHANGELOG.md`, API documentation, and status-code documentation.

## Build and static verification

- [ ] Confirm every maintained Core helper still has a clear user or internal purpose.
- [ ] Remove obsolete, duplicated, experimental, and unreachable code.
- [ ] Review comments for CalcPad-specific behavior, registry schemas, sentinels, unit handling, and engineering assumptions.
- [ ] Run `pwsh -File Tools/BuildCore.ps1`.
- [ ] Run `pwsh -File Tools/BuildCore.ps1 -Check`.
- [ ] Confirm all includes are direct, relative, repository-local, and exact-case.
- [ ] Confirm generated HTML and PDF files are not staged.
- [ ] Run `git diff --check`.
- [ ] Confirm `Repository verification / Windows static and distribution verification` passes for the release commit.
- [ ] Confirm the hosted workflow summary states that CalcPad CE execution was skipped.

## CalcPad verification

- [ ] Confirm every test protects a maintained behavior and states its test purpose.
- [ ] Confirm every example has one end-user purpose, a defined scope, the standard report structure, and a conclusion.
- [ ] Confirm the general template and every affected specialized template remain usable starting points.
- [ ] Run `pwsh -File Tools/VerifyRepository.ps1` with the CalcPad CE CLI.
- [ ] Confirm all negative failure-mode fixtures report the expected compatibility, dependency, or incompatible-unit diagnostic.
- [ ] Treat CalcPad's native `Inconsistent units` diagnostic as the release boundary for arbitrary dimension mismatches; do not claim that `CHK_ERROR` is returned before evaluation unless the engine provides a safe unit-compatibility predicate.
- [ ] Confirm every Core `all_tests` value is true.
- [ ] Render every changed example in the CalcPad CE GUI.
- [ ] Render `Templates/EngineeringCalculationTemplate.cpd`.
- [ ] Review screen layout, print preview, page breaks, table alignment, and conclusions.
- [ ] Verify Plotly examples with network access when plotting changed.
- [ ] Verify compatibility messages with each required dependency deliberately made incompatible.

## Engineering data review

- [ ] Confirm every changed value has a source and dataset revision.
- [ ] Confirm units and conversion mappings.
- [ ] Confirm missing values remain explicit.
- [ ] Confirm typical, screening, specified-minimum, and design-allowable classifications are not conflated.
- [ ] Confirm valid ranges and extrapolation policies are documented.

## Packaging and publication

- [ ] Merge the verified release branch into `develop`.
- [ ] Open the release pull request from `develop` to `main`.
- [ ] Confirm the release diff contains only intended source, generated Core, documentation, and tests.
- [ ] Create the versioned bundle from the merged `main` commit.
- [ ] Run `pwsh -File Tools/BuildDistribution.ps1 -Archive`.
- [ ] Confirm `manifest.json` contains the expected Core API, library revisions, compatibility bounds, and file hashes.
- [ ] Include `Core/DratCore.cpd`, selected libraries, templates, examples, documentation, and license files.
- [ ] Publish release notes and the compatibility matrix.
- [ ] Tag the merged release commit.
- [ ] Run `Tests/Distribution/DISTRIBUTION_TEST.ps1`.
- [ ] Test the archive installer and portable-project generator in a clean user-controlled directory.
