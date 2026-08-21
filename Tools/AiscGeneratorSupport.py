"""Shared AISC v16 workbook validation for structural-section generators."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

from GeneratorSupport import GeneratorError, require


DATABASE_SHEET = "Database v16.0"
README_SHEET = "Readme"
SOURCE_REVISION = "AISC Shapes Database v16.0, August 2023"
LABEL_PATTERN = re.compile(r"^[A-Z0-9./X-]+$")
ALLOWED_UNITS = {"lb/ft", "in^2", "in", "in^3", "in^4", "in^6"}


def load_family(
    workbook: Path,
    families: Iterable[str],
    properties: list[tuple[str, str, str, str]],
    expected_counts: dict[str, int],
) -> pd.DataFrame:
    """Load one or more AISC families after validating the official workbook schema."""

    require(workbook.is_file(), f"AISC source workbook does not exist: {workbook}")
    try:
        with pd.ExcelFile(workbook, engine="openpyxl") as excel:
            for sheet in (DATABASE_SHEET, README_SHEET):
                require(sheet in excel.sheet_names, f"AISC source workbook is missing worksheet '{sheet}'.")
            data = pd.read_excel(excel, sheet_name=DATABASE_SHEET)
            readme = pd.read_excel(excel, sheet_name=README_SHEET, header=None)
    except GeneratorError:
        raise
    except Exception as error:
        raise GeneratorError(f"Could not open or read AISC source workbook {workbook}: {error}") from error

    required_columns = ["Type", "AISC_Manual_Label", *(column for _, _, _, column in properties)]
    missing_columns = [column for column in required_columns if column not in data.columns]
    require(not missing_columns, f"AISC worksheet is missing required columns: {', '.join(missing_columns)}")
    require(len(required_columns) == len(set(required_columns)), "AISC generator property columns must be unique.")
    invalid_units = [unit for _, _, unit, _ in properties if unit not in ALLOWED_UNITS]
    if invalid_units:
        raise GeneratorError(f"AISC generator contains unsupported unit mapping: {invalid_units[0]}")
    readme_text = "\n".join(str(value) for value in readme.to_numpy().flat if pd.notna(value))
    require("AISC Shapes Database v16.0" in readme_text, "AISC source revision is not v16.0.")
    require("August 2023" in readme_text, "AISC source revision date is not August 2023.")

    family_names = list(families)
    sections = data[data["Type"].isin(family_names)].copy().reset_index(drop=True)
    for family, expected in expected_counts.items():
        actual = int(sections["Type"].eq(family).sum())
        require(actual == expected, f"Expected {expected} {family} records; found {actual}.")
    require(len(sections) == sum(expected_counts.values()), "AISC family record total is inconsistent.")

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
