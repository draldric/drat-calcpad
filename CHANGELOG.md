# Changelog

All notable changes to DRAT CalcpadCE are documented here.
The project follows semantic versioning for the generated Core API.

## Unreleased

### Added

- Structured engineering check-result registry with stable IDs, upper-limit, lower-limit, and custom constructors, automatic aggregation, governing selection, issue summaries, and document-status integration.
- Dedicated check-registry demo and expanded Core regression coverage.
- Structured registries for references, design criteria, assumptions, and limitations with unique IDs, validated source links, inline errors, standardized tables, and an aggregate reporting summary.
- Dedicated reporting-registry demo, focused regression coverage, and a registry-based engineering calculation template.
- Versioned distribution-directory and ZIP creation with a machine-readable compatibility and SHA-256 manifest.
- Managed per-user installation and update tooling with retained versions and a stable `Current` path.
- Portable-project generation with direct relative Core and optional Materials includes.
- Automated clean-directory distribution, installation, update, and project-generation regression checks.
- Document-level calculation status aggregation with distinct pass, warning, fail, incomplete-input, and calculation-error outcomes.
- Standard calculation-status banner with validation and engineering-check counts.
- Structured project documentation for Core APIs, status codes, architecture, library authoring, versioning, contribution, and releases.
- Engineering Materials discovery APIs for category filtering, property availability, coverage counts, and predefined catalog tables.
- Explicit screening-value classification plus material, property, provenance, and dataset-integrity statuses.
- Library-specific regression verification under `Tests/Libraries/`.
- Multi-property candidate selection across one category or the complete material catalog.
- Ascending and descending property ranking with structured status, material ID, and raw-value results.
- Unit-aware minimum, maximum, and bounded material filters.
- Predefined ranked-candidate and side-by-side material-comparison tables.
- Single-property bar charts and two-property trade-off plots for explicit material shortlists.
- AISC v16 W-shape structural-sections library with 289 embedded geometric-property records, unit-aware lookup, aliases, screening, provenance tables, demo, and regression coverage.
- AISC v16 HSS library with 714 square, rectangular, and round section records, including HSS-specific dimensions, lookup, reporting, and regression coverage.
- AISC v16 C and MC channel library with 72 asymmetric-section records, including centroid and shear-center properties, lookup, reporting, and regression coverage.
- AISC v16 single-angle library with 137 L-section records, principal-axis properties, lookup, screening, reporting, and regression coverage; double angles are excluded.

### Changed

- Core is versioned as 3.0.0 because manual check-summary macros and caller-maintained parallel result vectors were replaced by the structured check-registry workflow before the first public release.
- Core is versioned as 2.0.0 because the former free-form reference and initial-condition macros were replaced by the structured registry workflow before the first public release.

## 1.6.0 - 2026-08-09

### Added

- Structured five-field validation results with automatic value, permitted-rule, and status reporting.
- Global permitted-value registry for reusable engineering input sets.
- Scalar sign, range, bound, zero-tolerance, availability, and registration rules.
- Vector range, sign, finiteness, ordering, uniqueness, and matching-length rules.
- Matrix row, column, square, and exact-dimension rules.
- Complete material allowable engineering example with source, revision, validation, checks, governing result, and conclusions.

### Changed

- Material-record, material-property, validation, variable, revision, and engineering-check tables use consistent engineering-report alignment.
- Validation reporting can derive all displayed fields from the evaluated result record.

## 1.4.0 - 2026-08-09

### Added

- Trusted calculation flow with aggregate check counts, governing utilization, governing row, and overall status.
- Validation-gated engineering checks.
- Repository verification script covering generated Core freshness, APIs, includes, whitespace, CalcPad tests, examples, and template rendering.
- Expanded engineering calculation template and document-control metadata.

## 1.0.0 - 2026-08-08

### Added

- Generated Core bundle and modular `Core/Src/` layout.
- Reusable worksheet definitions, styling, checks, validation, database helpers, data wrappers, and Plotly helpers.
- Engineering Materials library and property-library template.
- Initial Core regression worksheets and examples.
