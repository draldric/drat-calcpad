# Tests

CalcPad regression worksheets are grouped by the behavior they protect.

- `Core/` verifies generated-Core APIs and reporting behavior.
- `Libraries/Analysis/` verifies reusable analysis models and response helpers.
- `Libraries/Materials/` verifies engineering-material data integrity and selection behavior.
- `Libraries/Steel/` verifies structural-section datasets and lookup contracts.
- `Distribution/` verifies packaging, installation, updates, and portable projects.

Every `.cpd` test declares a `TEST PURPOSE`.
Automated worksheets define and render `all_tests`; `PlottingBrowserDiagnostic.cpd` is the single explicit browser diagnostic because JavaScript execution and CDN availability cannot be proven by CalcPad equations alone.

| Worksheet | Maintained behavior |
| --- | --- |
| `Core/CalculationStatusTest.cpd` | Calculation-status classification, predicates, completion rules, and registry aggregation. |
| `Core/ChecksTest.cpd` | Utilization, classification, units, gating, aggregation, and engineering-check registries. |
| `Core/DatabaseTest.cpd` | Safe columns, table lookups, missing values, fallbacks, and database registries. |
| `Core/DataWrapperTest.cpd` | Property-wrapper aliases, values, statuses, metadata, interpolation, and bounds policies. |
| `Core/PlottingTest.cpd` | Deterministic minimal plotting workflow and CalcPad generation. |
| `Core/PlottingBrowserDiagnostic.cpd` | Browser JavaScript execution and Plotly CDN loading. |
| `Core/ReportingTest.cpd` | Report-registry shapes, links, summaries, and invalid registration attempts. |
| `Core/ReviewSummaryTest.cpd` | Unified review status, readiness, issue counts, and summary rendering. |
| `Core/ValidationTest.cpd` | Scalar, vector, matrix, set, registry, and unit-aware validation. |
| `Libraries/Analysis/BeamAnalysisTest.cpd` | Beam models, load cases, reactions, responses, extrema, diagrams, and screening helpers. |
| `Libraries/Materials/EngineeringMaterialsTest.cpd` | Material data integrity, classification, provenance, discovery, ranking, and thresholds. |
| `Libraries/Materials/EngineeringMaterialsPlottingTest.cpd` | Material comparison and trade-off plotting inputs. |
| `Libraries/Steel/StructuralSectionsTest.cpd` | W-section data, aliases, property lookup, and selection. |
| `Libraries/Steel/AiscHssSectionsTest.cpd` | Rectangular and round HSS data, aliases, statuses, and selection. |
| `Libraries/Steel/AiscChannelSectionsTest.cpd` | C and MC channel data, aliases, statuses, and selection. |
| `Libraries/Steel/AiscAngleSectionsTest.cpd` | Single-angle data, property lookup, and selection. |

A test remains relevant only while it protects a maintained public behavior, dataset invariant, compatibility guard, or rendering boundary.
When behavior is removed or consolidated, remove or consolidate its tests in the same change.
