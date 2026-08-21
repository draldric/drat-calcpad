# Changelog

All notable changes to DRAT CalcpadCE are documented here.
The project follows semantic versioning for the generated Core API.

## Unreleased

### Added

- Dataset provenance records under `Data/Sources/`, compatible generator dependencies, a consolidated source/redistribution audit, and the CoolProp MIT notice.
- Engineering Materials workbook validation for worksheets, IDs, numeric types, derived moduli, source links, missing values, and the complete CPD numeric export.
- Shared AISC generator schema validation, deterministic read-only checks, verified temporary output, atomic replacement, and failed-write preservation coverage.
- Explicit worksheet-authoring API with H3-H6 helpers, semantic callouts, heading-free lists and definitions, compact records and comparisons, CalcPad-native equation blocks, citations, captions, result highlights, print grouping, regression coverage, and a focused pipe-insulation demo.
- Generated Thermophysical Properties 0.1.0 library with traceable water and 50% ethylene-glycol temperature curves, unit-aware typed helpers, status-aware generic lookup, provenance reporting, schema validation, regression coverage, and a focused end-user demo.
- Deterministic boundary and failure-mode coverage for empty and malformed registries, missing versus zero data, invalid beam records, modifiers, and extrema, incompatible Core/component/Plotting APIs, missing dependencies, rendered error evidence, and native CalcPad unit errors.
- Independent equilibrium and Euler-Bernoulli beam benchmarks covering point loads, uniform and triangular distributed loads, applied moments, support conditions, sign conventions, and alternate units.
- Windows GitHub Actions verification for generated Core, APIs, includes, artifact conventions, public-helper integrity, and distribution workflows, with an explicit CalcPad CE qualification boundary.
- Deterministic public-Core API audit that rejects undocumented, duplicated, or unexplained definition-only helpers, inventories implementation-only helpers, and enforces module-prefixed macro locals with explicit global-registry exceptions.
- Unified document-review status combining calculation results and reporting integrity, with separate readiness-for-check and readiness-for-issue decisions.
- Consolidated linked review summary for validation, engineering-check, and reporting issues, with a dedicated demo and regression worksheet.
- Structured engineering check-result registry with stable IDs, upper-limit, lower-limit, and custom constructors, automatic aggregation, governing selection, issue summaries, and document-status integration.
- Dedicated check-registry demo and expanded Core regression coverage.
- Structured input-validation registry with stable IDs, automatic aggregation, linked issue summaries, integrity checks, and document-status integration.
- Dedicated validation-registry demo and expanded validation and calculation-status regression coverage.
- Structured registries for references, design criteria, assumptions, and limitations with unique IDs, validated source links, inline errors, standardized tables, and an aggregate reporting summary.
- Dedicated reporting-registry demo, focused regression coverage, and a registry-based engineering calculation template.
- Versioned distribution-directory and ZIP creation with a machine-readable compatibility and SHA-256 manifest.
- Managed per-user installation and update tooling with retained versions and a stable `Current` path.
- Portable-project generation with direct relative Core and optional Materials includes.
- Automated clean-directory distribution qualification with declaration-backed archive metadata, required and optional library compatibility records, table-driven metadata tamper checks, junction-aware path-overlap rejection, optional-library entrypoint preflight, explicit native-launch failure propagation, internally consistent retained-version updates, stable `Current` verification, and relocated current-version Core-only and Materials-enabled project checks.
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

- Core generation now verifies a unique same-directory temporary bundle and atomically replaces `DratCore.cpd`, preserving the previous output and cleaning temporary files when generation fails.
- Core is versioned as 4.3.0 with Authoring API 1.0.0 and shared stylesheet 1.10.0.
- Definitions 2.2.0 makes conclusion blocks render result values with units without exposing variable expressions and restores worksheet rendering modes when the block ends.
- Authoring definitions use an open term-description layout, prose-valued table cells align with numeric values, and validation-summary counts use a compact structured footer.
- Core 4.2.0 established worksheet-owned report headings, compact IEEE-style reference rows, stacked design-basis records, and record-level print grouping; cover-page helpers remained the only implicit heading producers.
- Core is versioned as 4.1.2 with shape-safe reporting registries and release-hardening standards for tests, examples, templates, and maintainability comments.
- Beam Analysis 0.6.1 rejects empty load families and prevents invalid model records from producing plausible high-level reactions, responses, or series.
- DataWrapper 0.3.3 identifies itself as the DRAT Data Wrapper instead of retaining stale template metadata.
- Examples use one focused purpose, explicit scope, standard document control, revision history, and conclusions.
- Tests use PascalCase names and state the maintained behavior or browser diagnostic they protect.
- Specialized templates are categorized under `Templates/`, leaving one general calculation template at the top level.
- Removed unused duplicate integrity predicates and the obsolete manual validation-row macro before the first public release.
- Core is versioned as 4.1.0 with the unified review-summary API and exact links to failed reporting-registration attempts.
- Reporting registration attempts now store entry type, ID, status, and sequence so document-review errors can link to their exact source rows.
- Core was versioned as 4.0.0 because validation reporting registers results by stable input ID and no longer requires caller-maintained result matrices.
- Validation summary macros now switch to value-only rendering internally and restore equation and variable-substitution rendering when the table closes.
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
