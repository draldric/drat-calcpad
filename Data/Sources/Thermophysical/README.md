# Thermophysical source record

## Identification

- Repository input: `ThermophysicalProperties.json`
- Dataset revision: 0.1.0, dated 2026-08-15
- SHA-256 at audit: `13d7ea2b9d58250f8c10af6cbcc82db17556401eb5f6bb41f7ad5118b11a0a60`
- Source engine: CoolProp sampled through SMath plugin build `6.4.8214.13502`
- Fluid keys: `Water` and `INCOMP::MEG-50%`
- CoolProp license: MIT License
- CoolProp project: https://github.com/CoolProp/CoolProp

The original tank-heating worksheet did not preserve every complete CoolProp input-pair call or the CoolProp engine version behind the SMath plugin. These curves are therefore a reproducible migration baseline, not independent validation of phase, pressure, reference state, or design applicability.

Water and steam values must be independently qualified against the applicable IAPWS release before the dataset claims an IAPWS or design-grade basis. The 50% ethylene-glycol curves also require an independently recorded CoolProp version, input pair, and pressure basis.

The JSON is repository-owned generator input and is excluded from runtime distributions. CoolProp itself is not bundled. The generated `.cpd` values and attribution are distributed under DRAT's license together with the CoolProp notice in `THIRD-PARTY-NOTICES.md`.

Do not edit `Libraries/Thermophysical/ThermophysicalProperties.cpd` directly. Update the JSON, retain the qualification notes, run the generator, and execute its schema and CalcPad regression tests.
