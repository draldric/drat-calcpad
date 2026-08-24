"""Validate IAPWS-IF97 source records and emit CalcPad Region 1/2 equations."""

from __future__ import annotations

from typing import Any, Callable


IF97_PROPERTY_UNITS = {
    "m3_per_kg": "m^3/kg",
    "kg_per_m3": "kg/m^3",
    "kJ_per_kg": "kJ/kg",
    "kJ_per_kgK": "kJ/(kg*K)",
    "m_per_s": "m/s",
}


def validate_if97(
    value: Any,
    source_ids: list[int],
    require: Callable[[bool, str], None],
    require_mapping: Callable[[Any, str], dict[str, Any]],
    require_list: Callable[[Any, str], list[Any]],
    require_integer: Callable[..., int],
    require_text: Callable[[Any, str], str],
    require_constant: Callable[[Any, str], str],
    require_number: Callable[[Any, str], float],
    validate_unique: Callable[[list[Any], str], None],
) -> dict[str, Any]:
    """Validate the fixed-shape IF97 records used by the generated equation backend."""

    root = require_mapping(value, "if97")
    require(require_integer(root.get("source_id"), "if97.source_id") in source_ids, "if97.source_id is unknown.")
    require_text(root.get("revision"), "if97.revision")
    for field in (
        "gas_constant_kJ_per_kgK",
        "critical_temperature_K",
        "critical_pressure_MPa",
        "minimum_temperature_K",
        "maximum_region2_temperature_K",
        "maximum_pressure_MPa",
    ):
        require_number(root.get(field), f"if97.{field}")

    properties = require_list(root.get("properties"), "if97.properties")
    require(properties, "if97.properties must not be empty.")
    property_ids: list[int] = []
    property_constants: list[str] = []
    for index, item in enumerate(properties):
        prop = require_mapping(item, f"if97.properties[{index}]")
        property_ids.append(require_integer(prop.get("id"), f"if97.properties[{index}].id"))
        property_constants.append(require_constant(prop.get("constant"), f"if97.properties[{index}].constant"))
        require_text(prop.get("name"), f"if97.properties[{index}].name")
        unit_key = require_text(prop.get("unit_key"), f"if97.properties[{index}].unit_key")
        require(unit_key in IF97_PROPERTY_UNITS, f"if97.properties[{index}].unit_key is unsupported.")
    validate_unique(property_ids, "IF97 property IDs")
    validate_unique(property_constants, "IF97 property constants")

    regions = require_mapping(root.get("regions"), "if97.regions")
    region1 = require_mapping(regions.get("region1"), "if97.regions.region1")
    region2 = require_mapping(regions.get("region2"), "if97.regions.region2")
    saturation = require_mapping(root.get("saturation"), "if97.saturation")
    boundary = require_mapping(root.get("boundary23"), "if97.boundary23")

    _validate_series(region1, "if97.regions.region1", 34, require, require_list, require_number)
    ideal = require_mapping(region2.get("ideal"), "if97.regions.region2.ideal")
    residual = require_mapping(region2.get("residual"), "if97.regions.region2.residual")
    _validate_series(ideal, "if97.regions.region2.ideal", 9, require, require_list, require_number, has_i=False)
    _validate_series(residual, "if97.regions.region2.residual", 43, require, require_list, require_number)

    for path, record, count in (
        ("if97.saturation", saturation, 10),
        ("if97.boundary23", boundary, 3),
    ):
        coefficients = require_list(record.get("n"), f"{path}.n")
        require(len(coefficients) == count, f"{path}.n must contain exactly {count} values.")
        for index, coefficient in enumerate(coefficients):
            require_number(coefficient, f"{path}.n[{index}]")
    return root


def _validate_series(
    record: dict[str, Any],
    path: str,
    count: int,
    require: Callable[[bool, str], None],
    require_list: Callable[[Any, str], list[Any]],
    require_number: Callable[[Any, str], float],
    has_i: bool = True,
) -> None:
    """Validate parallel exponent and coefficient arrays."""

    fields = ("i", "j", "n") if has_i else ("j", "n")
    for field in fields:
        values = require_list(record.get(field), f"{path}.{field}")
        require(len(values) == count, f"{path}.{field} must contain exactly {count} values.")
        for index, value in enumerate(values):
            require_number(value, f"{path}.{field}[{index}]")


def generate_if97(dataset: dict[str, Any], format_number: Callable[[Any], str]) -> list[str]:
    """Render the complete unit-aware IF97 Region 1/2 public API."""

    data = dataset["if97"]
    region1 = data["regions"]["region1"]
    ideal = data["regions"]["region2"]["ideal"]
    residual = data["regions"]["region2"]["residual"]
    sat = data["saturation"]["n"]
    b23 = data["boundary23"]["n"]

    r1_terms = list(zip(region1["i"], region1["j"], region1["n"]))
    r2_ideal_terms = [(0, j, n) for j, n in zip(ideal["j"], ideal["n"])]
    r2_residual_terms = list(zip(residual["i"], residual["j"], residual["n"]))

    properties = data["properties"]
    property_constants = {item["name"]: item["constant"] for item in properties}
    unit_terms: list[str] = []
    undefined_terms: list[str] = []
    for prop in properties:
        unit = IF97_PROPERTY_UNITS[prop["unit_key"]]
        unit_terms.extend((f"property ≡ {prop['constant']}", f"setunits(value; {unit})"))
        undefined_terms.extend((f"property ≡ {prop['constant']}", f"setunits(0/0; {unit})"))

    n = [None] + [format_number(value) for value in sat]
    b = [None] + [format_number(value) for value in b23]
    r = format_number(data["gas_constant_kJ_per_kgK"])
    t_min = format_number(data["minimum_temperature_K"])
    t_max = format_number(data["maximum_region2_temperature_K"])
    t_critical = format_number(data["critical_temperature_K"])
    p_critical = format_number(data["critical_pressure_MPa"])
    p_max = format_number(data["maximum_pressure_MPa"])

    lines = [
        "'<!-- IAPWS-IF97 Region 1 and Region 2 equation backend. -->",
        "",
        "IF97_OK = 0",
        "IF97_ERR_PROPERTY = 101",
        "IF97_ERR_PRESSURE_LOW = 102",
        "IF97_ERR_PRESSURE_HIGH = 103",
        "IF97_ERR_TEMPERATURE_LOW = 104",
        "IF97_ERR_TEMPERATURE_HIGH = 105",
        "IF97_ERR_TWO_PHASE = 106",
        "IF97_ERR_UNSUPPORTED_REGION = 107",
        "IF97_REGION_UNSUPPORTED = 0",
        "IF97_REGION_1 = 1",
        "IF97_REGION_2 = 2",
        f"IF97_R = {r}",
        f"IF97_T_MIN = {t_min}K",
        "IF97_T_R1_MAX = 623.15K",
        "IF97_T_B23_MAX = 863.15K",
        f"IF97_T_R2_MAX = {t_max}K",
        f"IF97_T_CRITICAL = {t_critical}K",
        f"IF97_P_CRITICAL = {p_critical}MPa",
        f"IF97_P_MAX = {p_max}MPa",
        f"IF97_SOURCE_ID = {data['source_id']}",
        "",
    ]
    for prop in properties:
        lines.append(f"{prop['constant']} = {prop['id']}")
    lines.extend(
        (
            "",
            "If97PropertyIDs = [" + "; ".join(str(item["id"]) for item in properties) + "]",
            f"If97PropertyCount = {len(properties)}",
            "If97ImplementedRegionCount = 2",
            "If97HasProperty(property) = DBHasID(If97PropertyIDs; property)",
            "If97DatasetOK = and(If97PropertyCount ≡ len(If97PropertyIDs); If97ImplementedRegionCount ≡ 2; IF97_SOURCE_ID ≡ THERMO_SRC_IAPWS_IF97)",
            "If97ApplyUnits(property; value) = switch(" + "; ".join(unit_terms + ["0/0"]) + ")",
            "If97Undefined(property) = switch(" + "; ".join(undefined_terms + ["0/0"]) + ")",
            "",
            f"If97SaturationPressureTRaw(T_K) = $block{{theta = T_K + {n[9]}/(T_K - {n[10]}); A = theta^2 + {n[1]}*theta + {n[2]}; B = {n[3]}*theta^2 + {n[4]}*theta + {n[5]}; C = {n[6]}*theta^2 + {n[7]}*theta + {n[8]}; (2*C/(-B + sqrt(B^2 - 4*A*C)))^4;}}",
            f"If97SaturationTemperaturePRaw(p_MPa) = $block{{beta = p_MPa^0.25; E = beta^2 + {n[3]}*beta + {n[6]}; F = {n[1]}*beta^2 + {n[4]}*beta + {n[7]}; G = {n[2]}*beta^2 + {n[5]}*beta + {n[8]}; D = 2*G/(-F - sqrt(F^2 - 4*E*G)); ({n[10]} + D - sqrt(({n[10]} + D)^2 - 4*({n[9]} + {n[10]}*D)))/2;}}",
            "If97SaturationPressureTStatus(temperature) = switch(temperature < IF97_T_MIN; IF97_ERR_TEMPERATURE_LOW; temperature > IF97_T_CRITICAL; IF97_ERR_TEMPERATURE_HIGH; IF97_OK)",
            "If97SaturationTemperaturePStatus(pressure) = switch(pressure < 0.000611213MPa; IF97_ERR_PRESSURE_LOW; pressure > IF97_P_CRITICAL; IF97_ERR_PRESSURE_HIGH; IF97_OK)",
            "If97SaturationPressureT(temperature) = if(If97SaturationPressureTStatus(temperature) ≡ IF97_OK; If97SaturationPressureTRaw(temperature/K)*MPa; setunits(0/0; MPa))",
            "If97SaturationTemperatureP(pressure) = if(If97SaturationTemperaturePStatus(pressure) ≡ IF97_OK; If97SaturationTemperaturePRaw(pressure/MPa)*K; setunits(0/0; K))",
            "",
            f"If97Boundary23PressureT(temperature) = ({b[1]} + {b[2]}*(temperature/K) + {b[3]}*(temperature/K)^2)*MPa",
            "If97RegionPTStatus(pressure; temperature) = $block{p_positive = pressure > 0MPa; p_in_range = pressure ≤ IF97_P_MAX; T_in_low = temperature ≥ IF97_T_MIN; T_in_high = temperature ≤ IF97_T_R2_MAX; p_sat = if(and(T_in_low; temperature ≤ IF97_T_R1_MAX); If97SaturationPressureT(temperature); 0MPa); on_saturation = if(and(T_in_low; temperature ≤ IF97_T_R1_MAX); pressure ≡ p_sat; 0); in_region3 = if(and(temperature > IF97_T_R1_MAX; temperature ≤ IF97_T_B23_MAX; p_positive; p_in_range); pressure > If97Boundary23PressureT(temperature); 0); switch(not(p_positive); IF97_ERR_PRESSURE_LOW; not(p_in_range); IF97_ERR_PRESSURE_HIGH; not(T_in_low); IF97_ERR_TEMPERATURE_LOW; not(T_in_high); IF97_ERR_TEMPERATURE_HIGH; on_saturation; IF97_ERR_TWO_PHASE; in_region3; IF97_ERR_UNSUPPORTED_REGION; IF97_OK);}",
            "If97RegionPT(pressure; temperature) = if(If97RegionPTStatus(pressure; temperature) ≠ IF97_OK; IF97_REGION_UNSUPPORTED; switch(temperature ≤ IF97_T_R1_MAX; if(pressure > If97SaturationPressureT(temperature); IF97_REGION_1; IF97_REGION_2); IF97_REGION_2))",
            "",
        )
    )

    lines.extend(_gamma_functions("If97R1", r1_terms, "7.1 - pi", "tau - 1.222", format_number, first_sign=-1))
    lines.extend(_ideal_gamma_functions(r2_ideal_terms, format_number))
    lines.extend(_gamma_functions("If97R2Residual", r2_residual_terms, "pi", "tau - 0.5", format_number, first_sign=1))

    lines.extend(
        (
            "If97R1PropertyRaw(property; p_MPa; T_K) = $block{pi = p_MPa/16.53; tau = 1386/T_K; g = If97R1Gamma(pi; tau); gp = If97R1GammaPi(pi; tau); gpp = If97R1GammaPiPi(pi; tau); gt = If97R1GammaTau(pi; tau); gtt = If97R1GammaTauTau(pi; tau); gpt = If97R1GammaPiTau(pi; tau); v = pi*gp*IF97_R*T_K/p_MPa/1000; h = tau*gt*IF97_R*T_K; u = (tau*gt - pi*gp)*IF97_R*T_K; s = (tau*gt - g)*IF97_R; cp = -tau^2*gtt*IF97_R; cv = (-tau^2*gtt + (gp - tau*gpt)^2/gpp)*IF97_R; w = sqrt(1000*IF97_R*T_K*gp^2/((gp - tau*gpt)^2/(tau^2*gtt) - gpp)); switch(property ≡ " + property_constants["Specific volume"] + "; v; property ≡ " + property_constants["Density"] + "; 1/v; property ≡ " + property_constants["Specific enthalpy"] + "; h; property ≡ " + property_constants["Specific internal energy"] + "; u; property ≡ " + property_constants["Specific entropy"] + "; s; property ≡ " + property_constants["Specific isobaric heat capacity"] + "; cp; property ≡ " + property_constants["Specific isochoric heat capacity"] + "; cv; property ≡ " + property_constants["Speed of sound"] + "; w; 0/0);}",
            "If97R2PropertyRaw(property; p_MPa; T_K) = $block{pi = p_MPa; tau = 540/T_K; g0 = If97R2IdealGamma(pi; tau); g0t = If97R2IdealGammaTau(pi; tau); g0tt = If97R2IdealGammaTauTau(pi; tau); gr = If97R2ResidualGamma(pi; tau); grp = If97R2ResidualGammaPi(pi; tau); grpp = If97R2ResidualGammaPiPi(pi; tau); grt = If97R2ResidualGammaTau(pi; tau); grtt = If97R2ResidualGammaTauTau(pi; tau); grpt = If97R2ResidualGammaPiTau(pi; tau); v = pi*(1/pi + grp)*IF97_R*T_K/p_MPa/1000; h = tau*(g0t + grt)*IF97_R*T_K; u = (tau*(g0t + grt) - pi*(1/pi + grp))*IF97_R*T_K; s = (tau*(g0t + grt) - (g0 + gr))*IF97_R; cp = -tau^2*(g0tt + grtt)*IF97_R; cv = (-tau^2*(g0tt + grtt) - (1 + pi*grp - tau*pi*grpt)^2/(1 - pi^2*grpp))*IF97_R; w = sqrt(1000*IF97_R*T_K*(1 + 2*pi*grp + pi^2*grp^2)/((1 - pi^2*grpp) + (1 + pi*grp - tau*pi*grpt)^2/(tau^2*(g0tt + grtt)))); switch(property ≡ " + property_constants["Specific volume"] + "; v; property ≡ " + property_constants["Density"] + "; 1/v; property ≡ " + property_constants["Specific enthalpy"] + "; h; property ≡ " + property_constants["Specific internal energy"] + "; u; property ≡ " + property_constants["Specific entropy"] + "; s; property ≡ " + property_constants["Specific isobaric heat capacity"] + "; cp; property ≡ " + property_constants["Specific isochoric heat capacity"] + "; cv; property ≡ " + property_constants["Speed of sound"] + "; w; 0/0);}",
            "",
            "If97PROPPTStatus(property; pressure; temperature) = switch(not(If97HasProperty(property)); IF97_ERR_PROPERTY; If97RegionPTStatus(pressure; temperature))",
            "If97PROPPT(property; pressure; temperature) = $block{status = If97PROPPTStatus(property; pressure; temperature); region = if(status ≡ IF97_OK; If97RegionPT(pressure; temperature); IF97_REGION_UNSUPPORTED); raw = switch(region ≡ IF97_REGION_1; If97R1PropertyRaw(property; pressure/MPa; temperature/K); region ≡ IF97_REGION_2; If97R2PropertyRaw(property; pressure/MPa; temperature/K); 0/0); if(status ≡ IF97_OK; If97ApplyUnits(property; raw); If97Undefined(property));}",
            "If97SpecificVolumePT(pressure; temperature) = If97PROPPT(IF97_P_SPECIFIC_VOLUME; pressure; temperature)",
            "If97DensityPT(pressure; temperature) = If97PROPPT(IF97_P_DENSITY; pressure; temperature)",
            "If97EnthalpyPT(pressure; temperature) = If97PROPPT(IF97_P_ENTHALPY; pressure; temperature)",
            "If97InternalEnergyPT(pressure; temperature) = If97PROPPT(IF97_P_INTERNAL_ENERGY; pressure; temperature)",
            "If97EntropyPT(pressure; temperature) = If97PROPPT(IF97_P_ENTROPY; pressure; temperature)",
            "If97CpPT(pressure; temperature) = If97PROPPT(IF97_P_CP; pressure; temperature)",
            "If97CvPT(pressure; temperature) = If97PROPPT(IF97_P_CV; pressure; temperature)",
            "If97SoundSpeedPT(pressure; temperature) = If97PROPPT(IF97_P_SOUND_SPEED; pressure; temperature)",
            "",
            "#def If97Status$(status$)",
            "    #if status$ ≡ IF97_OK",
            "        '<span class=\"ok\">Valid IF97 Region 1 or Region 2 state</span>",
            "    #end if",
            "    #if status$ ≡ IF97_ERR_PROPERTY",
            "        '<span class=\"err\">Unknown IF97 property ID</span>",
            "    #end if",
            "    #if status$ ≡ IF97_ERR_PRESSURE_LOW",
            "        '<span class=\"err\">Pressure is below the supported IF97 range</span>",
            "    #end if",
            "    #if status$ ≡ IF97_ERR_PRESSURE_HIGH",
            "        '<span class=\"err\">Pressure is above the supported IF97 range</span>",
            "    #end if",
            "    #if status$ ≡ IF97_ERR_TEMPERATURE_LOW",
            "        '<span class=\"err\">Temperature is below the supported IF97 range</span>",
            "    #end if",
            "    #if status$ ≡ IF97_ERR_TEMPERATURE_HIGH",
            "        '<span class=\"err\">Temperature is above the supported Region 1 and Region 2 range</span>",
            "    #end if",
            "    #if status$ ≡ IF97_ERR_TWO_PHASE",
            "        '<span class=\"err\">State lies on the saturation boundary and requires a phase quality</span>",
            "    #end if",
            "    #if status$ ≡ IF97_ERR_UNSUPPORTED_REGION",
            "        '<span class=\"err\">State lies in an IF97 region that is not implemented</span>",
            "    #end if",
            "#end def",
            "",
        )
    )
    return lines


def _gamma_functions(
    prefix: str,
    terms: list[tuple[Any, Any, Any]],
    x: str,
    y: str,
    format_number: Callable[[Any], str],
    first_sign: int,
) -> list[str]:
    """Generate a Gibbs series and its five needed analytical derivatives."""

    specs = (
        ("Gamma", 0, 0),
        ("GammaPi", 1, 0),
        ("GammaPiPi", 2, 0),
        ("GammaTau", 0, 1),
        ("GammaTauTau", 0, 2),
        ("GammaPiTau", 1, 1),
    )
    lines: list[str] = []
    for suffix, di, dj in specs:
        rendered: list[str] = []
        for i_value, j_value, n_value in terms:
            i = int(i_value)
            j = int(j_value)
            multiplier = float(n_value)
            if di:
                for decrement in range(di):
                    multiplier *= i - decrement
            if dj:
                for decrement in range(dj):
                    multiplier *= j - decrement
            if multiplier == 0:
                continue
            if di % 2 == 1:
                multiplier *= first_sign
            rendered.append(_term(multiplier, x, i - di, y, j - dj, format_number))
        lines.append(f"{prefix}{suffix}(pi; tau) = " + " + ".join(rendered))
    lines.append("")
    return lines


def _ideal_gamma_functions(terms: list[tuple[Any, Any, Any]], format_number: Callable[[Any], str]) -> list[str]:
    """Generate the Region 2 ideal-gas Gibbs series and temperature derivatives."""

    gamma = ["ln(pi)"]
    tau = []
    tau_tau = []
    for _, j_value, n_value in terms:
        j = int(j_value)
        n = float(n_value)
        gamma.append(_term(n, "tau", j, None, 0, format_number))
        if j != 0:
            tau.append(_term(n * j, "tau", j - 1, None, 0, format_number))
        if j * (j - 1) != 0:
            tau_tau.append(_term(n * j * (j - 1), "tau", j - 2, None, 0, format_number))
    return [
        "If97R2IdealGamma(pi; tau) = " + " + ".join(gamma),
        "If97R2IdealGammaTau(pi; tau) = " + " + ".join(tau),
        "If97R2IdealGammaTauTau(pi; tau) = " + " + ".join(tau_tau),
        "",
    ]


def _term(
    coefficient: float,
    x: str,
    x_power: int,
    y: str | None,
    y_power: int,
    format_number: Callable[[Any], str],
) -> str:
    """Render a single polynomial term while omitting neutral factors."""

    factors = [format_number(coefficient)]
    if x_power != 0:
        factors.append(f"({x})^{x_power}")
    if y is not None and y_power != 0:
        factors.append(f"({y})^{y_power}")
    return "*".join(factors)
