# Static beam analysis library

`Libraries/Analysis/BeamAnalysis.cpd` provides a small, auditable response layer for common prismatic-beam cases.

## Scope

The current release supports:

- simply supported beams;
- cantilever beams;
- any finite set of point loads at user-specified positions; and
- any finite set of piecewise-constant distributed-load segments;
- axial point loads and piecewise-constant axial-load segments; and
- sampled loading, shear, bending-moment, axial-force, and displacement diagrams through the Core Plotting wrapper.

The equations are closed-form Euler-Bernoulli elastic beam equations for static, small-deflection response.
The modular functions use linear superposition of the supported load families, so each load vector must contain one physical quantity only.
The caller supplies span, load, elastic modulus, and second moment of area with units.

The library does not provide code capacities, factored load combinations, lateral-torsional buckling, shear-deformation, plastic, dynamic, or stability analysis.
Those decisions remain worksheet- and code-specific.

## Recommended beam-model API

The model API stores the complete definition in one mixed-unit CalcPad vector.
Accessor functions retain the units of each stored element, while the public calculations accept the model directly:

```text
#hide
beam = BeamModel(BEAM_SIMPLE_SUPPORTED; 6m; 200GPa; 8*10^-6m^4)
beam = BeamWithPointLoads(beam; [10kN; 4kN]; [2m; 4m])
beam = BeamWithDistributedLoads(beam; [0m; 3m]; [3m; 6m]; [1kN/m; 1kN/m])
beam = BeamWithSampleCount(beam; 61)
#show

M_mid = BeamMoment(beam; 3m)
ShowBeamModel$(beam)
ShowBeamDiagrams$(beam_plot; beam)
```

`BeamModel(...)` returns a model with the supplied beam properties, zero-valued defaults for every load family, and a default sample count of 61.
Each `BeamWith...` function returns an updated model, so assign the result back to the beam variable as shown above.
The update functions replace one load family without repeating the beam properties:

- `BeamWithPointLoad(model; load; position)` or `BeamWithPointLoads(model; loads; positions)`;
- `BeamWithUDL(model; load)` for one full-span UDL;
- `BeamWithDistributedLoads(model; starts; ends; loads)` for piecewise-constant transverse loading;
- `BeamWithAxialPointLoads(model; loads; positions)`;
- `BeamWithAxialDistributedLoads(model; starts; ends; loads)`;
- `BeamWithDiagramMoments(model; positions; moments)` for schematic-only moment markers; and
- `BeamWithSampleCount(model; count)`.

The concise calculation functions are:

- `BeamModelStatus(model)`;
- `BeamShear(model; x)`, `BeamMoment(model; x)`, `BeamDeflection(model; x)`, and `BeamAxial(model; x)`;
- `BeamLeftReaction(model)`, `BeamRightReaction(model)`, and `BeamFixedEndMoment(model)`;
- `BeamSamplePositions(model)` and the four `Beam...Series(model)` helpers; and
- `BeamPeakShear(model)`, `BeamPeakMoment(model)`, and `BeamPeakDeflection(model)`.

The record is versioned and self-describing rather than dependent on a global registry.
Use accessors such as `BeamModelSpan(model)`, `BeamModelPointLoads(model)`, and `BeamModelModulus(model)` when individual fields must be audited or reused.

## Legacy scalar API

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

## Explicit low-level load-set API

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

`BeamStations(span; count)` creates an evenly spaced, unit-consistent station vector for diagrams and screening searches.
`BeamNumericSeries(values)` converts a unit-valued vector to numeric ordinates one scalar at a time for Plotting-wrapper calls.

The axial convention is positive toward increasing `x`, with returned internal axial force positive in tension.
`BeamAxialStatus(...)`, `BeamAxialAtLoads(...)`, and `BeamAxialSampleSeries(...)` provide validation, point evaluation, and sampled axial response.

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

The recommended model-level report macros are:

- `ShowBeamModel$(model)` for the definition, load-family counts, and combined input status;
- `ShowBeamResponseAt$(model; x)` for shear, moment, and deflection at one position;
- `ShowBeamReactions$(model)`;
- `ShowBeamExtrema$(model)` using the model sample count;
- `ShowBeamScreening$(model; section_modulus; shear_area; allowable_stress; allowable_deflection)`; and
- `ShowBeamFBD$(id; model)` for the loading schematic;
- `ShowBeamShearPlot$(id; model)`, `ShowBeamMomentPlot$(id; model)`, `ShowBeamAxialPlot$(id; model)`, and `ShowBeamDeflectionPlot$(id; model)` for individual response diagrams; or
- `ShowBeamDiagrams$(id; model)` for the complete diagram set.

The model-level diagram macros temporarily switch Markdown processing off while emitting Plotly HTML and restore it to on afterward.
CalcPadCE does not expose the prior Markdown state, so a worksheet that intentionally operates with `#md off` should reapply `#md off` after calling one of these model-level macros.

The following explicit report macros remain available for compatibility and specialized callers.

`ShowBeamCaseSummary$(support; load_type; span; point_load; point_position; distributed_load; modulus; inertia)` renders the inputs and validation status.
`ShowBeamResponse$(support; load_type; span; point_load; point_position; distributed_load; modulus; inertia; x)` renders shear, moment, deflection, and query status at one location.
`ShowBeamLoadSummary$(support; span; point_loads; point_positions; udl_starts; udl_ends; udl_values; modulus; inertia)` renders the modular load-set metadata and status.
`ShowBeamLoadResponse$(support; span; point_loads; point_positions; udl_starts; udl_ends; udl_values; modulus; inertia; x)` renders the modular response at one location.
`ShowBeamLoadReactions$(...)` renders vertical and fixed-end reactions.
`ShowBeamLoadExtrema$(...; sample_positions)` renders sampled response maxima.

When the Core Plotting API is in the supported 3.2.x range, the following helpers render Plotly diagrams:

- `ShowBeamSchematic$(id; span; point_loads; point_positions; udl_starts; udl_ends; udl_values; axial_loads; axial_positions; axial_starts; axial_ends; axial_values; moment_positions; moment_values)` shows triangular supports, shaded distributed-load regions, load-scaled color-coded arrows, and applied-moment symbols;
- `ShowBeamShearDiagram$(id; ...; sample_positions)` shows sampled shear;
- `ShowBeamMomentDiagram$(id; ...; sample_positions)` shows sampled bending moment;
- `ShowBeamAxialDiagram$(id; ...; sample_positions)` shows sampled internal axial force; and
- `ShowBeamDeflectionDiagram$(id; ...; sample_positions)` shows sampled displacement.

The diagram helpers convert unit-valued vectors to numeric plotting ordinates internally.
Each distributed-load region and its arrows use the same normalized ordinate, so the shaded height is proportional to the load magnitude and the arrow tails coincide with its boundary.
The schematic uses red for transverse point loads, blue for distributed loads, green for axial loads, and purple for applied moments; the legend is intentionally hidden.
Include the span ends, point-load positions, and segment boundaries in `sample_positions` when exact jumps or extrema must be visible.
Applied moments are currently visual schematic inputs only; the closed-form response functions do not yet include concentrated moment loads in their equilibrium equations.

These report macros intentionally keep the calculation variables hidden while leaving the rendered value cells auditable.

See [`Examples/BeamAnalysisDemo.cpd`](../Examples/BeamAnalysisDemo.cpd) and [`Tests/Libraries/Analysis/BEAM_ANALYSIS_TEST.cpd`](../Tests/Libraries/Analysis/BEAM_ANALYSIS_TEST.cpd).
