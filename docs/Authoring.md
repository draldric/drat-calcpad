# Worksheet authoring components

`Core/Src/Authoring.cpd` provides explicit report-structure and layout components for calculation authors.
The components do not calculate engineering acceptance and do not register validation or check status.
They organize narrative, equations, compact records, alternatives, references, and results around the trusted calculation flow.

The authoring component API is `DRAT_AUTHORING_API = 10000` in generated Core 4.3.0.

## Heading ownership

The worksheet owns its H3-H6 hierarchy.
Reporting, validation, check, conclusion, variable, and review-summary macros never insert headings on behalf of the worksheet.
Use the explicit helpers when an HTML heading is preferable to Markdown, including around content that requires `#md off`:

```text
H3$(Heat-Transfer Analysis)
H4$(Resistance Model)
H5$(External Convection)
H6$(Property Evaluation)
```

`H3$` starts a new printed page through the shared stylesheet.
`H4$`, `H5$`, and `H6$` remain numbered subsections on the current page.
The cover-page helpers remain responsible for the document-control H1-H2 content.

## Narrative components

```text
SectionIntro$(This section calculates the governing heat loss.)
CalculationStep$(Evaluate the cylindrical resistance)
Divider$
```

`SectionIntro$` introduces a section without adding another heading.
`CalculationStep$` labels one calculation stage without changing the heading counters.
`Divider$` inserts a consistently spaced visual separator.

## Semantic callouts

```text
Note$(Supplementary information.)
Basis$(Reason for a modeling choice.)
Important$(Information that requires attention.)
Warning$(A condition that could affect applicability.)
ErrorMessage$(The calculation cannot continue for the stated reason.)
```

Callouts include visible text labels and border styles, so meaning does not rely on color alone.
They are author annotations only.
Use validation results, engineering checks, calculation status, and document-review status for machine-readable outcomes.

## Lists and definitions

Lists deliberately do not generate headings:

```text
H4$(Procedure)
BeginNumberedList$
AddNumberedItem$(Validate the inputs.)
AddNumberedItem$(Evaluate the response.)
AddNumberedItem$(Review the engineering checks.)
EndNumberedList$
```

`BeginBulletList$`, `AddBullet$`, and `EndBulletList$` provide the equivalent bulleted form.

Use a compact definition list for terminology and abbreviations:

```text
BeginDefinitions$
AddDefinition$(MAWP; Maximum allowable working pressure.)
AddDefinition$(MDMT; Minimum design metal temperature.)
EndDefinitions$
```

Definitions are different from `BeginVariables$`: definitions describe terminology, while the variable table records calculation symbols and units for the document.

## Compact key-value tables

```text
TableCaption$(1; Selected case)
BeginKeyValueTable$
AddKeyValue$(Design pressure; design_pressure)
AddKeyValue$(Design temperature; design_temperature)
AddKeyText$(Operating case; Normal operation)
EndKeyValueTable$
```

`AddKeyValue$` renders a CalcPad expression in a right-aligned value cell.
`AddKeyText$` renders prose in the same right-aligned value column.
Labels and alternative names remain left aligned, keeping every two-column component visually consistent.

## Equations and local definitions

Equation blocks retain CalcPad-native equation rendering and substitutions:

```text
BeginEquation$(HT-1; Cylindrical insulation resistance)
R_cond(r_i; r_o; k; L) = ln(r_o/r_i)/(2*π*k*L)
EndEquation$

BeginWhere$
AddWhereWithUnits$(r_i; Inner radius; m)
AddWhereWithUnits$(r_o; Outer radius; m)
AddWhere$(k; Thermal conductivity)
EndWhere$
```

Use `EquationReference$(HT-1)` to link narrative back to the stable equation identifier.
Equation bodies are left aligned so the global justified-prose rule does not stretch equations across the available width.
The local where table documents only the equation beside it; it does not replace the document-wide variable list.

## References, captions, and cross-references

`Cite$(reference_id)` links to a reference already registered with `AddReference$`.
`SourceNote$(reference_id; text)` renders a compact provenance statement with the same link.

Tables and figures use explicit stable identifiers:

```text
TableCaption$(2; Calculated alternatives)
TableReference$(2)

FigureCaption$(F1; Beam free-body diagram)
FigureReference$(F1)
```

Explicit identifiers remain stable when document order changes and are easier to use in review comments than automatic CSS counters.
The caption is a separate component so the same styling can be used with HTML tables, CalcPad plots, and Plotly figures.

## Results and comparisons

```text
Result$(Required heating time; heating_time)
Decision$(Selected arrangement; Four parallel coils)

BeginComparison$(Heating alternatives)
AddComparisonValue$(Four parallel coils; four_coil_time)
AddComparisonValue$(Six-pass circuit; six_pass_time)
AddComparisonText$(Selected arrangement; Four parallel coils)
EndComparison$
```

These components present outcomes but do not assign pass, warning, or failure status.
Register the applicable engineering check separately.

## Print grouping and empty states

```text
BeginKeepTogether$
TableCaption$(3; Short result table)
BeginKeyValueTable$
AddKeyValue$(Governing utilization; utilization)
EndKeyValueTable$
EndKeepTogether$
```

`BeginKeepTogether$` and `EndKeepTogether$` request that the wrapped content remain on one printed page.
Browsers may still split a block when it is taller than the available page.

`EmptyState$(text)` explicitly explains an intentionally empty result area.
Do not use an empty state to imply that validation, checks, limitations, or review are complete merely because their registries contain no entries.

## Formatting contract

- Use Markdown for ordinary prose, emphasis, and links.
- Use authoring macros where consistent HTML structure, expression rendering, cross-references, or print behavior adds value.
- Do not place a semicolon inside one text argument. CalcPad treats every semicolon as a macro-argument separator; use a period, comma, colon, or separate component instead.
- Do not nest unmatched `Begin...$` and `End...$` components.
- Use relative paths for any images supplied directly through CalcPad.
- Do not use author callouts as substitutes for registered engineering status.
- Keep H3-H6 calls visible at worksheet level; do not hide headings inside table or library reporting macros.

See `Examples/AuthoringDemo.cpd` for a complete pipe-insulation screening worksheet and `Tests/Core/AuthoringTest.cpd` for the deterministic rendering fixture.
