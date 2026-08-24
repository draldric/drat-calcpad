# Thermophysical source record

## Identification

- Repository inputs: `ThermophysicalProperties.json` and `HelmholtzFluids.json`
- Dataset revision: 0.4.0, dated 2026-08-23
- Main JSON SHA-256 at audit: `22c335b14230e844de76c45b2a92666efc53b2b36490b08c86eed7404d8fe942`
- Helmholtz JSON SHA-256 at audit: `53bae89ea4b591f3e3e8281d5a0b67b51fd2c77e6187e3269a5eebf54210d9e5`
- Source engine: CoolProp sampled through SMath plugin build `6.4.8214.13502`
- Equation source: IAPWS R7-97(2012) Revised Release
- Pure-fluid equation sources: Span et al. nitrogen EOS and Span-Wagner carbon-dioxide EOS
- Pinned CoolProp revision: `5b9c32ac3cbedf7ec67fb4e23c65751ffee237db`
- Fluid keys: `Water`, `INCOMP::MEG-50%`, `Nitrogen`, and `CarbonDioxide`
- CoolProp license: MIT License
- CoolProp project: https://github.com/CoolProp/CoolProp

The original tank-heating worksheet did not preserve every complete CoolProp input-pair call or the CoolProp engine version behind the SMath plugin. These curves are therefore a reproducible migration baseline, not independent validation of phase, pressure, reference state, or design applicability.

The Region 1, Region 2, Region 4 saturation, and B23 coefficients are transcribed from the official IAPWS release and checked against every applicable computer-program verification point in its Tables 1, 5, 15, 35, and 36. The 50% ethylene-glycol curves and the older sampled water curves still require an independently recorded CoolProp version, input pair, and pressure basis.

The nitrogen and carbon-dioxide records retain the complete ideal and residual terms needed by the implemented Helmholtz backend, plus saturation-pressure and saturated-liquid-density ancillaries used to choose the pressure-temperature density root. Their upstream JSON hashes are embedded per fluid. Gas, liquid, and supercritical CalcPad results are regression-checked against pinned CoolProp 8.0.0 values. Transport-property correlations and two-phase quality calculations are not included.

The JSON is repository-owned generator input and is excluded from runtime distributions. CoolProp itself is not bundled. The generated `.cpd` values and attribution are distributed under DRAT's license together with the CoolProp and IAPWS notices in `THIRD-PARTY-NOTICES.md`.

Do not edit `Libraries/Thermophysical/ThermophysicalProperties.cpd` directly. Update the JSON records, retain the qualification notes, run the generator with `--helmholtz-source`, and execute its schema and CalcPad regression tests. Use `Tools/ImportCoolPropHelmholtzFluids.py` when refreshing selected upstream pure-fluid records.
