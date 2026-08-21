"""Validate the Engineering Materials workbook and its CalcPad numeric export."""

from __future__ import annotations

import argparse
import math
import re
import sys
import warnings
from pathlib import Path

import pandas as pd

from GeneratorSupport import GeneratorError, require


REQUIRED_SHEETS = (
    "README",
    "Materials",
    "Property Dictionary",
    "Sources",
    "CPD Numeric Export",
    "Selector",
    "QA",
)
MATERIAL_COLUMNS = (
    "Material_ID",
    "CPD_Constant",
    "Material_Name",
    "Family",
    "Category",
    "Standard_or_Grade",
    "Condition",
    "Elastic_Model",
    "Density_kg_m3",
    "Youngs_Modulus_GPa",
    "Poisson_Ratio",
    "Shear_Override_GPa",
    "Bulk_Override_GPa",
    "Shear_Modulus_GPa_Derived",
    "Bulk_Modulus_GPa_Derived",
    "Yield_Strength_MPa",
    "Tensile_Strength_MPa",
    "Compressive_Strength_MPa",
    "Flexural_Strength_MPa",
    "Elongation_Fraction",
    "Fracture_Toughness_MPa_sqrt_m",
    "Thermal_Conductivity_W_mK",
    "Specific_Heat_J_kgK",
    "CTE_um_mK",
    "Electrical_Resistivity_ohm_m",
    "Transition_Temperature_C",
    "Max_Service_Temperature_C",
    "Hardness_HV",
    "Source_ID",
    "Data_Quality",
    "Notes",
    "Source_URL",
    "Duplicate_ID_Flag",
)
PROPERTY_COLUMNS = (
    "Property_ID",
    "CPD_Constant",
    "Property_Name",
    "Unit",
    "CPD_Export_Header",
    "Definition",
    "Missing_Value_Behavior",
)
SOURCE_COLUMNS = ("Source_ID", "Source_Name", "Coverage", "Use_in_Library", "URL")
CPD_CONSTANT = re.compile(r"^[A-Z][A-Z0-9_]*$")
SEMANTIC_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def read_sheets(path: Path) -> dict[str, pd.DataFrame]:
    """Read every required worksheet after checking workbook identity."""

    require(path.is_file(), f"Engineering Materials source workbook does not exist: {path}")
    try:
        with pd.ExcelFile(path, engine="openpyxl") as workbook:
            for sheet in REQUIRED_SHEETS:
                require(sheet in workbook.sheet_names, f"Engineering Materials workbook is missing worksheet '{sheet}'.")
            return {sheet: pd.read_excel(workbook, sheet_name=sheet) for sheet in REQUIRED_SHEETS}
    except GeneratorError:
        raise
    except Exception as error:
        raise GeneratorError(f"Could not read Engineering Materials workbook {path}: {error}") from error


def require_columns(frame: pd.DataFrame, required: tuple[str, ...], sheet: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    require(not missing, f"Worksheet '{sheet}' is missing required columns: {', '.join(missing)}")


def require_unique_integer_ids(series: pd.Series, label: str, expected_count: int) -> list[int]:
    numeric = pd.to_numeric(series, errors="coerce")
    require(len(numeric) == expected_count, f"Expected {expected_count} {label}; found {len(numeric)}.")
    require(numeric.notna().all(), f"{label} must be numeric.")
    require(numeric.map(lambda value: float(value).is_integer()).all(), f"{label} must be integers.")
    values = [int(value) for value in numeric]
    require(len(values) == len(set(values)), f"{label} must be unique.")
    require(all(value > 0 for value in values), f"{label} must be positive.")
    return values


def require_numeric_or_blank(series: pd.Series, label: str) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    invalid = series.notna() & numeric.isna()
    require(not invalid.any(), f"{label} contains a non-numeric populated value.")
    require(numeric.dropna().map(lambda value: math.isfinite(float(value))).all(), f"{label} contains a non-finite value.")
    return numeric


def validate_dataset(sheets: dict[str, pd.DataFrame]) -> dict[str, int | str]:
    """Validate workbook schema, IDs, derived values, export order, and sources."""

    readme = sheets["README"]
    materials = sheets["Materials"]
    properties = sheets["Property Dictionary"]
    sources = sheets["Sources"]
    export = sheets["CPD Numeric Export"]
    require_columns(materials, MATERIAL_COLUMNS, "Materials")
    require_columns(properties, PROPERTY_COLUMNS, "Property Dictionary")
    require_columns(sources, SOURCE_COLUMNS, "Sources")

    readme_map = {
        str(row.iloc[0]).strip(): str(row.iloc[1]).strip()
        for _, row in readme.iloc[:, :2].dropna(how="any").iterrows()
    }
    revision = readme_map.get("Library revision", "")
    revision_date = readme_map.get("Revision date", "")
    require(SEMANTIC_VERSION.fullmatch(revision) is not None, "README Library revision must use numeric semantic versioning.")
    require(DATE.fullmatch(revision_date) is not None, "README Revision date must use YYYY-MM-DD.")

    material_ids = require_unique_integer_ids(materials["Material_ID"], "material IDs", 126)
    property_ids = require_unique_integer_ids(properties["Property_ID"], "property IDs", 18)
    source_ids = require_unique_integer_ids(sources["Source_ID"], "source IDs", 11)
    require(property_ids == list(range(1, 19)), "Property IDs must remain the stable sequence 1 through 18.")

    for label, frame in (("material", materials), ("property", properties)):
        constants = frame["CPD_Constant"].astype(str)
        require(constants.is_unique, f"{label.title()} CPD constants must be unique.")
        invalid = [value for value in constants if CPD_CONSTANT.fullmatch(value) is None]
        if invalid:
            raise GeneratorError(f"{label.title()} CPD constant is invalid: {invalid[0]}")

    require(set(materials["Source_ID"].astype(int)).issubset(source_ids), "Materials contains an unknown Source_ID.")
    source_urls = dict(zip(sources["Source_ID"].astype(int), sources["URL"].astype(str)))
    for _, row in materials.iterrows():
        require(str(row["Source_URL"]) == source_urls[int(row["Source_ID"])], f"Material {int(row['Material_ID'])} Source_URL does not match Sources.")
    allowed_quality = {"Representative", "Approximate"}
    require(set(materials["Data_Quality"].astype(str)).issubset(allowed_quality), "Data_Quality contains an unsupported classification.")

    property_source_columns = [
        "Density_kg_m3",
        "Youngs_Modulus_GPa",
        "Shear_Modulus_GPa_Derived",
        "Poisson_Ratio",
        "Yield_Strength_MPa",
        "Tensile_Strength_MPa",
        "Compressive_Strength_MPa",
        "Flexural_Strength_MPa",
        "Elongation_Fraction",
        "Fracture_Toughness_MPa_sqrt_m",
        "Thermal_Conductivity_W_mK",
        "Specific_Heat_J_kgK",
        "CTE_um_mK",
        "Electrical_Resistivity_ohm_m",
        "Transition_Temperature_C",
        "Max_Service_Temperature_C",
        "Hardness_HV",
        "Bulk_Modulus_GPa_Derived",
    ]
    numeric_materials = {column: require_numeric_or_blank(materials[column], f"Materials.{column}") for column in property_source_columns}

    isotropic = materials["Elastic_Model"].eq("Isotropic")
    derived_shear = materials["Youngs_Modulus_GPa"] / (2 * (1 + materials["Poisson_Ratio"]))
    derived_bulk = materials["Youngs_Modulus_GPa"] / (3 * (1 - 2 * materials["Poisson_Ratio"]))
    shear_expected = materials["Shear_Override_GPa"].where(materials["Shear_Override_GPa"].notna(), derived_shear.where(isotropic))
    bulk_expected = materials["Bulk_Override_GPa"].where(materials["Bulk_Override_GPa"].notna(), derived_bulk.where(isotropic))
    actual_shear = materials["Shear_Modulus_GPa_Derived"]
    actual_bulk = materials["Bulk_Modulus_GPa_Derived"]
    shear_equal = (actual_shear.isna() & shear_expected.isna()) | ((actual_shear - shear_expected).abs() < 1e-10)
    bulk_equal = (actual_bulk.isna() & bulk_expected.isna()) | ((actual_bulk - bulk_expected).abs() < 1e-10)
    require(shear_equal.all(), "Derived shear modulus values are inconsistent with E, Poisson ratio, or override.")
    require(bulk_equal.all(), "Derived bulk modulus values are inconsistent with E, Poisson ratio, or override.")

    expected_export_headers = ["Material_ID", *properties.sort_values("Property_ID")["CPD_Export_Header"].astype(str)]
    require(list(export.columns) == expected_export_headers, "CPD Numeric Export columns do not match Property Dictionary order.")
    require(list(export["Material_ID"].astype(int)) == material_ids, "CPD Numeric Export material IDs do not match Materials order.")
    for export_column, source_column in zip(expected_export_headers[1:], property_source_columns):
        export_values = require_numeric_or_blank(export[export_column], f"CPD Numeric Export.{export_column}")
        source_values = numeric_materials[source_column]
        equal = (export_values.isna() & source_values.isna()) | ((export_values - source_values).abs() < 1e-10)
        require(equal.all(), f"CPD Numeric Export.{export_column} does not match Materials.{source_column}.")

    available = int(sum(series.notna().sum() for series in numeric_materials.values()))
    require(available == 2011, f"Expected 2,011 populated material-property values; found {available}.")
    return {
        "revision": revision,
        "revision_date": revision_date,
        "materials": len(material_ids),
        "properties": len(property_ids),
        "sources": len(source_ids),
        "populated_values": available,
    }


def validate_workbook(path: Path) -> dict[str, int | str]:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Unknown extension is not supported and will be removed")
        warnings.filterwarnings("ignore", message="Conditional Formatting extension is not supported and will be removed")
        return validate_dataset(read_sheets(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Engineering Materials source workbook.")
    options = parser.parse_args()
    try:
        summary = validate_workbook(options.source)
    except GeneratorError as error:
        print(f"Engineering Materials source error: {error}", file=sys.stderr)
        return 1
    print(
        "Validated Engineering Materials source: "
        f"revision {summary['revision']}, {summary['materials']} materials, "
        f"{summary['properties']} properties, {summary['populated_values']} populated values."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
