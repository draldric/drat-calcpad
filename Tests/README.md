# Tests

CalcPad regression worksheets are grouped by the behavior they protect.

- `Core/` verifies generated-Core APIs and reporting behavior.
- `Libraries/Analysis/` verifies reusable analysis models and response helpers.
- `Libraries/Materials/` verifies engineering-material data integrity and selection behavior.
- `Libraries/Steel/` verifies structural-section datasets and lookup contracts.
- `Libraries/Thermophysical/` verifies generated fluid-property curves, units, ranges, provenance, and rejected queries.
- `Distribution/` verifies exact archive and declaration-backed manifest contents, metadata and file tamper rejection, physical path-overlap rejection through junction aliases, optional-library preflight, retained version updates, the stable `Current` path, and moved current-version Core-only and optional-library projects.
- `FailureModes/` verifies one-to-one expected CalcPad diagnostics for incompatible APIs, missing dependencies, and incompatible engineering units, including a temporary patched-Core mirror for Plotting-API guards.
- `Tooling/` verifies repository-audit parsers and enforcement rules without requiring CalcPad.

Every `.cpd` test declares a `TEST PURPOSE`.
Automated worksheets define and render `all_tests`; `PlottingBrowserDiagnostic.cpd` is the single explicit browser diagnostic because JavaScript execution and CDN availability cannot be proven by CalcPad equations alone.

| Worksheet | Maintained behavior |
| --- | --- |
| `Core/AuthoringTest.cpd` | Explicit heading, narrative, callout, list, definition, compact-table, equation, citation, caption, outcome, and print-grouping components. |
| `Core/CalculationStatusTest.cpd` | Calculation-status classification, predicates, completion rules, and registry aggregation. |
| `Core/ChecksTest.cpd` | Utilization, classification, units, gating, aggregation, and engineering-check registries. |
| `Core/DatabaseTest.cpd` | Safe columns, table lookups, missing values, fallbacks, and database registries. |
| `Core/DataWrapperTest.cpd` | Property-wrapper aliases, values, statuses, metadata, interpolation, and bounds policies. |
| `Core/FailureModesTest.cpd` | Empty, malformed, duplicate, missing, corrupt, and non-finite Core inputs, including review-status propagation. |
| `Core/PlottingTest.cpd` | Deterministic minimal plotting workflow and CalcPad generation. |
| `Core/PlottingBrowserDiagnostic.cpd` | Browser JavaScript execution and Plotly CDN loading. |
| `Core/ReportingTest.cpd` | Report-registry shapes, links, summaries, and invalid registration attempts. |
| `Core/ReviewSummaryTest.cpd` | Unified review status, readiness, issue counts, and summary rendering. |
| `Core/ValidationTest.cpd` | Scalar, vector, matrix, set, registry, and unit-aware validation. |
| `Libraries/Analysis/BeamAnalysisTest.cpd` | Beam models, load cases, reactions, responses, extrema, diagrams, and screening helpers. |
| `Libraries/Analysis/BeamAnalysisBenchmarkTest.cpd` | Independent equilibrium and Euler-Bernoulli benchmarks for reactions, shear, moment, rotation, deflection, sign conventions, and unit conversion. |
| `Libraries/Analysis/BeamAnalysisFailureModesTest.cpd` | Empty load families, malformed models, invalid geometry, extreme values, accessor gating, and screening failures. |
| `Libraries/Materials/EngineeringMaterialsTest.cpd` | Material data integrity, classification, provenance, discovery, ranking, and thresholds. |
| `Libraries/Materials/EngineeringMaterialsPlottingTest.cpd` | Material comparison and trade-off plotting inputs. |
| `Libraries/Steel/StructuralSectionsTest.cpd` | W-section data, aliases, property lookup, and selection. |
| `Libraries/Steel/AiscHssSectionsTest.cpd` | Rectangular and round HSS data, aliases, statuses, and selection. |
| `Libraries/Steel/AiscChannelSectionsTest.cpd` | C and MC channel data, aliases, statuses, and selection. |
| `Libraries/Steel/AiscAngleSectionsTest.cpd` | Single-angle data, property lookup, and selection. |
| `Libraries/Thermophysical/ThermophysicalPropertiesTest.cpd` | Generated water and 50% ethylene-glycol values, interpolation, units, statuses, provenance, and rendered records. |
| `Tooling/PublicApiAuditTest.ps1` | Multiline-macro assignment parsing and module-namespace classification. |
| `Tooling/ThermophysicalGeneratorTest.py` | Raw-data schema rejection, deterministic generation, and stale-output detection. |
| `FailureModes/FailureModeRuntimeTest.ps1` | Expected compatibility, dependency, and native incompatible-unit diagnostics from a one-to-one negative fixture specification. |

`Distribution/DISTRIBUTION_TEST.ps1` is a PowerShell workflow test rather than a CalcPad worksheet.
It uses only tools copied into the extracted package after the initial build and accepts `-CalcPadCli` to render both relocated portable-project variants.
Native launch failures terminate the test, and repository verification requires the distribution test's final PASS marker.

A test remains relevant only while it protects a maintained public behavior, dataset invariant, compatibility guard, or rendering boundary.
When behavior is removed or consolidated, remove or consolidate its tests in the same change.
