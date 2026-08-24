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
    "R11": {
        "id": 303,
        "constant": "THERMO_R11",
        "function_prefix": "HelmholtzR11",
        "display_name": "R11",
        "description": "Pure trichlorofluoromethane using the Jacobsen et al. reference Helmholtz equation of state.",
        "source_id": 5,
        "source_constant": "THERMO_SRC_R11_EOS",
        "citation": "Jacobsen, Penoncello, and Lemmon, A Fundamental Equation for Trichlorofluoromethane R-11, Fluid Phase Equilibria 80, 45-56, 1992",
        "reference_note": "Primary EOS DOI 10.1016/0378-3812(92)87054-Q.",
        "eos_citation": "Jacobsen-FPE-1992",
        "eos_index": 0,
        "valid_temperature_max_K": 625.0,
    },
    "R12": {
        "id": 304,
        "constant": "THERMO_R12",
        "function_prefix": "HelmholtzR12",
        "display_name": "R12",
        "description": "Pure dichlorodifluoromethane using the Marx et al. reference Helmholtz equation of state.",
        "source_id": 6,
        "source_constant": "THERMO_SRC_R12_EOS",
        "citation": "Marx, Pruss, and Wagner, Neue Zustandsgleichung fuer R 12, R 22, R 11 und R 113, VDI Verlag, 1992",
        "reference_note": "Primary EOS reference is VDI Fortschritt-Berichte series 19 number 57.",
        "eos_citation": "Marx-BOOK-1992",
        "eos_index": 0,
        "valid_temperature_max_K": 525.0,
    },
    "R13": {
        "id": 305,
        "constant": "THERMO_R13",
        "function_prefix": "HelmholtzR13",
        "display_name": "R13",
        "description": "Pure chlorotrifluoromethane using the Platzer et al. reference Helmholtz equation of state.",
        "source_id": 7,
        "source_constant": "THERMO_SRC_R13_EOS",
        "citation": "Platzer, Polt, and Maurer, Thermophysical Properties of Refrigerants, Springer-Verlag, 1990",
        "reference_note": "Primary reference DOI 10.1007/978-3-662-02608-3.",
        "eos_citation": "Platzer-BOOK-1990",
        "eos_index": 0,
        "valid_temperature_max_K": 450.0,
    },
    "R134a": {
        "id": 306,
        "constant": "THERMO_R134A",
        "function_prefix": "HelmholtzR134A",
        "display_name": "R134a",
        "description": "Pure 1,1,1,2-tetrafluoroethane using the Tillner-Roth and Baehr reference Helmholtz equation of state.",
        "source_id": 8,
        "source_constant": "THERMO_SRC_R134A_EOS",
        "citation": "Tillner-Roth and Baehr, An International Standard Formulation for the Thermodynamic Properties of R134a, J. Phys. Chem. Ref. Data 23, 657-729, 1994",
        "doi": "10.1063/1.555958",
        "eos_citation": "TillnerRoth-JPCRD-1994",
        "valid_temperature_max_K": 455.0,
    },
    "R32": {
        "id": 307,
        "constant": "THERMO_R32",
        "function_prefix": "HelmholtzR32",
        "display_name": "R32",
        "description": "Pure difluoromethane using the Tillner-Roth and Yokozeki reference Helmholtz equation of state.",
        "source_id": 9,
        "source_constant": "THERMO_SRC_R32_EOS",
        "citation": "Tillner-Roth and Yokozeki, An International Standard Equation of State for Difluoromethane R-32, J. Phys. Chem. Ref. Data 26, 1273-1328, 1997",
        "doi": "10.1063/1.556002",
        "eos_citation": "TillnerRoth-JPCRD-1997",
        "valid_temperature_max_K": 435.0,
    },
    "R1234yf": {
        "id": 308,
        "constant": "THERMO_R1234YF",
        "function_prefix": "HelmholtzR1234YF",
        "display_name": "R1234yf",
        "description": "Pure 2,3,3,3-tetrafluoropropene using the Lemmon and Akasaka reference Helmholtz equation of state.",
        "source_id": 10,
        "source_constant": "THERMO_SRC_R1234YF_EOS",
        "citation": "Lemmon and Akasaka, An International Standard Formulation for 2,3,3,3-Tetrafluoroprop-1-ene R1234yf, Int. J. Thermophys. 43, 2022",
        "doi": "10.1007/s10765-022-03015-y",
        "eos_citation": "Lemmon-IJT-2022",
        "valid_temperature_max_K": 410.0,
    },
    "n-Propane": {
        "id": 309,
        "constant": "THERMO_R290",
        "function_prefix": "HelmholtzR290",
        "display_name": "R290 (propane)",
        "description": "Pure propane using the Lemmon et al. reference Helmholtz equation of state.",
        "source_id": 11,
        "source_constant": "THERMO_SRC_R290_EOS",
        "citation": "Lemmon, McLinden, and Wagner, Thermodynamic Properties of Propane, J. Chem. Eng. Data 54, 3141-3180, 2009",
        "doi": "10.1021/je900217v",
        "eos_citation": "Lemmon-JCED-2009",
        "valid_temperature_max_K": 650.0,
    },
    "IsoButane": {
        "id": 310,
        "constant": "THERMO_R600A",
        "function_prefix": "HelmholtzR600A",
        "display_name": "R600a (isobutane)",
        "description": "Pure isobutane using the Buecker and Wagner reference Helmholtz equation of state.",
        "source_id": 12,
        "source_constant": "THERMO_SRC_R600A_EOS",
        "citation": "Buecker and Wagner, A Reference Equation of State for Isobutane, J. Phys. Chem. Ref. Data 35, 929-1019, 2006",
        "doi": "10.1063/1.1901687",
        "eos_citation": "Buecker-JPCRD-2006B",
        "valid_temperature_max_K": 575.0,
    },
    "Ammonia": {
        "id": 311,
        "constant": "THERMO_R717",
        "function_prefix": "HelmholtzR717",
        "display_name": "R717 (ammonia)",
        "description": "Pure ammonia using the Gao et al. reference Helmholtz equation of state.",
        "source_id": 13,
        "source_constant": "THERMO_SRC_R717_EOS",
        "citation": "Gao, Wu, Bell, and Lemmon, Thermodynamic Properties of Ammonia from the Melting Line to 725 K and 1000 MPa, J. Phys. Chem. Ref. Data 49, 2020",
        "eos_citation": "Gao-JPCRD-2020",
        "reference_note": "Primary equation selected by the pinned CoolProp default EOS ordering.",
        "valid_temperature_max_K": 725.0,
    },
}

ALLOWED_IDEAL_TYPES = {
    "IdealGasHelmholtzLead",
    "IdealGasHelmholtzLogTau",
    "IdealGasHelmholtzPower",
    "IdealGasHelmholtzPlanckEinstein",
    "IdealGasHelmholtzPlanckEinsteinFunctionT",
    "IdealGasHelmholtzEnthalpyEntropyOffset",
    "IdealGasHelmholtzCP0Constant",
    "IdealGasHelmholtzCP0PolyT",
}
ALLOWED_RESIDUAL_TYPES = {
    "ResidualHelmholtzPower",
    "ResidualHelmholtzGaussian",
    "ResidualHelmholtzNonAnalytic",
    "ResidualHelmholtzExponential",
    "ResidualHelmholtzGaoB",
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
    eos_index = config.get("eos_index", 0)
    require(isinstance(eos_records, list) and len(eos_records) > eos_index, f"{name} does not contain the configured EOS record.")
    eos = eos_records[eos_index]
    ideal_types = {term.get("type") for term in eos.get("alpha0", [])}
    residual_types = {term.get("type") for term in eos.get("alphar", [])}
    require(ideal_types <= ALLOWED_IDEAL_TYPES, f"{name} has unsupported ideal Helmholtz terms: {sorted(ideal_types - ALLOWED_IDEAL_TYPES)}")
    require(residual_types <= ALLOWED_RESIDUAL_TYPES, f"{name} has unsupported residual Helmholtz terms: {sorted(residual_types - ALLOWED_RESIDUAL_TYPES)}")
    expected_citation = config.get("eos_citation", "Span-JPCRD-2000" if name == "Nitrogen" else "Span-JPCRD-1996")
    require(eos.get("BibTeX_EOS") == expected_citation, f"{name} EOS citation changed upstream.")
    p_sat = raw.get("ANCILLARIES", {}).get("pS", {})
    rho_liquid = raw.get("ANCILLARIES", {}).get("rhoL", {})
    require(p_sat.get("type") in {"pL", "pV"} and p_sat.get("using_tau_r") is True, f"{name} saturation-pressure form changed upstream.")
    require(rho_liquid.get("type") == "rhoLnoexp", f"{name} saturated-liquid-density form changed upstream.")
    reducing = eos.get("STATES", {}).get("reducing", {})
    fluid = {
        "id": config["id"],
        "constant": config["constant"],
        "function_prefix": config["function_prefix"],
        "name": config["display_name"],
        "description": config["description"],
        "source_id": config["source_id"],
        "aliases": list(dict.fromkeys([name, *raw["INFO"]["ALIASES"]])),
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
    reference_note = config.get("reference_note")
    if reference_note is None:
        reference_note = f"Primary EOS DOI {config['doi']}."
    source = {
        "id": config["source_id"],
        "constant": config["source_constant"],
        "name": f"{config['display_name']} reference equation of state",
        "citation": config["citation"],
        "revision": f"CoolProp record at pinned revision for {eos['BibTeX_EOS']}",
        "license": "Equation coefficients are factual records; CoolProp source record is distributed under the MIT License",
        "notes": f"{reference_note} Imported from the pinned CoolProp pure-fluid JSON record.",
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
