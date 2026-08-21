# Engineering data sources

This hierarchy contains repository-owned generator inputs and provenance records. It is deliberately separate from `Libraries/`, which contains the self-contained CalcPad runtime libraries copied into distributions.

Each dataset folder records:

- the source, edition, revision, retrieval date, and source-file hash;
- whether the raw input is repository-owned or externally obtained;
- the redistribution disposition for both the raw input and generated output;
- scope, units, conversions, missing-value policy, exclusions, and qualification limits;
- the command and dependency environment used for deterministic generation.

Externally obtained raw files must not be committed unless redistribution permission is explicit. Keep those files outside the repository, verify their recorded hash when they are used for qualification, and never add them to a runtime distribution. A repository-owned curated compilation may be committed when its factual scope, transformation, attribution, and redistribution disposition are documented.

The consolidated audit and release dispositions are documented in [`docs/DataProvenance.md`](../../docs/DataProvenance.md).
