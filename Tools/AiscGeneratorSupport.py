"""Shared validation for the repository-owned structural-section source workbook."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

from GeneratorSupport import GeneratorError, require


README_SHEET = "README"
PROPERTIES_SHEET = "Properties"
DATASET_ID = "DRAT_STRUCTURAL_SECTIONS"
DATASET_REVISION = "1.0.0"
SOURCE_REVISION = "AISC Shapes Database v16.0, August 2023"
LABEL_PATTERN = re.compile(r"^[A-Z0-9./X-]+$")
ALLOWED_UNITS = {"lb/ft", "in^2", "in", "in^3", "in^4", "in^6"}


def load_family(
    workbook: Path,
    sheet_name: str,
    families: Iterable[str],
    properties: list[tuple[str, str, str, str]],
    expected_counts: dict[str, int],
    first_id: int,
) -> pd.DataFrame:
    """Load one DRAT family sheet after validating its curated source contract."""

    require(workbook.is_file(), f"DRAT structural-section source workbook does not exist: {workbook}")
    try:
        with pd.ExcelFile(workbook, engine="openpyxl") as excel:
            for sheet in (README_SHEET, PROPERTIES_SHEET, sheet_name):
                require(sheet in excel.sheet_names, f"DRAT source workbook is missing worksheet '{sheet}'.")
            data = pd.read_excel(excel, sheet_name=sheet_name)
            property_contract = pd.read_excel(excel, sheet_name=PROPERTIES_SHEET)
            readme = pd.read_excel(excel, sheet_name=README_SHEET, header=None)
    except GeneratorError:
        raise
    except Exception as error:
        raise GeneratorError(f"Could not open or read DRAT structural-section source workbook {workbook}: {error}") from error

    required_columns = ["Section_ID", "Type", "AISC_Manual_Label", *(column for _, _, _, column in properties)]
    missing_columns = [column for column in required_columns if column not in data.columns]
    require(not missing_columns, f"DRAT family worksheet is missing required columns: {', '.join(missing_columns)}")
    require(len(required_columns) == len(set(required_columns)), "DRAT generator property columns must be unique.")
    unexpected_columns = [column for column in data.columns if column not in required_columns]
    require(not unexpected_columns, f"DRAT family worksheet contains unsupported columns: {', '.join(unexpected_columns)}")
    invalid_units = [unit for _, _, unit, _ in properties if unit not in ALLOWED_UNITS]
    if invalid_units:
        raise GeneratorError(f"DRAT generator contains unsupported unit mapping: {invalid_units[0]}")
    readme_text = "\n".join(str(value) for value in readme.to_numpy().flat if pd.notna(value))
    require(DATASET_ID in readme_text, f"DRAT source workbook does not identify dataset {DATASET_ID}.")
    require(DATASET_REVISION in readme_text, f"DRAT source workbook revision is not {DATASET_REVISION}.")
    require(SOURCE_REVISION in readme_text, "DRAT source workbook does not record the qualified AISC source basis.")

    expected_contract = pd.DataFrame(
        [
            {
                "Family": sheet_name,
                "Property ID": index,
                "CalcPad code": code,
                "Property name": name,
                "Unit": unit,
                "Source column": column,
                "Required": "Yes" if code in {"WEIGHT", "AREA"} else "No",
            }
            for index, (code, name, unit, column) in enumerate(properties, 1)
        ]
    )
    actual_contract = property_contract[property_contract["Family"].eq(sheet_name)].reset_index(drop=True)
    require(
        actual_contract.equals(expected_contract),
        f"DRAT Properties contract for {sheet_name} does not match the generator API.",
    )

    family_names = list(families)
    sections = data.copy().reset_index(drop=True)
    require(sections["Type"].isin(family_names).all(), f"{sheet_name} contains an unsupported shape family.")
    for family, expected in expected_counts.items():
        actual = int(sections["Type"].eq(family).sum())
        require(actual == expected, f"Expected {expected} {family} records; found {actual}.")
    require(len(sections) == sum(expected_counts.values()), "DRAT family record total is inconsistent.")

    ids = pd.to_numeric(sections["Section_ID"], errors="coerce")
    require(ids.notna().all(), "Section_ID contains a non-numeric value.")
    require((ids % 1 == 0).all(), "Section_ID values must be integers.")
    expected_ids = pd.Series(range(first_id, first_id + len(sections)), dtype="int64")
    require(ids.astype("int64").equals(expected_ids), "Section_ID values must be unique, ordered, and contiguous.")

    labels = sections["AISC_Manual_Label"]
    require(labels.notna().all(), "AISC_Manual_Label contains a missing value.")
    normalized_labels = labels.astype(str).str.strip()
    require((normalized_labels == labels.astype(str)).all(), "AISC_Manual_Label contains surrounding whitespace.")
    require(normalized_labels.is_unique, "AISC_Manual_Label values must be unique within a generated library.")
    invalid_labels = [label for label in normalized_labels if LABEL_PATTERN.fullmatch(label) is None]
    if invalid_labels:
        raise GeneratorError(f"AISC_Manual_Label contains unsupported text: {invalid_labels[0]}")

    for code, _, _, column in properties:
        numeric = pd.to_numeric(sections[column].replace({"–": None, "-": None}), errors="coerce")
        invalid = sections[column].notna() & ~sections[column].astype(str).str.strip().isin(["–", "-"]) & numeric.isna()
        require(not invalid.any(), f"AISC property column '{column}' contains a non-numeric value.")
        finite = numeric.dropna().map(lambda value: math.isfinite(float(value)))
        require(bool(finite.all()), f"AISC property column '{column}' contains a non-finite value.")
        if code in {"WEIGHT", "AREA"}:
            require(numeric.notna().all(), f"Required AISC property column '{column}' contains a missing value.")
            require((numeric > 0).all(), f"Required AISC property column '{column}' must be positive.")

    return sections
