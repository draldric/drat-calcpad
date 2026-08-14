# Contributing to DRAT CalcpadCE

## Branches and pull requests

- `main` contains stable releases.
- `develop` contains integrated work in progress.
- Create feature and fix branches from `develop`.
- Open pull requests back into `develop`.
- Keep pull requests as drafts until the affected worksheets have been tested in CalcPad CE.

Keep commits focused and use brief, imperative subjects.
Do not commit generated HTML, PDFs, editor settings, backups, or temporary files.

## Repository responsibilities

- Put reusable calculation behavior in `Core/Src/`.
- Regenerate `Core/DratCore.cpd` after changing a Core source module.
- Put optional engineering datasets and their lookup interfaces in `Libraries/`.
- Use `Templates/` for supported starting points.
- Use `Examples/` for complete workflows.
- Add deterministic regressions to `Tests/Core/` for every changed public Core helper.

Read the [architecture](docs/Architecture.md), [Core API](docs/CoreApi.md), and [library-authoring guide](docs/LibraryAuthoring.md) before changing a public contract.

## CalcPad conventions

- Separate function arguments and `$block` expressions with semicolons.
- Use relative includes with exact directory and filename casing.
- Keep the include graph direct; libraries do not include their dependencies.
- Use PascalCase filenames and PascalCase-prefixed public helpers.
- Use descriptive snake_case for local calculation values.
- Preserve four-space indentation inside macro bodies and nested JavaScript.
- Treat apostrophe-prefixed lines as formatted output, not inert comments.
- Avoid listing undefined macro names in rendered comments.
- Do not use `#else if`; use nested conditionals or separate `#if` blocks.
- Verify multiline matrices, macros, and functions against working CalcPad examples.

Preserve working plotting and data-wrapper patterns unless the change explicitly targets them.

## Public APIs and versions

Before changing a public function, macro, constant, status, data ID, or unit mapping:

1. Decide whether the change is patch, minor, or major.
2. Update the component and manifest versions described in the [versioning policy](docs/Versioning.md).
3. Update the generated Core bundle.
4. Update API and status documentation.
5. Add regression coverage.
6. Record the change in `CHANGELOG.md`.

## Verification

Every pull request targeting `develop` or `main` runs the Windows `Repository verification` workflow.
Its hosted job performs changed-file whitespace checks and runs:

```powershell
pwsh -NoProfile -File Tools/VerifyRepository.ps1 -SkipCalcPad
```

The hosted workflow does not install or execute CalcPad CE.
See the [automation guide](docs/Automation.md) for its exact coverage and the stable check name used by branch protection.

Run the complete verifier before opening or updating a pull request:

```powershell
pwsh -File Tools/VerifyRepository.ps1
```

The verifier checks the generated Core, version declarations, includes, whitespace, Core tests, examples, and engineering template.

If the CalcPad CLI is unavailable, static checks can be run with:

```powershell
pwsh -File Tools/VerifyRepository.ps1 -SkipCalcPad
```

State clearly in the pull request when local CalcPad execution was skipped, even when the hosted workflow passes.
Static checks do not replace manual GUI review.

## Pull-request description

Explain:

- The engineering use case.
- Public APIs or datasets changed.
- Worksheets and documentation changed.
- Automated and manual tests performed.
- Remaining CalcPad CE GUI checks.
- Compatibility or migration impact.

Include rendered screenshots when plotting, stylesheet, table, or print behavior changes.
