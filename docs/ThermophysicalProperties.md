# Thermophysical Properties

`Libraries/Thermophysical/ThermophysicalProperties.cpd` is the generated, self-contained DRAT property library for thermal and fluid calculations.
It does not require CoolProp at worksheet runtime.

The initial `0.1.0` dataset is deliberately narrow:

- Water specific heat, saturation pressure, and latent heat of vaporization.
- Density, specific heat, dynamic viscosity, and thermal conductivity for 50% ethylene glycol by mass (`INCOMP::MEG-50%`).
- Linear interpolation from 10 °C through 95 °C.

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

The maintained source is `Libraries/Thermophysical/Data/ThermophysicalProperties.json`.
The committed `.cpd` library is generated:

```powershell
python Tools/GenerateThermophysicalLibrary.py `
    Libraries/Thermophysical/Data/ThermophysicalProperties.json `
    Libraries/Thermophysical/ThermophysicalProperties.cpd
```

Check that the generated file is current without rewriting it:

```powershell
python Tools/GenerateThermophysicalLibrary.py `
    Libraries/Thermophysical/Data/ThermophysicalProperties.json `
    Libraries/Thermophysical/ThermophysicalProperties.cpd `
    --check
```

The generator uses only the Python standard library.
It rejects unknown units, duplicate IDs or curve keys, duplicate public functions, non-finite values, unequal axes, and non-increasing temperatures before emitting CalcPad source.

## Qualification

`Tests/Libraries/Thermophysical/ThermophysicalPropertiesTest.cpd` verifies the exact sampled values, midpoint interpolation, units, aliases, range policies, missing properties, provenance, dimensioned undefined results, and rendered records.
`Tests/Tooling/ThermophysicalGeneratorTest.py` verifies the raw-data schema and stale-output detection.

The dataset should eventually be checked against independent governing sources, not only the engine used to generate it.
Water and steam should be qualified against IAPWS values before the library claims an IAPWS or design-grade classification.

## Planned expansion

The next increments are:

1. Add audited two-dimensional `temperature-concentration` interpolation and ethylene/propylene glycol concentration families.
2. Add an IAPWS-IF97 water/steam backend with phase and saturation-region handling.
3. Add inverse queries such as saturation temperature from pressure and later pressure-enthalpy state recovery.
4. Add humid-air properties using a separately qualified model.
5. Add other fluids only in response to maintained engineering use cases.

Arbitrary refrigerants, mixtures, reference states, and general Helmholtz equations of state remain outside the initial scope.

See `Examples/ThermophysicalPropertiesDemo.cpd` for the complete end-user workflow.
