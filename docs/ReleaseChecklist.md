# Release checklist

## Scope and versions

- [ ] Define the release scope and target Core version.
- [ ] Confirm every public change is backward compatible or documented as a breaking change.
- [ ] Update component header versions and matching manifest API values.
- [ ] Update `DRATCoreVersion$` and `DRAT_CORE_API` when required.
- [ ] Update library revisions for data or library-interface changes.
- [ ] Update `CHANGELOG.md`, API documentation, and status-code documentation.

## Build and static verification

- [ ] Run `pwsh -File Tools/BuildCore.ps1`.
- [ ] Run `pwsh -File Tools/BuildCore.ps1 -Check`.
- [ ] Confirm all includes are direct, relative, repository-local, and exact-case.
- [ ] Confirm generated HTML and PDF files are not staged.
- [ ] Run `git diff --check`.

## CalcPad verification

- [ ] Run `pwsh -File Tools/VerifyRepository.ps1` with the CalcPad CE CLI.
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
- [ ] Include `Core/DratCore.cpd`, selected libraries, templates, examples, documentation, and license files.
- [ ] Publish release notes and the compatibility matrix.
- [ ] Tag the merged release commit.
- [ ] Test installation or extraction in a clean directory.
