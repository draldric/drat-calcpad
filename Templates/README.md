# Templates

## General calculation

`EngineeringCalculationTemplate.cpd` is the single general-purpose starting point.
It provides the complete trusted calculation and report structure without assuming an engineering discipline or design method.

## Specialized templates

Specialized templates are organized by what they create or calculate.

- `Libraries/PropertyLibraryTemplate.cpd` starts a guarded numeric property library with aliases, units, metadata, source reporting, and bounds policies.
- Future discipline-specific calculation templates should use a clear category such as `Analysis/`, `Structural/`, `Mechanical/`, or `Electrical/` rather than accumulating beside the general template.

Each specialized template must provide a meaningful starting structure, not merely a syntax sample.
