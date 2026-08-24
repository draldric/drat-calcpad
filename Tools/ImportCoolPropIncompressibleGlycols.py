"""Import the pinned CoolProp aqueous-glycol equation records into DRAT JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from GeneratorSupport import GeneratorError, write_or_check


CONFIG = {
    "MEG": {"id": 1, "constant": "GLYCOL_ETHYLENE", "prefix": "GlycolMEG", "name": "Ethylene glycol and water"},
    "MPG": {"id": 2, "constant": "GLYCOL_PROPYLENE", "prefix": "GlycolMPG", "name": "Propylene glycol and water"},
}
PROPERTIES = ("density", "specific_heat", "viscosity", "conductivity")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GeneratorError(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise GeneratorError(f"Invalid CoolProp incompressible source {path}: {error}") from error
    require(isinstance(value, dict), f"CoolProp source must be an object: {path}")
    return value


def select(path: Path) -> dict[str, Any]:
    raw = load(path)
    code = raw.get("name")
    require(code in CONFIG, f"Unsupported aqueous-glycol record: {code!r}")
    config = CONFIG[code]
    require(raw.get("xid") == "mass", f"{code} concentration basis changed upstream.")
    require(raw.get("reference") == "Melinder2010", f"{code} reference changed upstream.")
    require(raw.get("T_freeze", {}).get("type") == "polynomial", f"{code} freezing correlation changed upstream.")
    properties: dict[str, Any] = {}
    for name in PROPERTIES:
        record = raw.get(name, {})
        expected = "exppolynomial" if name == "viscosity" else "polynomial"
        require(record.get("type") == expected, f"{code} {name} equation family changed upstream.")
        coefficients = record.get("coeffs")
        require(isinstance(coefficients, list) and coefficients and all(isinstance(row, list) and row for row in coefficients), f"{code} {name} coefficients are invalid.")
        properties[name] = {"type": expected, "coeffs": coefficients}
    return {
        **config,
        "description": raw["description"],
        "reference": raw["reference"],
        "temperature_min_K": raw["Tmin"],
        "temperature_max_K": raw["Tmax"],
        "temperature_base_K": raw["Tbase"],
        "mass_fraction_min": raw["xmin"],
        "mass_fraction_max": raw["xmax"],
        "mass_fraction_base": raw["xbase"],
        "freezing_temperature": raw["T_freeze"],
        "properties": properties,
        "upstream_file": path.name,
        "upstream_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def build(paths: list[Path], revision: str) -> dict[str, Any]:
    require(len(revision) == 40 and all(character in "0123456789abcdef" for character in revision.lower()), "CoolProp revision must be a full Git commit.")
    families = [select(path) for path in paths]
    require({item["constant"] for item in families} == {item["constant"] for item in CONFIG.values()}, "Import must contain exactly MEG and MPG once each.")
    return {
        "schema_version": 1,
        "upstream": {"project": "CoolProp", "repository": "https://github.com/CoolProp/CoolProp", "revision": revision.lower(), "license": "MIT"},
        "source": {
            "name": "Melinder aqueous glycol correlations",
            "citation": "Melinder, Properties of Secondary Working Fluids for Indirect Systems, IIR, 2010",
            "notes": "Equation coefficients curated from the pinned CoolProp MEG and MPG incompressible records; valid only within each recorded temperature, mass-fraction, and liquid-phase range.",
        },
        "families": sorted(families, key=lambda item: item["id"]),
    }


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args(sys.argv[1:] if arguments is None else arguments)
    try:
        rendered = json.dumps(build(options.sources, options.revision), indent=2, ensure_ascii=False) + "\n"
        write_or_check(options.output, rendered, options.check)
    except GeneratorError as error:
        print(f"CoolProp glycol import error: {error}", file=sys.stderr)
        return 1
    print(f"{'Verified' if options.check else 'Generated'} {options.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
