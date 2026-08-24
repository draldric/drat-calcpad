# Thermophysical Properties

`Libraries/Thermophysical/ThermophysicalProperties.cpd` is the generated, self-contained DRAT property library for thermal and fluid calculations.
It does not require CoolProp or another property engine at worksheet runtime.

Release `0.3.0` provides two complementary backends and one unified state-query interface:

- Water specific heat, saturation pressure, and latent heat of vaporization.
- Density, specific heat, dynamic viscosity, and thermal conductivity for 50% ethylene glycol by mass (`INCOMP::MEG-50%`).
- Linear interpolation from 10 °C through 95 °C.
- IAPWS-IF97 fundamental equations for stable single-phase water and steam in Regions 1 and 2.
- IAPWS-IF97 Region 4 forward and inverse saturation equations plus the B23 boundary used for region selection.
- A CoolProp-shaped `ThermoProps` selector over the implemented equation backends.

These curves reproduce the values embedded in the migrated tank-heating calculation.
They were sampled from CoolProp through SMath plugin build `6.4.8214.13502`.
The saved worksheet did not preserve every original CoolProp input-pair call, so this revision is a traceable migration baseline rather than independent verification of the thermodynamic basis.

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

The two inputs can be supplied in either order. Version `0.3.0` supports only the pressure-temperature pair and the `THERMO_WATER` equation backend. Unsupported fluids, outputs, inputs, repeated inputs, and unavailable IF97 regions return explicit statuses. `ThermoPropsStatus$(status)` renders the complete unified or underlying IF97 status.

Input IDs are `THERMO_IN_PRESSURE` and `THERMO_IN_TEMPERATURE`. Output IDs are `THERMO_OUT_SPECIFIC_VOLUME`, `THERMO_OUT_DENSITY`, `THERMO_OUT_ENTHALPY`, `THERMO_OUT_INTERNAL_ENERGY`, `THERMO_OUT_ENTROPY`, `THERMO_OUT_CP`, `THERMO_OUT_CV`, and `THERMO_OUT_SOUND_SPEED`.

Unlike CoolProp's `PropsSI`, values are passed and returned with CalcPad units instead of unitless SI numbers. The ID-based interface also avoids fragile string comparisons in generated worksheets. Its call shape is reserved for future pressure-enthalpy, pressure-entropy, and quality input pairs.

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

The maintained source is `Data/Sources/Thermophysical/ThermophysicalProperties.json`.
Schema version 2 stores both curve records and the fixed-shape IF97 coefficient arrays.
The committed `.cpd` library is generated:

```powershell
python Tools/GenerateThermophysicalLibrary.py `
    Data/Sources/Thermophysical/ThermophysicalProperties.json `
    Libraries/Thermophysical/ThermophysicalProperties.cpd
```

Check that the generated file is current without rewriting it:

```powershell
python Tools/GenerateThermophysicalLibrary.py `
    Data/Sources/Thermophysical/ThermophysicalProperties.json `
    Libraries/Thermophysical/ThermophysicalProperties.cpd `
    --check
```

The generator uses only the Python standard library.
It rejects unknown units, duplicate IDs or curve keys, duplicate public functions, non-finite values, unequal axes, non-increasing temperatures, and incomplete IF97 coefficient series before atomically replacing the generated library.

## Qualification

`Tests/Libraries/Thermophysical/ThermophysicalPropertiesTest.cpd` verifies the sampled curves and every Region 1, Region 2, B23 boundary, saturation-pressure, and saturation-temperature computer-program verification point published in IAPWS R7-97(2012) Tables 1, 5, 15, 35, and 36.
It also checks region selection, unsupported Region 3 states, saturation-line rejection, units, dimensioned undefined results, and derived density and isochoric heat capacity.
`Tests/Tooling/ThermophysicalGeneratorTest.py` verifies the raw-data schema and stale-output detection.

The curve backend should eventually be checked against independent governing sources, not only the engine used to generate it.
The IF97 backend is transcribed and regression-checked directly against the official IAPWS release, but worksheet authors remain responsible for confirming that a state lies in the implemented stable single-phase scope.
The exact CoolProp version and complete input-pair calls for the original sampled curves remain unresolved. The [dataset provenance audit](DataProvenance.md) records that separate curve-data issue.

## Planned expansion

The next increments are:

1. Add IF97 Region 3 so the pressure-temperature map is continuous through the dense-fluid and supercritical domain.
2. Add pressure-enthalpy and pressure-entropy state recovery with explicit phase handling.
3. Add audited two-dimensional `temperature-concentration` interpolation and ethylene/propylene glycol concentration families.
4. Add humid-air properties using a separately qualified model.
5. Add other fluids only in response to maintained engineering use cases.

Arbitrary refrigerants, mixtures, reference states, and general Helmholtz equations of state remain outside the initial scope.

See `Examples/ThermophysicalPropertiesDemo.cpd` for the complete end-user workflow.
