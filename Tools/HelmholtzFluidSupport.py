"""Validate curated Helmholtz-fluid records and emit CalcPad equation functions."""

from __future__ import annotations

from typing import Any, Callable


IDEAL_TYPES = {
    "IdealGasHelmholtzLead",
    "IdealGasHelmholtzLogTau",
    "IdealGasHelmholtzPower",
    "IdealGasHelmholtzPlanckEinstein",
    "IdealGasHelmholtzPlanckEinsteinFunctionT",
    "IdealGasHelmholtzEnthalpyEntropyOffset",
    "IdealGasHelmholtzCP0Constant",
    "IdealGasHelmholtzCP0PolyT",
}
RESIDUAL_TYPES = {"ResidualHelmholtzPower", "ResidualHelmholtzGaussian", "ResidualHelmholtzNonAnalytic", "ResidualHelmholtzExponential", "ResidualHelmholtzGaoB"}


def validate_helmholtz(
    dataset: Any,
    require: Callable[[bool, str], None],
    require_mapping: Callable[[Any, str], dict[str, Any]],
    require_list: Callable[[Any, str], list[Any]],
    require_integer: Callable[..., int],
    require_text: Callable[[Any, str], str],
    require_constant: Callable[[Any, str], str],
    require_number: Callable[[Any, str], float],
    validate_unique: Callable[[list[Any], str], None],
) -> dict[str, Any]:
    """Validate the fixed curated subset used by the generated backend."""

    root = require_mapping(dataset, "helmholtz root")
    require(root.get("schema_version") == 1, "helmholtz schema_version must equal 1.")
    upstream = require_mapping(root.get("upstream"), "helmholtz upstream")
    for field in ("project", "repository", "revision", "license"):
        require_text(upstream.get(field), f"helmholtz upstream.{field}")
    require(len(upstream["revision"]) == 40 and all(character in "0123456789abcdef" for character in upstream["revision"].lower()), "helmholtz upstream.revision must be a full Git commit.")

    sources = require_list(root.get("sources"), "helmholtz sources")
    fluids = require_list(root.get("fluids"), "helmholtz fluids")
    require(sources and fluids, "helmholtz sources and fluids must not be empty.")
    source_ids: list[int] = []
    source_constants: list[str] = []
    for index, item in enumerate(sources):
        source = require_mapping(item, f"helmholtz sources[{index}]")
        source_ids.append(require_integer(source.get("id"), f"helmholtz sources[{index}].id"))
        source_constants.append(require_constant(source.get("constant"), f"helmholtz sources[{index}].constant"))
        for field in ("name", "citation", "revision", "license", "notes"):
            require_text(source.get(field), f"helmholtz sources[{index}].{field}")
    validate_unique(source_ids, "helmholtz source IDs")
    validate_unique(source_constants, "helmholtz source constants")

    fluid_ids: list[int] = []
    fluid_constants: list[str] = []
    prefixes: list[str] = []
    for index, item in enumerate(fluids):
        path = f"helmholtz fluids[{index}]"
        fluid = require_mapping(item, path)
        fluid_ids.append(require_integer(fluid.get("id"), f"{path}.id"))
        fluid_constants.append(require_constant(fluid.get("constant"), f"{path}.constant"))
        prefix = require_text(fluid.get("function_prefix"), f"{path}.function_prefix")
        require(prefix.startswith("Helmholtz") and prefix.isalnum(), f"{path}.function_prefix must be an alphanumeric Helmholtz prefix.")
        prefixes.append(prefix)
        for field in ("name", "description", "cas", "upstream_file", "upstream_sha256"):
            require_text(fluid.get(field), f"{path}.{field}")
        require(len(fluid["upstream_sha256"]) == 64 and all(character in "0123456789abcdef" for character in fluid["upstream_sha256"].lower()), f"{path}.upstream_sha256 must be a SHA-256 digest.")
        require_integer(fluid.get("source_id"), f"{path}.source_id")
        require(fluid["source_id"] in source_ids, f"{path}.source_id is unknown.")
        for field in (
            "molar_mass_kg_per_mol",
            "gas_constant_J_per_molK",
            "temperature_min_K",
            "temperature_max_K",
            "pressure_max_Pa",
            "reducing_temperature_K",
            "reducing_molar_density_mol_per_m3",
        ):
            require_number(fluid.get(field), f"{path}.{field}")
            require(fluid[field] > 0, f"{path}.{field} must be positive.")
        require(fluid["temperature_max_K"] > fluid["temperature_min_K"], f"{path} temperature bounds must increase.")
        aliases = require_list(fluid.get("aliases"), f"{path}.aliases")
        require(aliases, f"{path}.aliases must not be empty.")
        for alias_index, alias in enumerate(aliases):
            require_text(alias, f"{path}.aliases[{alias_index}]")
        validate_unique(aliases, f"{path} aliases")
        ideal = [require_mapping(term, f"{path}.ideal[{term_index}]") for term_index, term in enumerate(require_list(fluid.get("ideal"), f"{path}.ideal"))]
        residual = [require_mapping(term, f"{path}.residual[{term_index}]") for term_index, term in enumerate(require_list(fluid.get("residual"), f"{path}.residual"))]
        require(ideal and residual, f"{path} ideal and residual term collections must not be empty.")
        ideal_types = [require_text(term.get("type"), f"{path}.ideal type") for term in ideal]
        residual_types = [require_text(term.get("type"), f"{path}.residual type") for term in residual]
        require(set(ideal_types) <= IDEAL_TYPES, f"{path} contains an unsupported ideal term family.")
        require(set(residual_types) <= RESIDUAL_TYPES, f"{path} contains an unsupported residual term family.")
        _validate_terms(ideal, path + ".ideal", require, require_list, require_number)
        _validate_terms(residual, path + ".residual", require, require_list, require_number)
        for ancillary_name in ("saturation_pressure", "saturated_liquid_density"):
            ancillary = require_mapping(fluid.get(ancillary_name), f"{path}.{ancillary_name}")
            for field in ("Tmin", "Tmax", "T_r", "reducing_value"):
                require_number(ancillary.get(field), f"{path}.{ancillary_name}.{field}")
            _validate_parallel_arrays(ancillary, ("n", "t"), f"{path}.{ancillary_name}", require, require_list, require_number)
            require(ancillary["Tmax"] > ancillary["Tmin"], f"{path}.{ancillary_name} temperature bounds must increase.")
    validate_unique(fluid_ids, "helmholtz fluid IDs")
    validate_unique(fluid_constants, "helmholtz fluid constants")
    validate_unique(prefixes, "helmholtz function prefixes")
    return root


def _validate_terms(terms: list[Any], path: str, require: Callable[[bool, str], None], require_list: Callable[[Any, str], list[Any]], require_number: Callable[[Any, str], float]) -> None:
    for index, term_value in enumerate(terms):
        term = term_value
        term_type = term["type"]
        if term_type in {"IdealGasHelmholtzPower", "IdealGasHelmholtzPlanckEinstein"}:
            _validate_parallel_arrays(term, ("n", "t"), f"{path}[{index}]", require, require_list, require_number)
        elif term_type == "IdealGasHelmholtzPlanckEinsteinFunctionT":
            _validate_parallel_arrays(term, ("n", "v"), f"{path}[{index}]", require, require_list, require_number)
            require_number(term.get("Tcrit"), f"{path}[{index}].Tcrit")
        elif term_type in {"IdealGasHelmholtzLead", "IdealGasHelmholtzEnthalpyEntropyOffset"}:
            require_number(term.get("a1"), f"{path}[{index}].a1")
            require_number(term.get("a2"), f"{path}[{index}].a2")
        elif term_type == "IdealGasHelmholtzLogTau":
            require_number(term.get("a"), f"{path}[{index}].a")
        elif term_type == "IdealGasHelmholtzCP0Constant":
            for field in ("cp_over_R", "Tc", "T0"):
                require_number(term.get(field), f"{path}[{index}].{field}")
        elif term_type == "IdealGasHelmholtzCP0PolyT":
            _validate_parallel_arrays(term, ("c", "t"), f"{path}[{index}]", require, require_list, require_number)
            for field in ("Tc", "T0"):
                require_number(term.get(field), f"{path}[{index}].{field}")
        elif term_type == "ResidualHelmholtzPower":
            _validate_parallel_arrays(term, ("n", "d", "t", "l"), f"{path}[{index}]", require, require_list, require_number)
        elif term_type == "ResidualHelmholtzGaussian":
            _validate_parallel_arrays(term, ("n", "d", "t", "eta", "epsilon", "beta", "gamma"), f"{path}[{index}]", require, require_list, require_number)
        elif term_type == "ResidualHelmholtzNonAnalytic":
            _validate_parallel_arrays(term, ("n", "a", "b", "beta", "A", "B", "C", "D"), f"{path}[{index}]", require, require_list, require_number)
        elif term_type == "ResidualHelmholtzExponential":
            _validate_parallel_arrays(term, ("n", "d", "t", "g", "l"), f"{path}[{index}]", require, require_list, require_number)
        elif term_type == "ResidualHelmholtzGaoB":
            _validate_parallel_arrays(term, ("n", "d", "t", "eta", "beta", "gamma", "epsilon", "b"), f"{path}[{index}]", require, require_list, require_number)


def _validate_parallel_arrays(record: dict[str, Any], fields: tuple[str, ...], path: str, require: Callable[[bool, str], None], require_list: Callable[[Any, str], list[Any]], require_number: Callable[[Any, str], float]) -> None:
    arrays = [require_list(record.get(field), f"{path}.{field}") for field in fields]
    require(arrays[0] and all(len(array) == len(arrays[0]) for array in arrays), f"{path} coefficient arrays must be non-empty and equal length.")
    for field, array in zip(fields, arrays):
        for index, value in enumerate(array):
            require_number(value, f"{path}.{field}[{index}]")


def generate_helmholtz(dataset: dict[str, Any], format_number: Callable[[Any], str]) -> list[str]:
    """Generate pure-fluid Helmholtz equations, derivatives, and P-T dispatch."""

    fluids = dataset["fluids"]
    lines = [
        "'<!-- Pure-fluid fundamental Helmholtz equation backend. -->",
        "",
        "HELMHOLTZ_OK = 0",
        "HELMHOLTZ_ERR_PRESSURE_LOW = 301",
        "HELMHOLTZ_ERR_PRESSURE_HIGH = 302",
        "HELMHOLTZ_ERR_TEMPERATURE_LOW = 303",
        "HELMHOLTZ_ERR_TEMPERATURE_HIGH = 304",
        "HELMHOLTZ_ERR_TWO_PHASE = 305",
        "HELMHOLTZ_ERR_DENSITY = 306",
        "HELMHOLTZ_DELTA_MIN = 1*10^-12",
        "HELMHOLTZ_DELTA_MAX = 8",
        "HELMHOLTZ_PRESSURE_TOLERANCE = 1*10^-8",
        "",
    ]
    lines.extend(_nonanalytic_helpers())
    for fluid in fluids:
        lines.extend(_generate_fluid(fluid, format_number))

    ids = "; ".join(str(fluid["id"]) for fluid in fluids)
    lines.extend((f"HelmholtzFluidIDs = [{ids}]", f"HelmholtzFluidCount = {len(fluids)}", "HelmholtzHasFluid(fluid) = DBHasID(HelmholtzFluidIDs; fluid)"))
    dispatches = {
        "HelmholtzTMinK": "TMinK",
        "HelmholtzTMaxK": "TMaxK",
        "HelmholtzPMaxKPa": "PMaxKPa",
        "HelmholtzTcK": "TcK",
        "HelmholtzRhoCritical": "RhoCritical",
        "HelmholtzR": "R",
        "HelmholtzPsatKPa": "PsatKPa",
        "HelmholtzRhoLSat": "RhoLSat",
        "HelmholtzAlpha0": "Alpha0",
        "HelmholtzAlpha0Tau": "Alpha0Tau",
        "HelmholtzAlpha0TauTau": "Alpha0TauTau",
        "HelmholtzAlphaR": "AlphaR",
        "HelmholtzAlphaRDelta": "AlphaRDelta",
        "HelmholtzAlphaRDeltaDelta": "AlphaRDeltaDelta",
        "HelmholtzAlphaRTau": "AlphaRTau",
        "HelmholtzAlphaRTauTau": "AlphaRTauTau",
        "HelmholtzAlphaRDeltaTau": "AlphaRDeltaTau",
    }
    for public_name, suffix in dispatches.items():
        arguments = "fluid; delta; tau" if suffix.startswith("Alpha") else ("fluid; T_K" if suffix in {"PsatKPa", "RhoLSat"} else "fluid")
        call_arguments = "delta; tau" if suffix.startswith("Alpha") else ("T_K" if suffix in {"PsatKPa", "RhoLSat"} else "")
        terms: list[str] = []
        for fluid in fluids:
            call = f"{fluid['function_prefix']}{suffix}({call_arguments})" if call_arguments else f"{fluid['function_prefix']}{suffix}"
            terms.extend((f"fluid ≡ {fluid['constant']}", call))
        lines.append(f"{public_name}({arguments}) = switch(" + "; ".join(terms + ["0/0"]) + ")")

    lines.extend(
        (
            "HelmholtzPressureRaw(fluid; delta; T_K) = $block{tau = HelmholtzTcK(fluid)/T_K; rho = delta*HelmholtzRhoCritical(fluid); rho*HelmholtzR(fluid)*T_K*(1 + delta*HelmholtzAlphaRDelta(fluid; delta; tau));}",
            "HelmholtzPressureDerivativeRaw(fluid; delta; T_K) = $block{tau = HelmholtzTcK(fluid)/T_K; HelmholtzRhoCritical(fluid)*HelmholtzR(fluid)*T_K*(1 + 2*delta*HelmholtzAlphaRDelta(fluid; delta; tau) + delta^2*HelmholtzAlphaRDeltaDelta(fluid; delta; tau));}",
            "HelmholtzInitialDelta(fluid; p_kPa; T_K) = $block{gas_delta = p_kPa/(HelmholtzRhoCritical(fluid)*HelmholtzR(fluid)*T_K); subcritical = T_K < HelmholtzTcK(fluid); liquid = if(subcritical; p_kPa > HelmholtzPsatKPa(fluid; T_K); 0); liquid_delta = if(liquid; HelmholtzRhoLSat(fluid; T_K)/HelmholtzRhoCritical(fluid); gas_delta); min(HELMHOLTZ_DELTA_MAX; max(HELMHOLTZ_DELTA_MIN; liquid_delta));}",
            "HelmholtzDeltaStep(fluid; delta; p_kPa; T_K) = $block{residual = HelmholtzPressureRaw(fluid; delta; T_K) - p_kPa; derivative = HelmholtzPressureDerivativeRaw(fluid; delta; T_K); candidate = delta - residual/derivative; damped = min(2*delta; max(delta/2; candidate)); min(HELMHOLTZ_DELTA_MAX; max(HELMHOLTZ_DELTA_MIN; damped));}",
            "HelmholtzDeltaPT(fluid; p_kPa; T_K) = $block{d0 = HelmholtzInitialDelta(fluid; p_kPa; T_K); d1 = HelmholtzDeltaStep(fluid; d0; p_kPa; T_K); d2 = HelmholtzDeltaStep(fluid; d1; p_kPa; T_K); d3 = HelmholtzDeltaStep(fluid; d2; p_kPa; T_K); d4 = HelmholtzDeltaStep(fluid; d3; p_kPa; T_K); d5 = HelmholtzDeltaStep(fluid; d4; p_kPa; T_K); d6 = HelmholtzDeltaStep(fluid; d5; p_kPa; T_K); d7 = HelmholtzDeltaStep(fluid; d6; p_kPa; T_K); d8 = HelmholtzDeltaStep(fluid; d7; p_kPa; T_K); d9 = HelmholtzDeltaStep(fluid; d8; p_kPa; T_K); d10 = HelmholtzDeltaStep(fluid; d9; p_kPa; T_K); d11 = HelmholtzDeltaStep(fluid; d10; p_kPa; T_K); d12 = HelmholtzDeltaStep(fluid; d11; p_kPa; T_K); d13 = HelmholtzDeltaStep(fluid; d12; p_kPa; T_K); d14 = HelmholtzDeltaStep(fluid; d13; p_kPa; T_K); d15 = HelmholtzDeltaStep(fluid; d14; p_kPa; T_K); d16 = HelmholtzDeltaStep(fluid; d15; p_kPa; T_K); d16;}",
            "HelmholtzPTBaseStatus(fluid; pressure; temperature) = switch(pressure ≤ 0kPa; HELMHOLTZ_ERR_PRESSURE_LOW; pressure > HelmholtzPMaxKPa(fluid)*kPa; HELMHOLTZ_ERR_PRESSURE_HIGH; temperature < HelmholtzTMinK(fluid)*K; HELMHOLTZ_ERR_TEMPERATURE_LOW; temperature > HelmholtzTMaxK(fluid)*K; HELMHOLTZ_ERR_TEMPERATURE_HIGH; and(temperature < HelmholtzTcK(fluid)*K; abs(pressure/(HelmholtzPsatKPa(fluid; temperature/K)*kPa) - 1) < HELMHOLTZ_PRESSURE_TOLERANCE); HELMHOLTZ_ERR_TWO_PHASE; HELMHOLTZ_OK)",
            "HelmholtzPTStatus(fluid; pressure; temperature) = $block{base_status = HelmholtzPTBaseStatus(fluid; pressure; temperature); p_kPa = if(base_status ≡ HELMHOLTZ_OK; pressure/kPa; 1); T_K = if(base_status ≡ HELMHOLTZ_OK; temperature/K; HelmholtzTMinK(fluid)); delta = if(base_status ≡ HELMHOLTZ_OK; HelmholtzDeltaPT(fluid; p_kPa; T_K); 1); pressure_error = if(base_status ≡ HELMHOLTZ_OK; abs(HelmholtzPressureRaw(fluid; delta; T_K)/p_kPa - 1); 0); if(base_status ≠ HELMHOLTZ_OK; base_status; if(pressure_error ≤ HELMHOLTZ_PRESSURE_TOLERANCE; HELMHOLTZ_OK; HELMHOLTZ_ERR_DENSITY));}",
            "HelmholtzPropertyPT(output; fluid; pressure; temperature) = $block{base_status = HelmholtzPTBaseStatus(fluid; pressure; temperature); p_kPa = if(base_status ≡ HELMHOLTZ_OK; pressure/kPa; 1); T_K = if(base_status ≡ HELMHOLTZ_OK; temperature/K; HelmholtzTMinK(fluid)); delta = if(base_status ≡ HELMHOLTZ_OK; HelmholtzDeltaPT(fluid; p_kPa; T_K); 1); pressure_error = if(base_status ≡ HELMHOLTZ_OK; abs(HelmholtzPressureRaw(fluid; delta; T_K)/p_kPa - 1); 0); status = if(base_status ≠ HELMHOLTZ_OK; base_status; if(pressure_error ≤ HELMHOLTZ_PRESSURE_TOLERANCE; HELMHOLTZ_OK; HELMHOLTZ_ERR_DENSITY)); tau = HelmholtzTcK(fluid)/T_K; rho = delta*HelmholtzRhoCritical(fluid); R = HelmholtzR(fluid); a0 = HelmholtzAlpha0(fluid; delta; tau); a0t = HelmholtzAlpha0Tau(fluid; delta; tau); a0tt = HelmholtzAlpha0TauTau(fluid; delta; tau); ar = HelmholtzAlphaR(fluid; delta; tau); ard = HelmholtzAlphaRDelta(fluid; delta; tau); ardd = HelmholtzAlphaRDeltaDelta(fluid; delta; tau); art = HelmholtzAlphaRTau(fluid; delta; tau); artt = HelmholtzAlphaRTauTau(fluid; delta; tau); ardt = HelmholtzAlphaRDeltaTau(fluid; delta; tau); v = 1/rho; h = R*T_K*(1 + tau*(a0t + art) + delta*ard); u = R*T_K*tau*(a0t + art); s = R*(tau*(a0t + art) - a0 - ar); cv = -R*tau^2*(a0tt + artt); cp = cv + R*(1 + delta*ard - delta*tau*ardt)^2/(1 + 2*delta*ard + delta^2*ardd); w = sqrt(1000*R*T_K*(1 + 2*delta*ard + delta^2*ardd - (1 + delta*ard - delta*tau*ardt)^2/(tau^2*(a0tt + artt)))); raw = switch(output ≡ IF97_P_SPECIFIC_VOLUME; v; output ≡ IF97_P_DENSITY; rho; output ≡ IF97_P_ENTHALPY; h; output ≡ IF97_P_INTERNAL_ENERGY; u; output ≡ IF97_P_ENTROPY; s; output ≡ IF97_P_CP; cp; output ≡ IF97_P_CV; cv; output ≡ IF97_P_SOUND_SPEED; w; 0/0); if(status ≡ HELMHOLTZ_OK; If97ApplyUnits(output; raw); If97Undefined(output));}",
            "HelmholtzDatasetOK = HelmholtzFluidCount ≡ len(HelmholtzFluidIDs)",
            "",
            "#def HelmholtzStatus$(status$)",
            "    #if status$ ≡ HELMHOLTZ_OK",
            "        '<span class=\"ok\">Valid fundamental Helmholtz equation state</span>",
            "    #end if",
            "    #if status$ ≡ HELMHOLTZ_ERR_PRESSURE_LOW",
            "        '<span class=\"err\">Pressure is below the equation range</span>",
            "    #end if",
            "    #if status$ ≡ HELMHOLTZ_ERR_PRESSURE_HIGH",
            "        '<span class=\"err\">Pressure is above the equation range</span>",
            "    #end if",
            "    #if status$ ≡ HELMHOLTZ_ERR_TEMPERATURE_LOW",
            "        '<span class=\"err\">Temperature is below the equation range</span>",
            "    #end if",
            "    #if status$ ≡ HELMHOLTZ_ERR_TEMPERATURE_HIGH",
            "        '<span class=\"err\">Temperature is above the equation range</span>",
            "    #end if",
            "    #if status$ ≡ HELMHOLTZ_ERR_TWO_PHASE",
            "        '<span class=\"err\">State lies on the saturation boundary and requires phase quality</span>",
            "    #end if",
            "    #if status$ ≡ HELMHOLTZ_ERR_DENSITY",
            "        '<span class=\"err\">Pressure-temperature density solution did not converge</span>",
            "    #end if",
            "#end def",
            "",
        )
    )
    return lines


def _generate_fluid(fluid: dict[str, Any], f: Callable[[Any], str]) -> list[str]:
    prefix = fluid["function_prefix"]
    molar_mass = float(fluid["molar_mass_kg_per_mol"])
    rho_critical = float(fluid["reducing_molar_density_mol_per_m3"]) * molar_mass
    R = float(fluid["gas_constant_J_per_molK"]) / molar_mass / 1000
    lines = [
        f"'{fluid['name']} fundamental equation from source ID {fluid['source_id']}.",
        f"{prefix}TMinK = {f(fluid['temperature_min_K'])}",
        f"{prefix}TMaxK = {f(fluid['temperature_max_K'])}",
        f"{prefix}PMaxKPa = {f(float(fluid['pressure_max_Pa']) / 1000)}",
        f"{prefix}TcK = {f(fluid['reducing_temperature_K'])}",
        f"{prefix}RhoCritical = {f(rho_critical)}",
        f"{prefix}R = {f(R)}",
    ]
    p_sat = fluid["saturation_pressure"]
    rho_l = fluid["saturated_liquid_density"]
    p_terms = " + ".join(f"{f(n)}*(theta)^{f(t)}" for n, t in zip(p_sat["n"], p_sat["t"]))
    rho_terms = " + ".join(f"{f(n)}*(theta)^{f(t)}" for n, t in zip(rho_l["n"], rho_l["t"]))
    lines.extend(
        (
            f"{prefix}PsatKPa(T_K) = $block{{theta = 1 - T_K/{f(p_sat['T_r'])}; {f(float(p_sat['reducing_value']) / 1000)}*exp({f(p_sat['T_r'])}/T_K*({p_terms}));}}",
            f"{prefix}RhoLSat(T_K) = $block{{theta = 1 - T_K/{f(rho_l['T_r'])}; {f(float(rho_l['reducing_value']) * molar_mass)}*(1 + {rho_terms});}}",
        )
    )
    ideal = _ideal_expressions(fluid, f)
    residual = _residual_expressions(fluid, f)
    lines.extend(
        (
            f"{prefix}Alpha0(delta; tau) = {ideal['base']}",
            f"{prefix}Alpha0Tau(delta; tau) = {ideal['tau']}",
            f"{prefix}Alpha0TauTau(delta; tau) = {ideal['tautau']}",
            f"{prefix}AlphaR(delta; tau) = {residual['base']}",
            f"{prefix}AlphaRDelta(delta; tau) = {residual['delta']}",
            f"{prefix}AlphaRDeltaDelta(delta; tau) = {residual['deltadelta']}",
            f"{prefix}AlphaRTau(delta; tau) = {residual['tau']}",
            f"{prefix}AlphaRTauTau(delta; tau) = {residual['tautau']}",
            f"{prefix}AlphaRDeltaTau(delta; tau) = {residual['deltatau']}",
            "",
        )
    )
    return lines


def _ideal_expressions(fluid: dict[str, Any], f: Callable[[Any], str]) -> dict[str, str]:
    parts = {key: [] for key in ("base", "tau", "tautau")}
    parts["base"].append("ln(delta)")
    for term in fluid["ideal"]:
        kind = term["type"]
        if kind in {"IdealGasHelmholtzLead", "IdealGasHelmholtzEnthalpyEntropyOffset"}:
            parts["base"].extend((f(term["a1"]), f"{f(term['a2'])}*tau"))
            parts["tau"].append(f(term["a2"]))
        elif kind == "IdealGasHelmholtzLogTau":
            parts["base"].append(f"{f(term['a'])}*ln(tau)")
            parts["tau"].append(f"{f(term['a'])}/tau")
            parts["tautau"].append(f"{f(-float(term['a']))}/tau^2")
        elif kind == "IdealGasHelmholtzPower":
            for n, t in zip(term["n"], term["t"]):
                parts["base"].append(f"{f(n)}*tau^{f(t)}")
                parts["tau"].append(f"{f(float(n)*float(t))}*tau^{f(float(t)-1)}")
                parts["tautau"].append(f"{f(float(n)*float(t)*(float(t)-1))}*tau^{f(float(t)-2)}")
        elif kind == "IdealGasHelmholtzCP0Constant":
            cp_over_R = float(term["cp_over_R"])
            tau0 = float(term["Tc"]) / float(term["T0"])
            parts["base"].append(f"{f(cp_over_R)} + {f(-cp_over_R)}*tau/{f(tau0)} + {f(cp_over_R)}*ln(tau/{f(tau0)})")
            parts["tau"].append(f"{f(cp_over_R)}/tau + {f(-cp_over_R)}/{f(tau0)}")
            parts["tautau"].append(f"{f(-cp_over_R)}/tau^2")
        elif kind == "IdealGasHelmholtzCP0PolyT":
            Tc = float(term["Tc"])
            T0 = float(term["T0"])
            tau0 = Tc / T0
            for coefficient, exponent in zip(term["c"], term["t"]):
                c = float(coefficient)
                t = float(exponent)
                if t == 0:
                    parts["base"].append(f"{f(c)} + {f(-c)}*tau/{f(tau0)} + {f(c)}*ln(tau/{f(tau0)})")
                    parts["tau"].append(f"{f(c)}/tau + {f(-c)}/{f(tau0)}")
                    parts["tautau"].append(f"{f(-c)}/tau^2")
                elif t == -1:
                    parts["base"].append(f"{f(c)}*tau/{f(Tc)}*ln({f(tau0)}/tau) + {f(c)}/{f(Tc)}*(tau - {f(tau0)})")
                    parts["tau"].append(f"{f(c)}/{f(Tc)}*ln({f(tau0)}/tau)")
                    parts["tautau"].append(f"{f(-c)}/(tau*{f(Tc)})")
                else:
                    parts["base"].append(f"{f(-c)}*{f(Tc)}^{f(t)}*tau^{f(-t)}/({f(t)}*{f(t + 1)}) + {f(-c)}*{f(T0)}^{f(t + 1)}*tau/({f(Tc)}*{f(t + 1)}) + {f(c)}*{f(T0)}^{f(t)}/{f(t)}")
                    parts["tau"].append(f"{f(c)}*{f(Tc)}^{f(t)}*tau^{f(-t - 1)}/{f(t + 1)} + {f(-c)}*{f(Tc)}^{f(t)}/({f(tau0)}^{f(t + 1)}*{f(t + 1)})")
                    parts["tautau"].append(f"{f(-c)}*({f(Tc)}/tau)^{f(t)}/tau^2")
        elif kind in {"IdealGasHelmholtzPlanckEinstein", "IdealGasHelmholtzPlanckEinsteinFunctionT"}:
            theta_values = term["t"] if kind == "IdealGasHelmholtzPlanckEinstein" else [value / term["Tcrit"] for value in term["v"]]
            for n, theta in zip(term["n"], theta_values):
                e = f(theta)
                parts["base"].append(f"{f(n)}*ln(1 - exp(-{e}*tau))")
                parts["tau"].append(f"{f(n)}*{e}/(exp({e}*tau) - 1)")
                parts["tautau"].append(f"{f(-float(n))}*{e}^2*exp({e}*tau)/(exp({e}*tau) - 1)^2")
    return {key: " + ".join(values) if values else "0" for key, values in parts.items()}


def _residual_expressions(fluid: dict[str, Any], f: Callable[[Any], str]) -> dict[str, str]:
    parts = {key: [] for key in ("base", "delta", "deltadelta", "tau", "tautau", "deltatau")}
    for group in fluid["residual"]:
        kind = group["type"]
        count = len(group["n"])
        for index in range(count):
            if kind in {"ResidualHelmholtzPower", "ResidualHelmholtzExponential"}:
                n, d, t, l = (float(group[key][index]) for key in ("n", "d", "t", "l"))
                coefficient = 1.0 if kind == "ResidualHelmholtzPower" else float(group["g"][index])
                exp_factor = "" if kind == "ResidualHelmholtzPower" and l == 0 else f"*exp(-{f(coefficient)}*delta^{f(l)})"
                base = f"{f(n)}*delta^{f(d)}*tau^{f(t)}{exp_factor}"
                has_decay = not (kind == "ResidualHelmholtzPower" and l == 0)
                A = f"({f(d)}/delta" + ("" if not has_decay else f" - {f(coefficient*l)}*delta^{f(l-1)}") + ")"
                A2 = f"(-{f(d)}/delta^2" + ("" if not has_decay else f" - {f(coefficient*l*(l-1))}*delta^{f(l-2)}") + ")"
                B = f"({f(t)}/tau)"
                parts["base"].append(base)
                parts["delta"].append(f"({base})*{A}")
                parts["deltadelta"].append(f"({base})*({A}^2 + {A2})")
                parts["tau"].append(f"({base})*{B}")
                parts["tautau"].append(f"({base})*{f(t*(t-1))}/tau^2")
                parts["deltatau"].append(f"({base})*{A}*{B}")
            elif kind == "ResidualHelmholtzGaussian":
                n, d, t, eta, epsilon, beta, gamma = (float(group[key][index]) for key in ("n", "d", "t", "eta", "epsilon", "beta", "gamma"))
                base = f"{f(n)}*delta^{f(d)}*tau^{f(t)}*exp(-{f(eta)}*(delta - {f(epsilon)})^2 - {f(beta)}*(tau - {f(gamma)})^2)"
                A = f"({f(d)}/delta - {f(2*eta)}*(delta - {f(epsilon)}))"
                A2 = f"(-{f(d)}/delta^2 - {f(2*eta)})"
                B = f"({f(t)}/tau - {f(2*beta)}*(tau - {f(gamma)}))"
                B2 = f"(-{f(t)}/tau^2 - {f(2*beta)})"
                parts["base"].append(base)
                parts["delta"].append(f"({base})*{A}")
                parts["deltadelta"].append(f"({base})*({A}^2 + {A2})")
                parts["tau"].append(f"({base})*{B}")
                parts["tautau"].append(f"({base})*({B}^2 + {B2})")
                parts["deltatau"].append(f"({base})*{A}*{B}")
            elif kind == "ResidualHelmholtzGaoB":
                n, d, t, eta, beta, gamma, epsilon, b = (float(group[key][index]) for key in ("n", "d", "t", "eta", "beta", "gamma", "epsilon", "b"))
                denominator = f"({f(b)} + {f(beta)}*(tau - {f(gamma)})^2)"
                base = f"{f(n)}*delta^{f(d)}*tau^{f(t)}*exp({f(eta)}*(delta - {f(epsilon)})^2 + 1/{denominator})"
                A = f"({f(d)}/delta + {f(2*eta)}*(delta - {f(epsilon)}))"
                A2 = f"(-{f(d)}/delta^2 + {f(2*eta)})"
                B = f"({f(t)}/tau - {f(2*beta)}*(tau - {f(gamma)})/{denominator}^2)"
                B2 = f"(-{f(t)}/tau^2 - {f(2*beta)}/{denominator}^2 + {f(8*beta*beta)}*(tau - {f(gamma)})^2/{denominator}^3)"
                parts["base"].append(base)
                parts["delta"].append(f"({base})*{A}")
                parts["deltadelta"].append(f"({base})*({A}^2 + {A2})")
                parts["tau"].append(f"({base})*{B}")
                parts["tautau"].append(f"({base})*({B}^2 + {B2})")
                parts["deltatau"].append(f"({base})*{A}*{B}")
            else:
                arguments = "; ".join(f(group[key][index]) for key in ("n", "a", "b", "beta", "A", "B", "C", "D"))
                for derivative, suffix in (("base", "Base"), ("delta", "Delta"), ("deltadelta", "DeltaDelta"), ("tau", "Tau"), ("tautau", "TauTau"), ("deltatau", "DeltaTau")):
                    parts[derivative].append(f"HelmholtzNA{suffix}(delta; tau; {arguments})")
    return {key: " + ".join(values) if values else "0" for key, values in parts.items()}


def _nonanalytic_helpers() -> list[str]:
    args = "delta; tau; n; a; b; beta; coef_A; coef_B; coef_C; coef_D"
    common = "d = if(abs(delta - 1) < 1*10^-12; 1 + 1*10^-12; delta); t = if(abs(tau - 1) < 1*10^-12; 1 + 1*10^-12; tau); x = d - 1; y = t - 1; theta = 1 - t + coef_A*(x^2)^(1/(2*beta)); psi = exp(-coef_C*x^2 - coef_D*y^2); Delta = theta^2 + coef_B*(x^2)^a;"
    delta_derivatives = "theta_d = coef_A/beta*(x^2)^(1/(2*beta) - 1)*x; theta_dd = coef_A/beta*(1/beta - 1)*(x^2)^(1/(2*beta) - 1); psi_d = -2*coef_C*x*psi; psi_dd = (2*coef_C*x^2 - 1)*2*coef_C*psi; Delta_d = 2*theta*theta_d + 2*coef_B*a*(x^2)^(a - 1)*x; Delta_dd = 2*(theta*theta_dd + theta_d^2 + coef_B*(2*a^2 - a)*(x^2)^(a - 1)); F = Delta^b; F_d = b*Delta^(b - 1)*Delta_d; F_dd = b*(Delta^(b - 1)*Delta_dd + (b - 1)*Delta^(b - 2)*Delta_d^2);"
    tau_derivatives = "psi_t = -2*coef_D*y*psi; psi_tt = (2*coef_D*y^2 - 1)*2*coef_D*psi; Delta_t = -2*theta; Delta_tt = 2; F = Delta^b; F_t = b*Delta^(b - 1)*Delta_t; F_tt = b*(Delta^(b - 1)*Delta_tt + (b - 1)*Delta^(b - 2)*Delta_t^2);"
    mixed_derivatives = delta_derivatives + " psi_t = -2*coef_D*y*psi; psi_dt = psi_d*(-2*coef_D*y); Delta_t = -2*theta; Delta_dt = -2*theta_d; F_t = b*Delta^(b - 1)*Delta_t; F_dt = b*(Delta^(b - 1)*Delta_dt + (b - 1)*Delta^(b - 2)*Delta_d*Delta_t);"
    return [
        f"HelmholtzNABase({args}) = $block{{{common} n*d*Delta^b*psi;}}",
        f"HelmholtzNADelta({args}) = $block{{{common} {delta_derivatives} n*(F*(psi + d*psi_d) + F_d*d*psi);}}",
        f"HelmholtzNADeltaDelta({args}) = $block{{{common} {delta_derivatives} n*(F*(2*psi_d + d*psi_dd) + 2*F_d*(psi + d*psi_d) + F_dd*d*psi);}}",
        f"HelmholtzNATau({args}) = $block{{{common} {tau_derivatives} n*d*(F*psi_t + F_t*psi);}}",
        f"HelmholtzNATauTau({args}) = $block{{{common} {tau_derivatives} n*d*(F_tt*psi + 2*F_t*psi_t + F*psi_tt);}}",
        f"HelmholtzNADeltaTau({args}) = $block{{{common} {mixed_derivatives} n*(F*(psi_t + d*psi_dt) + d*F_d*psi_t + F_t*(psi + d*psi_d) + F_dt*d*psi);}}",
        "",
    ]
