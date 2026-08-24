"""Validate and generate concentration-aware aqueous-glycol equations."""

from __future__ import annotations

from typing import Any, Callable


PROPERTY_MAP = {
    "density": ("THERMO_P_DENSITY", "kg/m^3", "Density"),
    "specific_heat": ("THERMO_P_SPECIFIC_HEAT", "J/(kg*K)", "SpecificHeat"),
    "viscosity": ("THERMO_P_DYNAMIC_VISCOSITY", "Pa*s", "Viscosity"),
    "conductivity": ("THERMO_P_THERMAL_CONDUCTIVITY", "W/(m*K)", "Conductivity"),
}


def validate_glycols(dataset: Any, require: Callable[[bool, str], None]) -> dict[str, Any]:
    require(isinstance(dataset, dict) and dataset.get("schema_version") == 1, "glycol schema_version must equal 1.")
    require(isinstance(dataset.get("upstream"), dict), "glycol upstream metadata is required.")
    require(isinstance(dataset.get("source"), dict), "glycol source metadata is required.")
    for container_name, fields in (("upstream", ("project", "repository", "revision", "license")), ("source", ("name", "citation", "notes"))):
        container = dataset[container_name]
        for field in fields:
            value = container.get(field)
            require(isinstance(value, str) and value.strip() == value and value and "\n" not in value and "\r" not in value, f"glycol {container_name}.{field} must be safe single-line text.")
            require(not any(marker in value for marker in ("'", "#", "$", "<", ">")), f"glycol {container_name}.{field} contains CalcPad control text.")
    families = dataset.get("families")
    require(isinstance(families, list) and len(families) == 2, "glycol dataset must contain exactly two families.")
    ids: set[int] = set()
    constants: set[str] = set()
    for index, family in enumerate(families):
        path = f"glycol families[{index}]"
        require(isinstance(family, dict), f"{path} must be an object.")
        require(isinstance(family.get("id"), int) and family["id"] > 0, f"{path}.id must be positive.")
        require(family["id"] not in ids, "glycol family IDs must be unique.")
        ids.add(family["id"])
        constant = family.get("constant")
        require(isinstance(constant, str) and constant.startswith("GLYCOL_") and constant not in constants, f"{path}.constant is invalid or duplicated.")
        constants.add(constant)
        for field in ("prefix", "name", "description", "reference", "upstream_file", "upstream_sha256"):
            require(isinstance(family.get(field), str) and family[field], f"{path}.{field} is required.")
        for field in ("temperature_min_K", "temperature_max_K", "temperature_base_K", "mass_fraction_min", "mass_fraction_max", "mass_fraction_base"):
            require(isinstance(family.get(field), (int, float)), f"{path}.{field} must be numeric.")
        require(family["temperature_min_K"] < family["temperature_max_K"], f"{path} temperature range is invalid.")
        require(0 <= family["mass_fraction_min"] < family["mass_fraction_max"] <= 1, f"{path} mass-fraction range is invalid.")
        properties = family.get("properties")
        require(isinstance(properties, dict) and set(properties) == set(PROPERTY_MAP), f"{path} must contain the four supported properties.")
        for name, record in properties.items():
            require(isinstance(record, dict), f"{path}.{name} must be an object.")
            expected = "exppolynomial" if name == "viscosity" else "polynomial"
            require(record.get("type") == expected, f"{path}.{name} equation family is unsupported.")
            _validate_matrix(record.get("coeffs"), f"{path}.{name}", require)
        freezing = family.get("freezing_temperature")
        require(isinstance(freezing, dict) and freezing.get("type") == "polynomial", f"{path} freezing equation is unsupported.")
        _validate_matrix(freezing.get("coeffs"), f"{path}.freezing_temperature", require)
    return dataset


def _validate_matrix(value: Any, path: str, require: Callable[[bool, str], None]) -> None:
    require(isinstance(value, list) and value, f"{path}.coeffs must be a non-empty matrix.")
    width = len(value[0]) if isinstance(value[0], list) else 0
    require(width > 0 and all(isinstance(row, list) and len(row) == width for row in value), f"{path}.coeffs must be rectangular.")
    require(all(isinstance(item, (int, float)) for row in value for item in row), f"{path}.coeffs must be numeric.")


def generate_glycols(dataset: dict[str, Any], f: Callable[[Any], str]) -> list[str]:
    families = dataset["families"]
    source = dataset["source"]
    upstream = dataset["upstream"]
    lines = [
        "'<!-- Concentration-aware incompressible aqueous-glycol equations. -->",
        "",
        f"#def GlycolEquationSource$ = {source['name']}",
        f"#def GlycolEquationCitation$ = {source['citation']}",
        f"#def GlycolEquationRevision$ = CoolProp {upstream['revision']}",
        f"#def GlycolEquationLicense$ = {upstream['license']}",
        "",
        "GLYCOL_OK = 0",
        "GLYCOL_ERR_FAMILY = 401",
        "GLYCOL_ERR_PROPERTY = 402",
        "GLYCOL_ERR_CONCENTRATION_LOW = 403",
        "GLYCOL_ERR_CONCENTRATION_HIGH = 404",
        "GLYCOL_ERR_TEMPERATURE_LOW = 405",
        "GLYCOL_ERR_TEMPERATURE_HIGH = 406",
        "GLYCOL_ERR_FROZEN = 407",
    ]
    for family in families:
        lines.append(f"{family['constant']} = {family['id']}")
    lines.extend((f"GlycolFamilyIDs = [{'; '.join(str(item['id']) for item in families)}]", f"GlycolFamilyCount = {len(families)}", "GlycolHasFamily(family) = DBHasID(GlycolFamilyIDs; family)", "GlycolPropertyIDs = [THERMO_P_DENSITY; THERMO_P_SPECIFIC_HEAT; THERMO_P_DYNAMIC_VISCOSITY; THERMO_P_THERMAL_CONDUCTIVITY]", "GlycolHasProperty(property) = DBHasID(GlycolPropertyIDs; property)", "GlycolDatasetOK = and(GlycolFamilyCount ≡ len(GlycolFamilyIDs); GlycolFamilyCount ≡ 2; len(GlycolPropertyIDs) ≡ 4)", ""))
    for family in families:
        prefix = family["prefix"]
        lines.extend((
            f"{prefix}TMinK = {f(family['temperature_min_K'])}",
            f"{prefix}TMaxK = {f(family['temperature_max_K'])}",
            f"{prefix}XMin = {f(family['mass_fraction_min'])}",
            f"{prefix}XMax = {f(family['mass_fraction_max'])}",
            f"{prefix}FreezeK(x) = {_poly(family['freezing_temperature']['coeffs'], '0', 'x', 0.0, family['mass_fraction_base'], f)}",
        ))
        for name, (_, _, suffix) in PROPERTY_MAP.items():
            record = family["properties"][name]
            expression = _poly(record["coeffs"], "T_K", "x", family["temperature_base_K"], family["mass_fraction_base"], f)
            if record["type"] == "exppolynomial":
                expression = f"exp({expression})"
            lines.append(f"{prefix}{suffix}Raw(T_K; x) = {expression}")
        lines.append("")
    for public, suffix in (("GlycolTMinK", "TMinK"), ("GlycolTMaxK", "TMaxK"), ("GlycolXMin", "XMin"), ("GlycolXMax", "XMax")):
        terms = [value for family in families for value in (f"family ≡ {family['constant']}", f"{family['prefix']}{suffix}")]
        lines.append(f"{public}(family) = switch(" + "; ".join(terms + ["0/0"]) + ")")
    freeze_terms = [value for family in families for value in (f"family ≡ {family['constant']}", f"{family['prefix']}FreezeK(x)")]
    lines.append("GlycolFreezeK(family; x) = switch(" + "; ".join(freeze_terms + ["0/0"]) + ")")
    raw_terms: list[str] = []
    for family in families:
        for name, (constant, _, suffix) in PROPERTY_MAP.items():
            raw_terms.extend((f"and(family ≡ {family['constant']}; property ≡ {constant})", f"{family['prefix']}{suffix}Raw(T_K; x)"))
    lines.extend((
        "GlycolRaw(family; property; T_K; x) = switch(" + "; ".join(raw_terms + ["0/0"]) + ")",
        "GlycolApplyUnits(property; value) = switch(property ≡ THERMO_P_DENSITY; setunits(value; kg/m^3); property ≡ THERMO_P_SPECIFIC_HEAT; setunits(value; J/(kg*K)); property ≡ THERMO_P_DYNAMIC_VISCOSITY; setunits(value; Pa*s); property ≡ THERMO_P_THERMAL_CONDUCTIVITY; setunits(value; W/(m*K)); 0/0)",
        "GlycolUndefined(property) = switch(property ≡ THERMO_P_DENSITY; setunits(0/0; kg/m^3); property ≡ THERMO_P_SPECIFIC_HEAT; setunits(0/0; J/(kg*K)); property ≡ THERMO_P_DYNAMIC_VISCOSITY; setunits(0/0; Pa*s); property ≡ THERMO_P_THERMAL_CONDUCTIVITY; setunits(0/0; W/(m*K)); 0/0)",
        "GlycolPROPStatus(family; property; temperature; glycol_mass_fraction) = $block{T_K = temperature/°C + 273.15; switch(not(GlycolHasFamily(family)); GLYCOL_ERR_FAMILY; not(GlycolHasProperty(property)); GLYCOL_ERR_PROPERTY; glycol_mass_fraction < GlycolXMin(family); GLYCOL_ERR_CONCENTRATION_LOW; glycol_mass_fraction > GlycolXMax(family); GLYCOL_ERR_CONCENTRATION_HIGH; T_K < GlycolTMinK(family); GLYCOL_ERR_TEMPERATURE_LOW; T_K > GlycolTMaxK(family); GLYCOL_ERR_TEMPERATURE_HIGH; T_K < GlycolFreezeK(family; glycol_mass_fraction); GLYCOL_ERR_FROZEN; GLYCOL_OK);}",
        "GlycolPROP(family; property; temperature; glycol_mass_fraction) = $block{status = GlycolPROPStatus(family; property; temperature; glycol_mass_fraction); raw = if(status ≡ GLYCOL_OK; GlycolRaw(family; property; temperature/°C + 273.15; glycol_mass_fraction); 0/0); if(status ≡ GLYCOL_OK; GlycolApplyUnits(property; raw); GlycolUndefined(property));}",
        "EgWaterDensityTX(temperature; glycol_mass_fraction) = GlycolPROP(GLYCOL_ETHYLENE; THERMO_P_DENSITY; temperature; glycol_mass_fraction)",
        "EgWaterSpecificHeatTX(temperature; glycol_mass_fraction) = GlycolPROP(GLYCOL_ETHYLENE; THERMO_P_SPECIFIC_HEAT; temperature; glycol_mass_fraction)",
        "EgWaterDynamicViscosityTX(temperature; glycol_mass_fraction) = GlycolPROP(GLYCOL_ETHYLENE; THERMO_P_DYNAMIC_VISCOSITY; temperature; glycol_mass_fraction)",
        "EgWaterThermalConductivityTX(temperature; glycol_mass_fraction) = GlycolPROP(GLYCOL_ETHYLENE; THERMO_P_THERMAL_CONDUCTIVITY; temperature; glycol_mass_fraction)",
        "PgWaterDensityTX(temperature; glycol_mass_fraction) = GlycolPROP(GLYCOL_PROPYLENE; THERMO_P_DENSITY; temperature; glycol_mass_fraction)",
        "PgWaterSpecificHeatTX(temperature; glycol_mass_fraction) = GlycolPROP(GLYCOL_PROPYLENE; THERMO_P_SPECIFIC_HEAT; temperature; glycol_mass_fraction)",
        "PgWaterDynamicViscosityTX(temperature; glycol_mass_fraction) = GlycolPROP(GLYCOL_PROPYLENE; THERMO_P_DYNAMIC_VISCOSITY; temperature; glycol_mass_fraction)",
        "PgWaterThermalConductivityTX(temperature; glycol_mass_fraction) = GlycolPROP(GLYCOL_PROPYLENE; THERMO_P_THERMAL_CONDUCTIVITY; temperature; glycol_mass_fraction)",
        "",
        "#def GlycolStatus$(status$)",
        "    #if status$ ≡ GLYCOL_OK",
        "        '<span class=\"ok\">Valid aqueous-glycol state</span>",
        "    #end if",
        "    #if status$ ≡ GLYCOL_ERR_FAMILY",
        "        '<span class=\"err\">Unknown glycol family ID</span>",
        "    #end if",
        "    #if status$ ≡ GLYCOL_ERR_PROPERTY",
        "        '<span class=\"err\">Property is unsupported by the glycol backend</span>",
        "    #end if",
        "    #if or(status$ ≡ GLYCOL_ERR_CONCENTRATION_LOW; status$ ≡ GLYCOL_ERR_CONCENTRATION_HIGH)",
        "        '<span class=\"err\">Glycol mass fraction is outside the validated range</span>",
        "    #end if",
        "    #if or(status$ ≡ GLYCOL_ERR_TEMPERATURE_LOW; status$ ≡ GLYCOL_ERR_TEMPERATURE_HIGH)",
        "        '<span class=\"err\">Temperature is outside the equation range</span>",
        "    #end if",
        "    #if status$ ≡ GLYCOL_ERR_FROZEN",
        "        '<span class=\"err\">State is below the correlated freezing temperature</span>",
        "    #end if",
        "#end def",
        "",
    ))
    return lines


def _poly(coefficients: list[list[float]], T: str, x: str, Tbase: float, xbase: float, f: Callable[[Any], str]) -> str:
    terms: list[str] = []
    for i, row in enumerate(coefficients):
        for j, coefficient in enumerate(row):
            if float(coefficient) == 0:
                continue
            factors = [f(coefficient)]
            if i:
                factors.append(f"({T} - {f(Tbase)})^{i}")
            if j:
                factors.append(f"({x} - {f(xbase)})^{j}")
            terms.append("*".join(factors))
    return " + ".join(terms) if terms else "0"
