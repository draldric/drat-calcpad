# Thermophysical raw data

`ThermophysicalProperties.json` is the maintained source for the generated CalcPad library one directory above.

The initial values were captured from the migrated tank-heating worksheet, which sampled the locally installed CoolProp engine through SMath plugin build `6.4.8214.13502` using the fluid keys `Water` and `INCOMP::MEG-50%`.
CoolProp is distributed under the [MIT License](https://github.com/CoolProp/CoolProp/blob/master/LICENSE).

The original worksheet did not preserve every complete CoolProp input-pair call.
Consequently, these values are retained as a reproducible migration baseline, not as independent confirmation of phase, pressure, reference-state, or design applicability.

Do not edit the generated `ThermophysicalProperties.cpd` directly.
Update the JSON, retain the source and qualification notes, run the generator, and execute the schema and CalcPad regression tests.
