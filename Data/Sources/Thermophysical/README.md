# Thermophysical source record

## Identification

- Repository inputs: `ThermophysicalProperties.json`, `HelmholtzFluids.json`, and `IncompressibleGlycols.json`
- Dataset revision: 0.7.0, dated 2026-08-24
- Main JSON SHA-256 at audit: `54f12aa5894bcf86335cfa4a94e088e0ccac2516668e2769329a6f0f30280cec`
- Helmholtz JSON SHA-256 at audit: `2f29ec3fdd7774d9f2d85d16a8d3593aeaeb07f48f2b496c5b4067631a47b288`
- Incompressible-glycol JSON SHA-256 at audit: `209943e5c3506ae9ef4b904352b0f116395f3d6b3428805c9d7f53d4eb2df8b5`
- Source engine: CoolProp sampled through SMath plugin build `6.4.8214.13502`
- Equation source: IAPWS R7-97(2012) Revised Release
- Pure-fluid equation sources: the cited default EOS records for nitrogen, carbon dioxide, R11, R12, R13, R134a, R32, R1234yf, propane, isobutane, ammonia, and propylene glycol
- Aqueous-glycol equation source: Melinder MEG and MPG correlations curated from the pinned CoolProp incompressible records
- Pinned CoolProp revision: `5b9c32ac3cbedf7ec67fb4e23c65751ffee237db`
- Fluid keys: `Water`, equation-backed aqueous `MEG` and `MPG` from 0 to 60% by mass, and the twelve pure-fluid Helmholtz records listed above
- CoolProp license: MIT License
- CoolProp project: https://github.com/CoolProp/CoolProp

The original tank-heating worksheet did not preserve every complete CoolProp input-pair call or the CoolProp engine version behind the SMath plugin. These curves are therefore a reproducible migration baseline, not independent validation of phase, pressure, reference state, or design applicability.

The Region 1, Region 2, Region 4 saturation, and B23 coefficients are transcribed from the official IAPWS release and checked against every applicable computer-program verification point in its Tables 1, 5, 15, 35, and 36. The older sampled water curves still require an independently recorded CoolProp version, input pair, and pressure basis. The 50% ethylene-glycol public API now evaluates the maintained aqueous correlation directly.

The pure-fluid records retain the complete ideal and residual terms needed by the implemented Helmholtz backend, plus saturation-pressure and saturated-liquid-density ancillaries used to choose the pressure-temperature density root. Their upstream JSON hashes are embedded per fluid. CalcPad results are regression-checked against pinned CoolProp 8.0.0 values. R744 uses the carbon-dioxide record; it is an alias rather than duplicate coefficients. The pure propylene-glycol record has thermodynamic EOS properties but no transport correlations. Pure ethylene glycol is excluded because the pinned source has no qualified pure-fluid EOS, and the aqueous equations stop at 60% mass fraction. R401A is excluded because it is a zeotropic blend and requires mixture reducing, departure, and bubble/dew calculations. Two-phase quality calculations are not included.

The JSON is repository-owned generator input and is excluded from runtime distributions. CoolProp itself is not bundled. The generated `.cpd` values and attribution are distributed under DRAT's license together with the CoolProp and IAPWS notices in `THIRD-PARTY-NOTICES.md`.

Do not edit `Libraries/Thermophysical/ThermophysicalProperties.cpd` directly. Update the JSON records, retain the qualification notes, run the generator with `--helmholtz-source` and `--glycol-source`, and execute its schema and CalcPad regression tests. Use the two `ImportCoolProp...` tools when refreshing selected upstream pure-fluid or incompressible-glycol records.
