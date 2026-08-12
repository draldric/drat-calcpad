# Repository artifact standards

## Purpose

The repository treats Core modules, tests, examples, and templates as maintained product surfaces.
Every artifact must have a defined user or verification purpose and must be removed when that purpose no longer exists.

## Core modules

- Keep reusable behavior in `Core/Src/` and regenerate `Core/DratCore.cpd`.
- Keep module boundaries aligned with one responsibility.
- Comment CalcPad-specific workarounds, numeric sentinels, registry schemas, unit-normalization behavior, and non-obvious engineering assumptions.
- Avoid apostrophes inside `#def` text values because CalcPad can interpret the remainder as formatted worksheet output.
- Do not add comments that only restate a clear function name or equation.
- Remove obsolete and duplicated public helpers before the first release instead of preserving accidental compatibility.

## Tests

Every CalcPad test states a `TEST PURPOSE` that identifies the maintained behavior it protects.
An automated regression worksheet defines and renders `all_tests`.
A worksheet that exists to exercise browser-only behavior must explicitly declare `TEST TYPE: BROWSER DIAGNOSTIC` and explain the manual observation it requires.

Delete a test when its covered behavior is removed.
Update its stated purpose when the public contract changes.
Do not retain tests that only reproduce abandoned experiments.

## Examples

Each example demonstrates one coherent end-user workflow.
It must:

- use a PascalCase filename ending in `Demo.cpd` unless it is itself a complete engineering calculation;
- enable Markdown and use the standard heading hierarchy instead of raw HTML headings;
- define the full document-control header, including Title, Purpose, and Scope;
- render the standard header, title, purpose, scope, and revision history;
- end with a conclusions section that explains what the result does and does not establish;
- avoid duplicating an unrelated feature that already has its own example.

Examples are teaching worksheets, not test fixtures.
Deterministic assertions belong under `Tests/`.

## Templates

`Templates/EngineeringCalculationTemplate.cpd` is the only general calculation template at the top level.
All other templates live in a category that identifies their purpose, such as `Templates/Libraries/` or a future discipline-specific calculation directory.

Every template states a `TEMPLATE PURPOSE` and must be usable as a starting point rather than merely demonstrating syntax.
Calculation templates follow the trusted calculation flow and clearly separate document control, basis, inputs, validation, methodology, calculations, checks, results, review, and conclusions.

## Enforcement

`Tools/VerifyRepository.ps1` checks filenames, required example report elements, test-purpose declarations, automated assertions or browser-diagnostic classification, and template organization.
The verifier complements engineering review; it cannot determine whether an equation, source, or acceptance criterion is technically appropriate.
