"""Import selected CoolProp pure-fluid Helmholtz records into a curated DRAT source."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from GeneratorSupport import GeneratorError, write_or_check
from GenerateThermophysicalLibrary import (
    require_constant,
    require_integer,
    require_list,
    require_mapping,
    require_number,
    require_text,
    validate_helmholtz,
    validate_unique,
)


UPSTREAM_FLUIDS = {
    "Nitrogen": {
        "id": 301,
        "constant": "THERMO_NITROGEN",
        "function_prefix": "HelmholtzN2",
        "display_name": "Nitrogen",
        "description": "Pure nitrogen using the Span et al. reference Helmholtz equation of state.",
        "source_id": 3,
        "source_constant": "THERMO_SRC_NITROGEN_EOS",
        "citation": "Span, Lemmon, Jacobsen, Wagner, and Yokozeki, A Reference Equation of State for the Thermodynamic Properties of Nitrogen, J. Phys. Chem. Ref. Data 29, 1361-1433, 2000",
        "doi": "10.1063/1.1349047",
        "valid_temperature_max_K": 1000.0,
    },
    "CarbonDioxide": {
        "id": 302,
        "constant": "THERMO_CARBON_DIOXIDE",
        "function_prefix": "HelmholtzCO2",
        "display_name": "Carbon dioxide",
        "description": "Pure carbon dioxide using the Span-Wagner reference Helmholtz equation of state.",
        "source_id": 4,
        "source_constant": "THERMO_SRC_CO2_EOS",
        "citation": "Span and Wagner, A New Equation of State for Carbon Dioxide, J. Phys. Chem. Ref. Data 25, 1509-1596, 1996",
        "doi": "10.1063/1.555991",
        "valid_temperature_max_K": 1100.0,
    },
}

ALLOWED_IDEAL_TYPES = {
    "IdealGasHelmholtzLead",
    "IdealGasHelmholtzLogTau",
    "IdealGasHelmholtzPower",
    "IdealGasHelmholtzPlanckEinstein",
    "IdealGasHelmholtzPlanckEinsteinFunctionT",
    "IdealGasHelmholtzEnthalpyEntropyOffset",
}
ALLOWED_RESIDUAL_TYPES = {
    "ResidualHelmholtzPower",
    "ResidualHelmholtzGaussian",
    "ResidualHelmholtzNonAnalytic",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GeneratorError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise GeneratorError(f"CoolProp source does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise GeneratorError(f"CoolProp source is invalid JSON: {path}: {error}") from error
    require(isinstance(value, dict), f"CoolProp source root must be an object: {path}")
    return value


def select_fluid(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = load_json(path)
    name = raw.get("INFO", {}).get("NAME")
    require(name in UPSTREAM_FLUIDS, f"Unsupported CoolProp fluid record: {name!r}")
    config = UPSTREAM_FLUIDS[name]
    eos_records = raw.get("EOS")
    require(isinstance(eos_records, list) and len(eos_records) == 1, f"{name} must contain exactly one EOS record.")
    eos = eos_records[0]
    ideal_types = {term.get("type") for term in eos.get("alpha0", [])}
    residual_types = {term.get("type") for term in eos.get("alphar", [])}
    require(ideal_types <= ALLOWED_IDEAL_TYPES, f"{name} has unsupported ideal Helmholtz terms: {sorted(ideal_types - ALLOWED_IDEAL_TYPES)}")
    require(residual_types <= ALLOWED_RESIDUAL_TYPES, f"{name} has unsupported residual Helmholtz terms: {sorted(residual_types - ALLOWED_RESIDUAL_TYPES)}")
    require(eos.get("BibTeX_EOS") in {"Span-JPCRD-2000", "Span-JPCRD-1996"}, f"{name} EOS citation changed upstream.")
    p_sat = raw.get("ANCILLARIES", {}).get("pS", {})
    rho_liquid = raw.get("ANCILLARIES", {}).get("rhoL", {})
    require(p_sat.get("type") == "pL" and p_sat.get("using_tau_r") is True, f"{name} saturation-pressure form changed upstream.")
    require(rho_liquid.get("type") == "rhoLnoexp", f"{name} saturated-liquid-density form changed upstream.")
    reducing = eos.get("STATES", {}).get("reducing", {})
    fluid = {
        "id": config["id"],
        "constant": config["constant"],
        "function_prefix": config["function_prefix"],
        "name": config["display_name"],
        "description": config["description"],
        "source_id": config["source_id"],
        "aliases": raw["INFO"]["ALIASES"],
        "cas": raw["INFO"]["CAS"],
        "molar_mass_kg_per_mol": eos["molar_mass"],
        "gas_constant_J_per_molK": eos["gas_constant"],
        "temperature_min_K": eos["Ttriple"],
        "temperature_max_K": config["valid_temperature_max_K"],
        "pressure_max_Pa": eos["p_max"],
        "reducing_temperature_K": reducing["T"],
        "reducing_molar_density_mol_per_m3": reducing["rhomolar"],
        "ideal": eos["alpha0"],
        "residual": eos["alphar"],
        "saturation_pressure": {key: p_sat[key] for key in ("Tmin", "Tmax", "T_r", "reducing_value", "n", "t", "type", "using_tau_r")},
        "saturated_liquid_density": {key: rho_liquid[key] for key in ("Tmin", "Tmax", "T_r", "reducing_value", "n", "t", "type")},
        "upstream_file": path.name,
        "upstream_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    source = {
        "id": config["source_id"],
        "constant": config["source_constant"],
        "name": f"{config['display_name']} reference equation of state",
        "citation": config["citation"],
        "revision": f"CoolProp record at pinned revision for {eos['BibTeX_EOS']}",
        "license": "Equation coefficients are factual records; CoolProp source record is distributed under the MIT License",
        "notes": f"Primary EOS DOI {config['doi']}. Imported from the pinned CoolProp pure-fluid JSON record.",
    }
    return source, fluid


def build_dataset(paths: list[Path], revision: str) -> dict[str, Any]:
    require(len(revision) == 40 and all(character in "0123456789abcdef" for character in revision.lower()), "CoolProp revision must be a 40-character Git commit.")
    selected = [select_fluid(path) for path in paths]
    sources = [item[0] for item in selected]
    fluids = [item[1] for item in selected]
    require(len({item["id"] for item in fluids}) == len(fluids), "Imported fluid IDs must be unique.")
    require(len({item["constant"] for item in fluids}) == len(fluids), "Imported fluid constants must be unique.")
    require({item["constant"] for item in fluids} == {item["constant"] for item in UPSTREAM_FLUIDS.values()}, "Import must contain exactly one record for every supported Helmholtz fluid.")
    dataset = {
        "schema_version": 1,
        "upstream": {
            "project": "CoolProp",
            "repository": "https://github.com/CoolProp/CoolProp",
            "revision": revision.lower(),
            "license": "MIT",
        },
        "sources": sources,
        "fluids": fluids,
    }
    validate_helmholtz(dataset, require, require_mapping, require_list, require_integer, require_text, require_constant, require_number, validate_unique)
    return dataset


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    options = parse_arguments(sys.argv[1:] if arguments is None else arguments)
    try:
        dataset = build_dataset(options.sources, options.revision)
        rendered = json.dumps(dataset, indent=2, ensure_ascii=False) + "\n"
        write_or_check(options.output, rendered, options.check)
    except GeneratorError as error:
        print(f"CoolProp Helmholtz import error: {error}", file=sys.stderr)
        return 1
    print(f"{'Verified' if options.check else 'Generated'} {options.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
