# Repository Guidelines

## Project Structure & Module Organization

This repository is a reusable CalcPad CE engineering-calculation framework. `Core/` contains shared definitions, styling, plotting helpers, validation, checks, and database wrappers. Add reusable functionality there rather than copying it into worksheets. `Templates/` provides starting points for domain-specific property libraries. `Examples/` demonstrates supported integrations, while `Tests/Core/` contains focused calculation and browser-rendering checks. All maintained source files use the `.cpd` extension; generated `.html` and `.pdf` files are intentionally ignored.

## Build, Test, and Development Commands

The project has no package manager or automated command-line build. Open worksheets in CalcPad CE to calculate and render them.

- `rg --files -g "*.cpd"` lists all CalcPad sources.
- `rg "#include" Core Examples Templates Tests` audits include paths after moving files.
- Open `Examples/PLOTTING_DEMO.cpd` to exercise the plotting API end to end.
- Open `Tests/Core/DATA_WRAPPER_TEST.cpd` and confirm `all_tests` evaluates true.
- Open the two `PLOTTING_*_TEST.cpd` worksheets and verify the chart and JavaScript diagnostic render without errors.

Plotting loads Plotly from a CDN, so those checks require network access.

## Coding Style & Naming Conventions

Match the surrounding CalcPad syntax and keep includes relative, with directory and filename casing that exactly matches the repository (for example, `#include ../Core/Plotting.cpd`). Use semicolons between function arguments and within `$block` expressions. Preserve four-space indentation inside macro bodies and nested JavaScript; use descriptive snake_case for local values, PascalCase-prefixed public helpers (such as `DBRangeStatus`), and uppercase constants. Core module filenames use PascalCase; use PascalCase for demos, templates, and tests where practical. Keep comments short and explain engineering intent or non-obvious bounds behavior.

## Testing Guidelines

Add deterministic checks to `Tests/Core/` and name new files `<FEATURE>_TEST.cpd`. Cover nominal values, aliases, missing data, range policies, and status codes where applicable. Use tolerances for interpolated numeric results instead of exact equality. There is no configured coverage threshold; every changed public helper should have a worksheet-level regression check.

## Commit & Pull Request Guidelines

History uses brief, imperative, title-case subjects such as `Updated File Paths`; keep commits focused and name the affected behavior. Pull requests should explain the engineering use case, list changed worksheets, and record manual test results. Link related issues and include rendered screenshots for plotting or stylesheet changes. Do not commit generated HTML, PDFs, editor settings, backups, or temporary files.

# DRAT CalcpadCE Development Instructions

## Project

DRAT stands for **Design, Reporting, Analysis, and Tools**.

DRAT is a modular engineering calculation and reporting framework for CalcpadCE.

Repository:

`draldric/drat-calcpad`

## Branching

- `main` contains stable releases.
- `develop` contains integrated work in progress.
- Create feature and fix branches from `develop`.
- Open pull requests back into `develop`.
- Use draft pull requests until changes have been tested in CalcpadCE.

## Current Task

Work on branch:

`agent/core-cleanup`

Complete the following without changing calculation behaviour:

1. Fix the remaining CSS syntax errors in the stylesheet.
2. Standardize core filenames.
3. Update every affected `#include` path.
4. Preserve the working plotting and database logic.
5. Review the final diff.
6. Commit and push the changes.
7. Open a draft pull request into `develop`.

## Filename Convention

Use PascalCase for core modules:

- `Core/Definitions.cpd`
- `Core/Stylesheet.cpd`
- `Core/Plotting.cpd`
- `Core/DataWrapper.cpd`
- `Core/Checks.cpd`
- `Core/Database.cpd`
- `Core/Validation.cpd`

Use PascalCase for examples, templates, and tests where practical.

CalcpadCE and Linux paths may be case-sensitive. Every include path must match the exact file and directory casing.

## CalcpadCE Constraints

CalcpadCE has syntax and rendering behaviour that differs from general-purpose programming languages.

Important known constraints:

- Apostrophe-prefixed lines are formatted output, not inert comments.
- Macro names ending in `$` may expand inside apostrophe text.
- Avoid listing undefined macro names in rendered comments.
- CalcpadCE does not support `#else if`; use nested conditionals or separate `#if` blocks.
- Verify multiline function and matrix syntax against working CalcpadCE examples.
- Do not assume JavaScript, HTML, CSS, or Calcpad syntax is valid without checking the generated output.
- Plotting uses inline Plotly JavaScript based on the official CalcpadCE example pattern.
- Preserve working code unless the task specifically requires a behavioural change.

## Stylesheet Cleanup

Correct known CSS errors, including:

- `text-transform:upercase` → `text-transform:uppercase`
- `counter - reset` → `counter-reset`
- `counter - increment` → `counter-increment`
- Ensure all `<style>` tags close with valid `</style>` tags.
- Consolidate repeated rules where this does not alter output.
- Use valid CSS property spacing and syntax.

## Include Paths

Examples are one directory below the repository root:

```text
#include ../Core/Stylesheet.cpd
#include ../Core/Definitions.cpd
#include ../Core/Plotting.cpd
```

Tests under `Tests/Core` are two directories below the root:

```text
#include ../../Core/Plotting.cpd
#include ../../Core/DataWrapper.cpd
#include ../../Templates/PropertyLibraryTemplate.cpd
```

Templates should reference core files from one directory below the root:

```text
#include ../Core/DataWrapper.cpd
```

Inspect every `.cpd` file rather than relying only on these examples.

## Validation

CalcpadCE is installed on the user's Windows machine. Run any available parser or worksheet tests where possible.

At minimum:

- Search for stale filenames and path casing.
- Search for invalid CSS forms.
- Confirm that all referenced `.cpd` files exist.
- Review the Git diff.
- Do not claim CalcpadCE runtime validation unless it was actually run.

The user will manually verify rendered worksheets in CalcpadCE when required.

## Pull Request

The draft pull request should target `develop`.

Suggested title:

`Clean up core naming, include paths, and stylesheet`

The description should include:

- Files renamed
- Include paths updated
- CSS errors corrected
- Confirmation that calculation logic was not intentionally changed
- Tests or static checks performed
- Any remaining CalcpadCE runtime checks required
