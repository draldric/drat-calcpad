"""Validate the complete Engineering Materials workbook contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from GeneratorSupport import GeneratorError, require
from WorkbookDatasetSupport import (
    ISO_DATE, SEMANTIC_VERSION, mapping_sheet, numeric_or_blank, read_workbook,
    require_columns, require_constants, require_contiguous, require_symbols, unique_positive_integer_ids,
)


CONTRACT_SHEET = "Dataset Contract"
CONTRACT_KEYS = (
    "Dataset_ID", "Schema_Version", "Library_Name", "Library_Revision", "Library_Date",
    "Records_Sheet", "Properties_Sheet", "Sources_Sheet", "Aliases_Sheet", "Categories_Sheet",
    "Export_Sheet", "Missing_Value", "Classification", "Data_Revision",
)
MATERIAL_COLUMNS = (
    "Material_ID", "CPD_Constant", "Material_Name", "Family", "Category", "Standard_or_Grade",
    "Condition", "Elastic_Model", "Density_kg_m3", "Youngs_Modulus_GPa", "Poisson_Ratio",
    "Shear_Override_GPa", "Bulk_Override_GPa", "Shear_Modulus_GPa_Derived",
    "Bulk_Modulus_GPa_Derived", "Yield_Strength_MPa", "Tensile_Strength_MPa",
    "Compressive_Strength_MPa", "Flexural_Strength_MPa", "Elongation_Fraction",
    "Fracture_Toughness_MPa_sqrt_m", "Thermal_Conductivity_W_mK", "Specific_Heat_J_kgK",
    "CTE_um_mK", "Electrical_Resistivity_ohm_m", "Transition_Temperature_C",
    "Max_Service_Temperature_C", "Hardness_HV", "Source_ID", "Data_Quality", "Notes",
    "Source_URL", "Duplicate_ID_Flag",
)
PROPERTY_COLUMNS = (
    "Property_ID", "CPD_Constant", "Property_Name", "Unit", "CPD_Export_Header", "Definition",
    "Missing_Value_Behavior", "Materials_Source_Column",
)
SOURCE_COLUMNS = ("Source_ID", "Source_Name", "Coverage", "Use_in_Library", "URL")
CATEGORY_COLUMNS = ("Category_ID", "CPD_Constant", "Category_Name", "Family", "Category_Override")
ALIAS_COLUMNS = ("Alias_Type", "Sequence", "Alias_Constant", "Target_Constant")


def _text(value: object) -> str:
    return str(value).strip()


def _category_for(row: pd.Series, categories: pd.DataFrame) -> int:
    family = _text(row["Family"])
    category = _text(row["Category"])
    family_rows = categories[categories["Family"].astype(str).str.strip().eq(family)]
    override = family_rows[family_rows["Category_Override"].fillna("").astype(str).str.strip().eq(category)]
    if len(override) == 1:
        return int(override.iloc[0]["Category_ID"])
    fallback = family_rows[family_rows["Category_Override"].fillna("").astype(str).str.strip().eq("")]
    require(len(fallback) == 1, f"Material family/category does not resolve to exactly one runtime category: {family} / {category}")
    return int(fallback.iloc[0]["Category_ID"])


def load_and_validate(path: Path) -> dict[str, object]:
    """Validate every workbook-owned input before generation starts."""

    contract_frame = read_workbook(path, (CONTRACT_SHEET,))[CONTRACT_SHEET]
    contract = mapping_sheet(contract_frame, "Key", "Value", CONTRACT_SHEET)
    missing_keys = [key for key in CONTRACT_KEYS if key not in contract]
    require(not missing_keys, f"Dataset Contract is missing keys: {', '.join(missing_keys)}")
    require(_text(contract["Dataset_ID"]) == "DRAT_ENGINEERING_MATERIALS", "Dataset Contract has the wrong Dataset_ID.")
    require(SEMANTIC_VERSION.fullmatch(_text(contract["Schema_Version"])) is not None, "Schema_Version must use semantic versioning.")
    require(SEMANTIC_VERSION.fullmatch(_text(contract["Library_Revision"])) is not None, "Library_Revision must use semantic versioning.")
    require(ISO_DATE.fullmatch(_text(contract["Library_Date"])) is not None, "Library_Date must use YYYY-MM-DD.")
    require(float(contract["Data_Revision"]).is_integer() and int(contract["Data_Revision"]) > 0, "Data_Revision must be a positive integer.")

    names = [
        CONTRACT_SHEET, "README", _text(contract["Records_Sheet"]), _text(contract["Properties_Sheet"]),
        _text(contract["Sources_Sheet"]), _text(contract["Aliases_Sheet"]), _text(contract["Categories_Sheet"]),
        _text(contract["Export_Sheet"]), "Selector", "QA",
    ]
    require(len(names) == len(set(names)), "Dataset Contract worksheet names must be unique.")
    sheets = read_workbook(path, names)
    materials = sheets[_text(contract["Records_Sheet"])].copy()
    properties = sheets[_text(contract["Properties_Sheet"])].copy()
    sources = sheets[_text(contract["Sources_Sheet"])].copy()
    aliases = sheets[_text(contract["Aliases_Sheet"])].copy()
    categories = sheets[_text(contract["Categories_Sheet"])].copy()
    export = sheets[_text(contract["Export_Sheet"])].copy()

    require_columns(materials, MATERIAL_COLUMNS, "Materials")
    require_columns(properties, PROPERTY_COLUMNS, "Property Dictionary")
    require_columns(sources, SOURCE_COLUMNS, "Sources")
    require_columns(categories, CATEGORY_COLUMNS, "Categories")
    require_columns(aliases, ALIAS_COLUMNS, "Aliases")
    material_ids = unique_positive_integer_ids(materials["Material_ID"], "material IDs")
    property_ids = unique_positive_integer_ids(properties["Property_ID"], "property IDs")
    source_ids = unique_positive_integer_ids(sources["Source_ID"], "source IDs")
    category_ids = unique_positive_integer_ids(categories["Category_ID"], "category IDs")
    require_contiguous(property_ids, "Property IDs")
    require_contiguous(category_ids, "Category IDs")

    material_constants = require_constants(materials["CPD_Constant"], "Material CPD constants")
    property_constants = require_constants(properties["CPD_Constant"], "Property CPD constants")
    category_constants = require_constants(categories["CPD_Constant"], "Category CPD constants")
    alias_constants = require_symbols(aliases["Alias_Constant"], "Alias constants")
    all_primary = set(material_constants + property_constants + category_constants)
    require(not (set(alias_constants) & all_primary), "Alias constants must not collide with primary constants.")
    for alias_type, allowed in (("Material", set(material_constants)), ("Property", set(property_constants))):
        subset = aliases[aliases["Alias_Type"].astype(str).str.strip().eq(alias_type)]
        require(len(subset) > 0, f"Aliases must contain at least one {alias_type} alias.")
        sequences = unique_positive_integer_ids(subset["Sequence"], f"{alias_type} alias sequences")
        require_contiguous(sequences, f"{alias_type} alias sequences")
        require(set(subset["Target_Constant"].astype(str).str.strip()).issubset(allowed), f"{alias_type} alias targets must reference {alias_type.lower()} constants.")
    require(set(aliases["Alias_Type"].astype(str).str.strip()) == {"Material", "Property"}, "Alias_Type must be Material or Property.")

    require(set(materials["Source_ID"].astype(int)).issubset(source_ids), "Materials contains an unknown Source_ID.")
    source_urls = dict(zip(sources["Source_ID"].astype(int), sources["URL"].astype(str)))
    for _, row in materials.iterrows():
        require(_text(row["Source_URL"]) == _text(source_urls[int(row["Source_ID"])]), f"Material {int(row['Material_ID'])} Source_URL does not match Sources.")
    require(set(materials["Data_Quality"].astype(str)).issubset({"Representative", "Approximate"}), "Data_Quality contains an unsupported classification.")

    ordered_properties = properties.sort_values("Property_ID").reset_index(drop=True)
    source_columns = ordered_properties["Materials_Source_Column"].astype(str).str.strip().tolist()
    require(len(source_columns) == len(set(source_columns)), "Materials source property columns must be unique.")
    require_columns(materials, source_columns, "Materials")
    numeric_materials = {column: numeric_or_blank(materials[column], f"Materials.{column}") for column in source_columns}
    isotropic = materials["Elastic_Model"].eq("Isotropic")
    derived_shear = materials["Youngs_Modulus_GPa"] / (2 * (1 + materials["Poisson_Ratio"]))
    derived_bulk = materials["Youngs_Modulus_GPa"] / (3 * (1 - 2 * materials["Poisson_Ratio"]))
    expected_shear = materials["Shear_Override_GPa"].where(materials["Shear_Override_GPa"].notna(), derived_shear.where(isotropic))
    expected_bulk = materials["Bulk_Override_GPa"].where(materials["Bulk_Override_GPa"].notna(), derived_bulk.where(isotropic))
    for actual, expected, label in ((materials["Shear_Modulus_GPa_Derived"], expected_shear, "shear"), (materials["Bulk_Modulus_GPa_Derived"], expected_bulk, "bulk")):
        equal = (actual.isna() & expected.isna()) | ((actual - expected).abs() < 1e-10)
        require(equal.all(), f"Derived {label} modulus values are inconsistent with E, Poisson ratio, or override.")

    export_headers = ["Material_ID", *ordered_properties["CPD_Export_Header"].astype(str)]
    require(list(export.columns) == export_headers, "CPD Numeric Export columns do not match Property Dictionary order.")
    materials_by_id = materials.sort_values("Material_ID").reset_index(drop=True)
    export_by_id = export.sort_values("Material_ID").reset_index(drop=True)
    require(export_by_id["Material_ID"].astype(int).tolist() == sorted(material_ids), "CPD Numeric Export material IDs do not match Materials.")
    for header, column in zip(export_headers[1:], source_columns):
        exported = numeric_or_blank(export_by_id[header], f"CPD Numeric Export.{header}")
        sourced = numeric_or_blank(materials_by_id[column], f"Materials.{column}")
        equal = (exported.isna() & sourced.isna()) | ((exported - sourced).abs() < 1e-10)
        require(equal.all(), f"CPD Numeric Export.{header} does not match Materials.{column}.")

    categories["Category_ID"] = categories["Category_ID"].astype(int)
    category_by_material = [_category_for(row, categories) for _, row in materials_by_id.iterrows()]
    populated = int(sum(series.notna().sum() for series in numeric_materials.values()))
    return {
        "contract": contract, "materials": materials_by_id, "properties": ordered_properties,
        "sources": sources.sort_values("Source_ID").reset_index(drop=True),
        "aliases": aliases.sort_values(["Alias_Type", "Sequence"]).reset_index(drop=True),
        "categories": categories.sort_values("Category_ID").reset_index(drop=True), "export": export_by_id,
        "category_by_material": category_by_material, "populated_values": populated,
    }


def validate_workbook(path: Path) -> dict[str, int | str]:
    dataset = load_and_validate(path)
    return {
        "revision": _text(dataset["contract"]["Library_Revision"]),
        "revision_date": _text(dataset["contract"]["Library_Date"]),
        "materials": len(dataset["materials"]), "properties": len(dataset["properties"]),
        "sources": len(dataset["sources"]), "populated_values": int(dataset["populated_values"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Engineering Materials source workbook.")
    options = parser.parse_args()
    try:
        summary = validate_workbook(options.source)
    except (GeneratorError, ValueError, TypeError) as error:
        print(f"Engineering Materials source error: {error}", file=sys.stderr)
        return 1
    print(f"Validated Engineering Materials source: revision {summary['revision']}, {summary['materials']} materials, {summary['properties']} properties, {summary['populated_values']} populated values.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
