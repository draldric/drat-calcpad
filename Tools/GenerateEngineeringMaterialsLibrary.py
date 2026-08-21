"""Generate the Engineering Materials CalcPad library from its workbook."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import pandas as pd

from GeneratorSupport import GeneratorError, require, write_or_check
from ValidateEngineeringMaterialsSource import load_and_validate


TOKENS = (
    "LIBRARY_METADATA", "DATA_DEFINITIONS", "SOURCE_AND_DATA", "MATERIAL_NAMES",
    "PROPERTY_NAMES", "PROPERTY_UNITS", "SOURCE_NAMES",
)


def _text(value: object) -> str:
    return str(value).strip()


def _calc_text(value: object) -> str:
    return _text(value).replace("'", "''")


def _number(value: object, missing: str) -> str:
    if pd.isna(value):
        return missing
    number = float(value)
    require(math.isfinite(number), "Generator received a non-finite numeric value after validation.")
    if number == 0:
        return "0"
    magnitude = abs(number)
    if magnitude >= 10**7 or magnitude < 10**-3:
        exponent = math.floor(math.log10(magnitude))
        mantissa = number / (10**exponent)
        return f"{format(mantissa, '.10g')}*10^{exponent}"
    rendered = format(number, ".10g")
    if "e" in rendered.lower():
        mantissa, exponent = rendered.lower().split("e")
        return f"{mantissa}*10^{int(exponent)}"
    return rendered


def _vector(values: list[object], missing: str = "DB_MISSING") -> str:
    return "[" + "; ".join(_number(value, missing) for value in values) + "]"


def _matrix(rows: list[list[object]], missing: str) -> str:
    return "[" + "|".join("; ".join(_number(value, missing) for value in row) for row in rows) + "]"


def _aliases(dataset: dict[str, object], alias_type: str, target: str) -> list[str]:
    aliases = dataset["aliases"]
    selected = aliases[
        aliases["Alias_Type"].astype(str).str.strip().eq(alias_type)
        & aliases["Target_Constant"].astype(str).str.strip().eq(target)
    ]
    return selected.sort_values("Sequence")["Alias_Constant"].astype(str).str.strip().tolist()


def _metadata(dataset: dict[str, object]) -> str:
    contract = dataset["contract"]
    return "\n".join((
        f"#def EngineeringMaterialsLibraryName$ = {_text(contract['Library_Name'])}",
        f"#def EngineeringMaterialsLibraryRevision$ = {_text(contract['Library_Revision'])}",
        f"#def EngineeringMaterialsLibraryDate$ = {_text(contract['Library_Date'])}",
        f"#def EngineeringMaterialsLibraryScope$ = {len(dataset['materials'])} common materials and {len(dataset['properties'])} nominal room-temperature screening properties with discovery, selection, comparison, classification, and provenance reporting.",
    ))


def _data_definitions(dataset: dict[str, object]) -> str:
    materials = dataset["materials"]
    properties = dataset["properties"]
    categories = dataset["categories"]
    lines: list[str] = []
    for _, row in materials.iterrows():
        target = _text(row["CPD_Constant"])
        lines.append(f"{target} = {int(row['Material_ID'])}")
        lines.extend(f"{alias} = {target}" for alias in _aliases(dataset, "Material", target))
        lines.append("")
    lines.append(f"EngineeringMaterialItemIDs = {_vector(materials['Material_ID'].tolist())}")
    lines.extend(("", "MAT_CAT_ALL = 0"))
    lines.extend(f"{_text(row['CPD_Constant'])} = {int(row['Category_ID'])}" for _, row in categories.iterrows())
    lines.extend((
        "",
        f"EngineeringMaterialCategoryIDs = {_vector(categories['Category_ID'].tolist())}",
        f"EngineeringMaterialCategoryByItem = {_vector(dataset['category_by_material'])}",
        "EngineeringMaterialCatalog = join_cols(EngineeringMaterialItemIDs; EngineeringMaterialCategoryByItem)",
        "EngineeringMaterialItemCount = len(EngineeringMaterialItemIDs)",
        "",
    ))
    for _, row in properties.iterrows():
        target = _text(row["CPD_Constant"])
        lines.append(f"{target} = {int(row['Property_ID'])}")
        lines.extend(f"{alias} = {target}" for alias in _aliases(dataset, "Property", target))
        lines.append("")
    lines.extend((
        f"EngineeringMaterialPropertyIDs = {_vector(properties['Property_ID'].tolist())}",
        "EngineeringMaterialPropertyCount = len(EngineeringMaterialPropertyIDs)",
    ))
    return "\n".join(lines)


def _source_and_data(dataset: dict[str, object]) -> str:
    contract = dataset["contract"]
    sources = dataset["sources"]
    materials = dataset["materials"]
    export = dataset["export"]
    missing = _text(contract["Missing_Value"])
    lines = [f"MAT_SRC_{int(source_id)} = {int(source_id)}" for source_id in sources["Source_ID"]]
    source_ids = sources["Source_ID"].astype(int).tolist()
    lines.extend((
        "",
        f"EngineeringMaterialSourceIDs = {_vector(source_ids)}",
        "MatSourceKnown(source_id) = DBHasID(EngineeringMaterialSourceIDs; source_id)",
        "",
    ))
    data_rows = export.values.tolist()
    lines.append(f"EngineeringMaterialData = {_matrix(data_rows, missing)}")
    revision = int(contract["Data_Revision"])
    metadata = [[int(row["Material_ID"]), int(row["Source_ID"]), revision] for _, row in materials.iterrows()]
    lines.append(f"EngineeringMaterialMetadata = {_matrix(metadata, missing)}")
    return "\n".join(lines)


def _lookup_macro(name: str, argument: str, rows: list[tuple[str, str]], known: str, error: str) -> str:
    lines = [f"#def {name}$({argument}$)"]
    for constant, display in rows:
        lines.extend((
            f"\t    #if {argument}$ ≡ {constant}",
            f"\t\t        '{_calc_text(display)}",
            "\t    #end if",
        ))
    lines.extend((
        f"\t    #if not({known}({argument}$))",
        f"\t\t        '<span class=\"err\">{error}</span>",
        "\t    #end if",
        "#end def",
    ))
    return "\n".join(lines)


def _material_names(dataset: dict[str, object]) -> str:
    rows = [(_text(row["CPD_Constant"]), _text(row["Material_Name"])) for _, row in dataset["materials"].iterrows()]
    return _lookup_macro("MatName", "item", rows, "MatHasItem", "Unknown material ID")


def _property_names(dataset: dict[str, object]) -> str:
    rows = [(_text(row["CPD_Constant"]), _text(row["Property_Name"])) for _, row in dataset["properties"].iterrows()]
    return _lookup_macro("MatPropertyName", "property", rows, "MatHasProperty", "Unknown material property ID")


def _property_units(dataset: dict[str, object]) -> str:
    rows = [(_text(row["CPD_Constant"]), _text(row["Unit"])) for _, row in dataset["properties"].iterrows()]
    return _lookup_macro("MatPropertyUnit", "property", rows, "MatHasProperty", "Unknown material property ID")


def _source_names(dataset: dict[str, object]) -> str:
    rows = [(f"MAT_SRC_{int(row['Source_ID'])}", f"{_text(row['Source_Name'])} — {_text(row['URL'])}") for _, row in dataset["sources"].iterrows()]
    return _lookup_macro("MatSource", "source_id", rows, "MatSourceKnown", "Unknown material source ID")


def generate_library(source: Path, template_path: Path) -> str:
    dataset = load_and_validate(source)
    require(template_path.is_file(), f"Engineering Materials template does not exist: {template_path}")
    template = template_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    replacements = {
        "LIBRARY_METADATA": _metadata(dataset), "DATA_DEFINITIONS": _data_definitions(dataset),
        "SOURCE_AND_DATA": _source_and_data(dataset), "MATERIAL_NAMES": _material_names(dataset),
        "PROPERTY_NAMES": _property_names(dataset), "PROPERTY_UNITS": _property_units(dataset),
        "SOURCE_NAMES": _source_names(dataset),
    }
    for token in TOKENS:
        marker = "{{" + token + "}}"
        require(template.count(marker) == 1, f"Template must contain exactly one {marker} token.")
        template = template.replace(marker, replacements[token])
    require("{{" not in template and "}}" not in template, "Template contains an unresolved generation token.")
    generated_notice = "'<!-- GENERATED FILE. Edit Data/Sources/EngineeringMaterials/EngineeringMaterialsDatabase.xlsx and run Tools/GenerateEngineeringMaterialsLibrary.py. -->\n"
    anchor = "'<!-- Common engineering materials library. Representative screening data; not design allowables. -->\n"
    require(anchor in template, "Engineering Materials template is missing its library description anchor.")
    return template.replace(anchor, anchor + generated_notice, 1).rstrip("\n") + "\n"


def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--template", type=Path, default=repository / "Tools" / "Templates" / "EngineeringMaterialsLibraryTemplate.cpd")
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    try:
        generated = generate_library(options.source, options.template)
        write_or_check(options.output, generated, options.check)
    except (GeneratorError, ValueError, TypeError) as error:
        print(f"Engineering Materials generation error: {error}", file=sys.stderr)
        return 1
    action = "Verified" if options.check else "Generated"
    print(f"{action} Engineering Materials library: {options.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
