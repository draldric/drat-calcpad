# Thermophysical Properties

`Libraries/Thermophysical/ThermophysicalProperties.cpd` is the generated, self-contained DRAT property library for thermal and fluid calculations.
It does not require CoolProp or another property engine at worksheet runtime.

Release `0.7.0` provides four complementary backends and two state-query interfaces:

- Water specific heat, saturation pressure, and latent heat of vaporization.
- Equation-based density, specific heat, dynamic viscosity, thermal conductivity, and freezing limits for aqueous ethylene-glycol and propylene-glycol mixtures from 0% through 60% glycol by mass.
- IAPWS-IF97 fundamental equations for stable single-phase water and steam in Regions 1 and 2.
- IAPWS-IF97 Region 4 forward and inverse saturation equations plus the B23 boundary used for region selection.
- Fundamental Helmholtz equations of state for pure nitrogen, carbon dioxide, R11, R12, R13, R134a, R32, R1234yf, R290, R600a, R717, and propylene glycol, including gas, liquid, and supercritical pressure-temperature states.
- A CoolProp-shaped `ThermoProps` selector over the implemented equation backends.
- A unit-aware `PropsSI` compatibility selector and preprocessing-macro call form, plus explicit scalar-SI helpers.

These curves reproduce the values embedded in the migrated tank-heating calculation.
They were sampled from CoolProp through SMath plugin build `6.4.8214.13502`.
The older water curves remain a traceable migration baseline. The glycol-mixture runtime path no longer interpolates the migrated 50% samples; it evaluates the maintained Melinder correlations directly.

## Loading

Load Core first and then the library directly:

```text
#include ../Core/DratCore.cpd
#include ../Libraries/Thermophysical/ThermophysicalProperties.cpd
```

The library requires Core API 4.x and DataWrapper API 0.3.3 or newer.
It guards its complete body and reports a compatibility error if either dependency is incompatible.

## Unified state selector

`ThermoProps` follows the six-argument shape of CoolProp's generic property query while retaining CalcPad units and stable numeric IDs:

```text
h = ThermoProps(THERMO_OUT_ENTHALPY; THERMO_IN_PRESSURE; 3MPa; THERMO_IN_TEMPERATURE; 500K; THERMO_WATER)
h_status = ThermoPropsStatus(THERMO_OUT_ENTHALPY; THERMO_IN_PRESSURE; 3MPa; THERMO_IN_TEMPERATURE; 500K; THERMO_WATER)
```

The two inputs can be supplied in either order. Version `0.7.0` supports the pressure-temperature pair for `THERMO_WATER` and every pure-fluid constant listed below. Glycol-water mixtures use a separate concentration-aware API because concentration is a required input. Unsupported fluids, outputs, inputs, repeated inputs, unavailable IF97 regions, out-of-range Helmholtz states, and saturation-boundary states return explicit statuses. `ThermoPropsStatus$(status)` renders the unified, IF97, or Helmholtz status; a successful non-water query renders the backend-neutral `Valid thermophysical state` message.

Input IDs are `THERMO_IN_PRESSURE` and `THERMO_IN_TEMPERATURE`. Output IDs are `THERMO_OUT_SPECIFIC_VOLUME`, `THERMO_OUT_DENSITY`, `THERMO_OUT_ENTHALPY`, `THERMO_OUT_INTERNAL_ENERGY`, `THERMO_OUT_ENTROPY`, `THERMO_OUT_CP`, `THERMO_OUT_CV`, and `THERMO_OUT_SOUND_SPEED`.

Unlike CoolProp's `PropsSI`, values are passed and returned with CalcPad units instead of unitless SI numbers. The ID-based interface also avoids fragile string comparisons in generated worksheets. Its call shape is reserved for future pressure-enthalpy, pressure-entropy, and quality input pairs.

## PropsSI compatibility interface

`PropsSI` uses CoolProp's six-argument order while requiring CalcPad units on pressure and temperature inputs and returning a dimensioned result. It retains numeric keys and fluid IDs:

```text
rho = PropsSI(CP_D; CP_P; 100kPa; CP_T; 300K; THERMO_NITROGEN)
h = PropsSI(CP_H; CP_T; 300K; CP_P; 100kPa; THERMO_NITROGEN)
status = PropsSIStatus(CP_D; CP_P; 100kPa; CP_T; 300K; THERMO_NITROGEN)
```

Pressure and absolute-temperature inputs must carry compatible units. Outputs carry their corresponding SI dimensions, so a density can be displayed in `kg/m^3` or converted by CalcPad to another compatible unit. Supported pure-fluid output keys are `CP_P`, `CP_T`, `CP_D`/`CP_DMASS`, `CP_H`/`CP_HMASS`, `CP_U`/`CP_UMASS`, `CP_S`/`CP_SMASS`, `CP_C`/`CP_CPMASS`, `CP_CV`/`CP_CVMASS`, `CP_A`/`CP_SPEED_OF_SOUND`, and the DRAT extension `CP_VSPEC`. Only the `CP_P` and `CP_T` input pair is currently accepted, in either order.

For hand-authored worksheets, a preprocessing macro provides a call that is visually close to CoolProp:

```text
rho = PropsSI$(D; P; 100kPa; T; 300K; Nitrogen)
h = PropsSI$(H; T; 300K; P; 100kPa; R134a)
```

CalcPad string macros are expanded before numeric parsing, so the key and fluid tokens are deliberately unquoted. This is not runtime string dispatch: computed strings, backend prefixes, arbitrary aliases, and composition syntax inside a fluid name cannot be accepted. Use the numeric `PropsSI` form for generated calculations.

For a mechanical translation that must retain CoolProp's raw SI-number convention, use `PropsSIScalar` and `PropsSIScalarStatus`. Their pressure inputs are numbers in pascals, temperature inputs are numbers in kelvins, and results are unitless SI magnitudes:

```text
rho_SI = PropsSIScalar(CP_D; CP_P; 100000; CP_T; 300; THERMO_NITROGEN)
```

Aqueous glycol concentration therefore uses an explicit seventh argument:

```text
rho_pg = PropsSIIncompressible(CP_D; CP_T; 313.15K; CP_P; 101.325kPa; GLYCOL_PROPYLENE; 0.30)
mu_eg = PropsSIIncompressible(CP_V; CP_P; 101.325kPa; CP_T; 333.15K; GLYCOL_ETHYLENE; 0.50)
```

The incompressible selector supports `CP_D`, `CP_C`, `CP_V` for dynamic viscosity, and `CP_L` for thermal conductivity. Pressure must be positive but does not alter the current incompressible correlations. Concentration, temperature, and freezing limits remain enforced by `PropsSIIncompressibleStatus`. `PropsSIIncompressibleScalar` provides the corresponding raw-SI compatibility path.

`ThermoProps` remains the native DRAT selector, while unit-aware `PropsSI` makes the call order familiar when translating CoolProp-style equations. Use the scalar variants only where an existing generator or equation set specifically requires raw SI numbers.

## Pure-fluid Helmholtz equations

The pure-fluid backend evaluates the published reduced Helmholtz-energy equations and their analytic first and second derivatives. Density is recovered from pressure and temperature with a bounded, phase-aware Newton iteration; specific volume, density, enthalpy, internal energy, entropy, isobaric and isochoric heat capacity, and speed of sound are then derived from the solved state.

```text
p = 10MPa
T = 320K

rho_co2 = ThermoProps(THERMO_OUT_DENSITY; THERMO_IN_PRESSURE; p; THERMO_IN_TEMPERATURE; T; THERMO_CARBON_DIOXIDE)
h_co2 = ThermoProps(THERMO_OUT_ENTHALPY; THERMO_IN_PRESSURE; p; THERMO_IN_TEMPERATURE; T; THERMO_CARBON_DIOXIDE)
state_status = ThermoPropsStatus(THERMO_OUT_DENSITY; THERMO_IN_PRESSURE; p; THERMO_IN_TEMPERATURE; T; THERMO_CARBON_DIOXIDE)
```

The supported constants are:

- `THERMO_NITROGEN`
- `THERMO_CARBON_DIOXIDE`, with alias `THERMO_R744`
- `THERMO_R11`, `THERMO_R12`, `THERMO_R13`, `THERMO_R134A`, `THERMO_R32`, and `THERMO_R1234YF`
- `THERMO_R290`, with alias `THERMO_PROPANE`
- `THERMO_R600A`, with alias `THERMO_ISOBUTANE`
- `THERMO_R717`, with alias `THERMO_AMMONIA`
- `THERMO_PROPYLENE_GLYCOL`

Each record uses the default pure-fluid EOS at the pinned CoolProp revision. The coefficients, ideal-gas terms, supported residual term families, saturation-pressure ancillary, and saturated-liquid-density ancillary are maintained in `HelmholtzFluids.json` with a source citation and upstream file hash.

All exposed state properties for these fluids are equation-derived; no sampled property tables are used. Transport properties such as viscosity and thermal conductivity are not yet exposed. Saturation-boundary pressure-temperature queries are rejected because the input pair does not specify phase quality.

The pure propylene-glycol record provides thermodynamic state properties through the Eisenbach et al. fundamental EOS. It does not provide viscosity or thermal conductivity. Pure ethylene glycol is not exposed as a pure-fluid constant: the pinned CoolProp source has no pure ethylene-glycol Helmholtz record, and extending the aqueous correlation beyond its 60% mass-fraction limit would be unqualified extrapolation.

## Aqueous glycol equations

Use `GLYCOL_ETHYLENE` or `GLYCOL_PROPYLENE`, a supported property ID, a Celsius temperature quantity, and glycol mass fraction:

```text
x_glycol = 0.30
rho_pg = GlycolPROP(GLYCOL_PROPYLENE; THERMO_P_DENSITY; 40°C; x_glycol)
rho_status = GlycolPROPStatus(GLYCOL_PROPYLENE; THERMO_P_DENSITY; 40°C; x_glycol)

Cp_eg = EgWaterSpecificHeatTX(60°C; 0.50)
mu_pg = PgWaterDynamicViscosityTX(40°C; 0.30)
```

Supported mixture properties are `THERMO_P_DENSITY`, `THERMO_P_SPECIFIC_HEAT`, `THERMO_P_DYNAMIC_VISCOSITY`, and `THERMO_P_THERMAL_CONDUCTIVITY`. Convenience functions use the `EgWater...TX` and `PgWater...TX` prefixes. `GlycolFreezeK(family; x)` returns the correlated freezing temperature in kelvins, and `GlycolStatus$(status)` renders a status description.

Both families enforce 0 to 0.60 mass fraction and the source temperature range. A state below its concentration-dependent freezing correlation returns `GLYCOL_ERR_FROZEN`. These are incompressible correlations; pressure is not an input. The existing `Eg50...T` and `ThermoPROP(THERMO_EG_50; ...)` calls are backward-compatible equation-backed aliases at `x = 0.50`. Clamp remains available, while extrapolation outside the equation range is rejected.

R401A is intentionally not represented as a pure fluid. It is a zeotropic R22/R152a/R124 blend with composition-dependent reducing and departure functions and temperature glide. Supporting it correctly requires a mixture backend and phase-aware bubble/dew handling; substituting a pure-fluid or averaged equation would give a misleading interface.

## IAPWS-IF97 pressure-temperature states

The IF97 API accepts unit-aware pressure and absolute temperature values:

```text
p = 3MPa
T = 500K

region = If97RegionPT(p; T)
status = If97RegionPTStatus(p; T)

rho = If97DensityPT(p; T)
v = If97SpecificVolumePT(p; T)
h = If97EnthalpyPT(p; T)
u = If97InternalEnergyPT(p; T)
s = If97EntropyPT(p; T)
Cp = If97CpPT(p; T)
Cv = If97CvPT(p; T)
w = If97SoundSpeedPT(p; T)
```

`If97RegionPT` returns `IF97_REGION_1`, `IF97_REGION_2`, or `IF97_REGION_UNSUPPORTED`.
The status helper rejects non-positive pressure, pressure above 100 MPa, temperature outside the implemented range, saturation-line states that require phase quality, and states in Region 3.
Region 5 and the special metastable-vapor equation are also outside this release.

The lower-level IF97 selector supports generated calculations when the input pair is already known to be pressure-temperature:

```text
h = If97PROPPT(IF97_P_ENTHALPY; p; T)
h_status = If97PROPPTStatus(IF97_P_ENTHALPY; p; T)
```

Available IDs are `IF97_P_SPECIFIC_VOLUME`, `IF97_P_DENSITY`, `IF97_P_ENTHALPY`, `IF97_P_INTERNAL_ENERGY`, `IF97_P_ENTROPY`, `IF97_P_CP`, `IF97_P_CV`, and `IF97_P_SOUND_SPEED`.
Rejected typed queries return a dimensioned undefined value.
Use `If97Status$(status)` to render the IF97-specific status description.

Saturation queries are independent of the single-phase property selector:

```text
p_sat = If97SaturationPressureT(500K)
T_sat = If97SaturationTemperatureP(1MPa)
```

Their status helpers enforce the official saturation range from 273.15 K through 647.096 K and from 0.000611213 MPa through 22.064 MPa.

## Typed property functions

Typed functions accept a unit-aware absolute temperature:

```text
T_process = 60°C

rho_eg = Eg50DensityT(T_process)
Cp_eg = Eg50SpecificHeatT(T_process)
mu_eg = Eg50DynamicViscosityT(T_process)
k_eg = Eg50ThermalConductivityT(T_process)

Cp_water = WaterSpecificHeatT(T_process)
P_sat = WaterSaturationPressureT(T_process)
h_fg = WaterLatentHeatT(T_process)
```

Each typed value helper has a status helper with the same prefix:

```text
rho_status = Eg50DensityTStatus(T_process)
pressure_status = WaterSaturationPressureTStatus(T_process)
```

The typed helpers preserve the property dimension on rejected queries by returning a dimensioned undefined value.
Call the status helper before using a result in an engineering check or calculation branch.

## Generic property functions

Stable IDs support catalog-style and generated workflows:

```text
THERMO_WATER
THERMO_EG_50

THERMO_P_DENSITY
THERMO_P_SPECIFIC_HEAT
THERMO_P_DYNAMIC_VISCOSITY
THERMO_P_THERMAL_CONDUCTIVITY
THERMO_P_SATURATION_PRESSURE
THERMO_P_LATENT_HEAT
```

The generic strict lookup is:

```text
value = ThermoPROP(fluid; property; temperature)
status = ThermoPROPStatus(fluid; property; temperature; method; bounds_policy)
```

`ThermoPROPAtC` accepts a unitless numeric value explicitly expressed on the Celsius scale.
`ThermoPROPClamped` and `ThermoPROPExtrapolated` expose the DataWrapper bounds policies, but strict lookup is the recommended engineering default.
Do not use extrapolation merely to suppress an out-of-range status.

The status contract distinguishes:

- Unknown fluid ID: `DB_ERR_NAME`.
- Unknown property ID: `DB_ERR_PROPERTY`.
- Property unavailable for the selected fluid: `DB_ERR_MISSING`.
- Query outside the validated curve: `DB_ERR_BELOW_RANGE` or `DB_ERR_ABOVE_RANGE`.
- Invalid interpolation method or bounds policy: the corresponding DataWrapper error.

## Range and provenance

The metadata API is derived from the same generated records as the value lookup:

```text
ThermoTMin(fluid; property)
ThermoTMax(fluid; property)
ThermoSourceID(fluid; property)
ThermoDataRevision(fluid; property)
ThermoFluidConcentrationMassFraction(fluid)
```

`ThermoDatasetStatus` checks the generated curve and metadata shapes.
`ShowThermoDatasetSummary$`, `ShowThermoSourceRecord$(source)`, `ShowThermoFluidRecord$(fluid)`, and `ShowThermoProperty$(fluid; property; temperature)` render focused tables without creating report headings.
The worksheet owns its heading hierarchy.

## Raw data and generation

The maintained inputs are `Data/Sources/Thermophysical/ThermophysicalProperties.json`, `HelmholtzFluids.json`, and `IncompressibleGlycols.json` in the same directory.
They store curve and IF97 records, curated pure-fluid equation records, and concentration-aware aqueous-glycol coefficients respectively.
The committed `.cpd` library is generated:

```powershell
python Tools/GenerateThermophysicalLibrary.py `
    Data/Sources/Thermophysical/ThermophysicalProperties.json `
    Libraries/Thermophysical/ThermophysicalProperties.cpd `
    --helmholtz-source Data/Sources/Thermophysical/HelmholtzFluids.json `
    --glycol-source Data/Sources/Thermophysical/IncompressibleGlycols.json
```

Check that the generated file is current without rewriting it:

```powershell
python Tools/GenerateThermophysicalLibrary.py `
    Data/Sources/Thermophysical/ThermophysicalProperties.json `
    Libraries/Thermophysical/ThermophysicalProperties.cpd `
    --helmholtz-source Data/Sources/Thermophysical/HelmholtzFluids.json `
    --glycol-source Data/Sources/Thermophysical/IncompressibleGlycols.json `
    --check
```

The generator uses only the Python standard library.
It rejects unknown units, duplicate IDs or curve keys, duplicate public functions, non-finite values, unequal axes, non-increasing temperatures, incomplete IF97 coefficient series, unsupported Helmholtz term families, and misaligned coefficient arrays before atomically replacing the generated library.

`Tools/ImportCoolPropHelmholtzFluids.py` is the maintenance importer for the selected upstream pure-fluid JSON records. It selects a configured EOS record, accepts only implemented equation-term and ancillary families, verifies the expected source citation key, records the pinned CoolProp Git revision and file hashes, validates the complete combined dataset, and then replaces `HelmholtzFluids.json` atomically.

`Tools/ImportCoolPropIncompressibleGlycols.py` performs the corresponding pinned import for CoolProp's MEG and MPG incompressible records. It requires a mass-fraction basis, the expected Melinder reference and equation families, both records exactly once, and records each upstream hash before atomic output replacement.

## Qualification

`Tests/Libraries/Thermophysical/ThermophysicalPropertiesTest.cpd` verifies the sampled curves and every Region 1, Region 2, B23 boundary, saturation-pressure, and saturation-temperature computer-program verification point published in IAPWS R7-97(2012) Tables 1, 5, 15, 35, and 36.
It also checks N2 and CO2 gas, liquid, and supercritical states, representative states for every supported refrigerant, pure propylene glycol, and both aqueous glycol families against CoolProp 8.0.0. Those checks exercise density, enthalpy, heat capacity, sound speed, transport correlations, concentration and freezing limits, equation ranges, saturation-boundary rejection, region selection, units, and dimensioned undefined results.
`Tests/Tooling/ThermophysicalGeneratorTest.py` verifies the raw-data schema and stale-output detection.

The curve backend should eventually be checked against independent governing sources, not only the engine used to generate it.
The IF97 backend is transcribed and regression-checked directly against the official IAPWS release, but worksheet authors remain responsible for confirming that a state lies in the implemented stable single-phase scope.
The exact CoolProp version and complete input-pair calls for the original sampled curves remain unresolved. The [dataset provenance audit](DataProvenance.md) records that separate curve-data issue.

## Planned expansion

The next increments are:

1. Add a validated refrigerant-mixture backend, beginning with R401A bubble/dew and pressure-temperature states.
2. Locate or develop a qualified pure ethylene-glycol model without extrapolating the aqueous correlations.
3. Add separately qualified pure-fluid transport-property correlations.
4. Add IF97 Region 3 and pressure-enthalpy or pressure-entropy state recovery with explicit phase handling.
5. Add humid-air properties using a separately qualified model.

Other mixtures, user-selectable reference states, and automatic phase-quality resolution remain outside the current scope.

See `Examples/ThermophysicalPropertiesDemo.cpd` for the complete end-user workflow.
