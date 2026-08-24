# Thermophysical source record

## Identification

- Repository input: `ThermophysicalProperties.json`
- Dataset revision: 0.2.0, dated 2026-08-23
- SHA-256 at audit: `581b451143945569e0c2aea7df9d02b0b1b3d17a2f0e32cc9beab81777ce01c3`
- Source engine: CoolProp sampled through SMath plugin build `6.4.8214.13502`
- Equation source: IAPWS R7-97(2012) Revised Release
- Fluid keys: `Water` and `INCOMP::MEG-50%`
- CoolProp license: MIT License
- CoolProp project: https://github.com/CoolProp/CoolProp

The original tank-heating worksheet did not preserve every complete CoolProp input-pair call or the CoolProp engine version behind the SMath plugin. These curves are therefore a reproducible migration baseline, not independent validation of phase, pressure, reference state, or design applicability.

The Region 1, Region 2, Region 4 saturation, and B23 coefficients are transcribed from the official IAPWS release and checked against every applicable computer-program verification point in its Tables 1, 5, 15, 35, and 36. The 50% ethylene-glycol curves and the older sampled water curves still require an independently recorded CoolProp version, input pair, and pressure basis.

The JSON is repository-owned generator input and is excluded from runtime distributions. CoolProp itself is not bundled. The generated `.cpd` values and attribution are distributed under DRAT's license together with the CoolProp and IAPWS notices in `THIRD-PARTY-NOTICES.md`.

Do not edit `Libraries/Thermophysical/ThermophysicalProperties.cpd` directly. Update the JSON, retain the qualification notes, run the generator, and execute its schema and CalcPad regression tests.
