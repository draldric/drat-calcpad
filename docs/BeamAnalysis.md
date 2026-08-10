# Static beam analysis library

`Libraries/Analysis/BeamAnalysis.cpd` provides a small, auditable response layer for common prismatic-beam cases.

## Scope

The current release supports:

- simply supported beams;
- cantilever beams;
- any finite set of point loads at user-specified positions; and
- any finite set of piecewise-constant distributed-load segments.

The equations are closed-form Euler-Bernoulli elastic beam equations for static, small-deflection response.
The modular functions use linear superposition of the supported load families, so each load vector must contain one physical quantity only.
The caller supplies span, load, elastic modulus, and second moment of area with units.

The library does not provide code capacities, factored load combinations, lateral-torsional buckling, shear-deformation, plastic, dynamic, or stability analysis.
Those decisions remain worksheet- and code-specific.

## Loading

Use the same scalar argument order for every response function:

```text
support; load_type; span; point_load; point_position; distributed_load; modulus; inertia
```

The arguments are ordered as follows:

| Position | Meaning |
| --- | --- |
| 1 | `BEAM_SIMPLE_SUPPORTED` or `BEAM_CANTILEVER` |
| 2 | `BEAM_POINT_LOAD` or `BEAM_FULL_UDL` |
| 3 | Span |
| 4 | Point-load magnitude; use zero for a UDL case |
| 5 | Point-load position from the left/fixed end; use zero for a UDL case |
| 6 | Full-span UDL magnitude; use zero for a point-load case |
| 7 | Elastic modulus |
| 8 | Second moment of area |

Validate a case before using it with `BeamCaseStatus(support; load_type; span; point_load; point_position; distributed_load; modulus; inertia)`.
The response functions return a non-finite value for a fatal case or out-of-span query.

## Modular load-set API

The modular functions use this argument order:

```text
support; span; point_loads; point_positions; udl_starts; udl_ends; udl_values; modulus; inertia
```

`point_loads` and `point_positions` must have the same length.
`udl_starts`, `udl_ends`, and `udl_values` must have the same length.
Each distributed-load entry is constant from its start position to its end position.
Segments may be partial-span and may be combined with point loads.
Use zero-valued one-element vectors for a load family that is not present.

- `BeamLoadSetStatus(...)` and `BeamAnalyzeStatus(...)` validate the complete load set.
- `BeamShearAtLoads(...; x)`, `BeamMomentAtLoads(...; x)`, and `BeamDeflectionAtLoads(...; x)` return the superposed response at `x`.
- `BeamReactionLeftLoads(...)`, `BeamReactionRightLoads(...)`, and `BeamReactionMomentLoads(...)` return support reactions.
- `BeamMaxShearAtSamples(...; sample_positions)`, `BeamMaxMomentAtSamples(...; sample_positions)`, and `BeamMaxDeflectionAtSamples(...; sample_positions)` return sampled absolute maxima.
- `BeamShearSampleSeries(...)`, `BeamMomentSampleSeries(...)`, and `BeamDeflectionSampleSeries(...)` return unit-consistent vectors suitable for caller-owned tables or plotting code.

The sampled extrema are only as complete as the supplied sample positions.
Add the span ends, point-load positions, and any load-segment boundaries when a diagram or peak search should include those discontinuities.

## Response API

- `BeamShearAt(case; x)` returns internal shear at position `x`.
- `BeamMomentAt(case; x)` returns bending moment at position `x`.
- `BeamDeflectionAt(case; x)` returns elastic deflection at position `x`.
- `BeamMaxShear(...)`, `BeamMaxMoment(...)`, and `BeamMaxDeflection(...)` return closed-form peak magnitudes for the supported cases, using the same scalar argument order.
- `BeamResponseStatus(case; x)` reports the case and position status using the Core database status codes.

## Screening API

The screening helpers deliberately accept section properties and allowable values from the worksheet rather than coupling the analysis to a material or shape library:

- `BeamBendingStress(moment; section_modulus)`
- `BeamBendingUtilization(moment; section_modulus; allowable_stress)`
- `BeamBendingStatus(moment; section_modulus; allowable_stress; warning_threshold)`
- `BeamShearStress(shear; shear_area)`
- `BeamShearUtilization(shear; shear_area; allowable_stress)`
- `BeamShearStatus(shear; shear_area; allowable_stress; warning_threshold)`
- `BeamDeflectionUtilization(deflection; allowable_deflection)`
- `BeamDeflectionStatus(deflection; allowable_deflection; warning_threshold)`

These helpers compare demand against supplied screening capacities through the Core check-status contract.
They are not substitutes for a governing design standard.

## Reporting

`ShowBeamCaseSummary$(support; load_type; span; point_load; point_position; distributed_load; modulus; inertia)` renders the inputs and validation status.
`ShowBeamResponse$(support; load_type; span; point_load; point_position; distributed_load; modulus; inertia; x)` renders shear, moment, deflection, and query status at one location.
`ShowBeamLoadSummary$(support; span; point_loads; point_positions; udl_starts; udl_ends; udl_values; modulus; inertia)` renders the modular load-set metadata and status.
`ShowBeamLoadResponse$(support; span; point_loads; point_positions; udl_starts; udl_ends; udl_values; modulus; inertia; x)` renders the modular response at one location.
`ShowBeamLoadReactions$(...)` renders vertical and fixed-end reactions.
`ShowBeamLoadExtrema$(...; sample_positions)` renders sampled response maxima.

These report macros intentionally keep the calculation variables hidden while leaving the rendered value cells auditable.

See [`Examples/BeamAnalysisDemo.cpd`](../Examples/BeamAnalysisDemo.cpd) and [`Tests/Libraries/Analysis/BEAM_ANALYSIS_TEST.cpd`](../Tests/Libraries/Analysis/BEAM_ANALYSIS_TEST.cpd).
