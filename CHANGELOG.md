# Changelog

All notable changes to DRAT CalcpadCE are documented here.
The project follows semantic versioning for the generated Core API.

## Unreleased

### Added

- Structured project documentation for Core APIs, status codes, architecture, library authoring, versioning, contribution, and releases.
- Engineering Materials discovery APIs for category filtering, property availability, coverage counts, and predefined catalog tables.
- Explicit screening-value classification plus material, property, provenance, and dataset-integrity statuses.
- Library-specific regression verification under `Tests/Libraries/`.

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
