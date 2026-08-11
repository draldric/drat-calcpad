# Versioning policy

DRAT uses semantic versions for the generated Core and independently versioned components and libraries.

## Semantic versions

Use `MAJOR.MINOR.PATCH`:

- Increment `MAJOR` for incompatible changes that require worksheet or library migration.
- Increment `MINOR` for backward-compatible public functions, macros, statuses, or supported behavior.
- Increment `PATCH` for backward-compatible fixes that do not add a public capability.

Documentation-only, test-only, and build-tool-only changes do not require a Core API bump unless they change a documented runtime contract.

## Numeric API values

The compatibility manifest encodes semantic versions as:

```text
API = MAJOR*10000 + MINOR*100 + PATCH
```

Examples:

- Core `1.6.0` becomes `10600`.
- Validation `1.4.0` becomes `10400`.
- DataWrapper `0.3.2` becomes `302`.

Libraries compare numeric ranges because CalcPad conditional expressions cannot parse semantic-version strings.

## Core and component changes

When changing a public Core component:

1. Update the component version in its header comment.
2. Update the matching `DRAT_*_API` value in `Core/Src/CoreManifest.cpd`.
3. Update `DRATCoreVersion$` and `DRAT_CORE_API` when the distributed Core contract changes.
4. Rebuild `Core/DratCore.cpd`.
5. Update the API and status references.
6. Add regression coverage for each changed public helper.
7. Record the change in `CHANGELOG.md`.

The verification script confirms that declared Core and component versions match their numeric API values.

## Compatibility ranges

Library guards state the range that was actually tested:

```text
#if and(DRAT_CORE_API ≥ 40000; DRAT_CORE_API < 50000)
```

The upper bound excludes the next incompatible major API.
Increase the lower bound only when the library begins using a newer capability.

Do not claim compatibility with an API that has not been rendered through the library's supported example or tests.

## Library revisions

Engineering libraries version their data and interface independently from Core.
A library revision must change when any of these change:

- A public item, property, alias, or lookup function.
- A numeric value, unit mapping, valid range, source, or dataset revision.
- The meaning or applicability classification of a value.
- The minimum compatible Core or component API.

Data corrections are never silent.
Record the old behavior, new behavior, source, and engineering impact in the changelog or library-specific release notes.

## Releases and tags

Use tags only after the release checklist passes and the release commit is merged to `main`.
Tag Core releases as `vMAJOR.MINOR.PATCH`.
If libraries later ship independently, prefix their tags with the package name.
