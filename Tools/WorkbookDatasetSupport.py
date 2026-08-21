"""Schema-driven validation primitives shared by workbook-backed generators."""

from __future__ import annotations

import math
import re
import warnings
from pathlib import Path
from typing import Iterable

import pandas as pd

from GeneratorSupport import GeneratorError, require


CPD_CONSTANT = re.compile(r"^[A-Z][A-Z0-9_]*$")
CALCPAD_SYMBOL = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
SEMANTIC_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def read_workbook(path: Path, required_sheets: Iterable[str]) -> dict[str, pd.DataFrame]:
    required = tuple(required_sheets)
    require(path.is_file(), f"Source workbook does not exist: {path}")
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Unknown extension is not supported and will be removed")
            warnings.filterwarnings("ignore", message="Conditional Formatting extension is not supported and will be removed")
            with pd.ExcelFile(path, engine="openpyxl") as workbook:
                for sheet in required:
                    require(sheet in workbook.sheet_names, f"Source workbook is missing worksheet '{sheet}'.")
                return {sheet: pd.read_excel(workbook, sheet_name=sheet) for sheet in required}
    except GeneratorError:
        raise
    except Exception as error:
        raise GeneratorError(f"Could not read source workbook {path}: {error}") from error


def mapping_sheet(frame: pd.DataFrame, key_column: str, value_column: str, label: str) -> dict[str, object]:
    require_columns(frame, (key_column, value_column), label)
    rows = frame[[key_column, value_column]].dropna(how="any")
    keys = rows[key_column].astype(str).str.strip()
    require((keys != "").all(), f"{label} contains a blank key.")
    require(keys.is_unique, f"{label} keys must be unique.")
    return dict(zip(keys, rows[value_column]))


def require_columns(frame: pd.DataFrame, required: Iterable[str], sheet: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    require(not missing, f"Worksheet '{sheet}' is missing required columns: {', '.join(missing)}")


def unique_positive_integer_ids(series: pd.Series, label: str) -> list[int]:
    require(len(series) > 0, f"{label} must contain at least one value.")
    numeric = pd.to_numeric(series, errors="coerce")
    require(numeric.notna().all(), f"{label} must be numeric.")
    require(numeric.map(lambda value: float(value).is_integer()).all(), f"{label} must be integers.")
    values = [int(value) for value in numeric]
    require(len(values) == len(set(values)), f"{label} must be unique.")
    require(all(value > 0 for value in values), f"{label} must be positive.")
    return values


def require_contiguous(values: list[int], label: str, first: int = 1) -> None:
    require(sorted(values) == list(range(first, first + len(values))), f"{label} must be contiguous from {first}.")


def require_constants(series: pd.Series, label: str) -> list[str]:
    constants = series.astype(str).str.strip()
    require((constants != "").all(), f"{label} contains a blank constant.")
    require(constants.is_unique, f"{label} must be unique.")
    invalid = [value for value in constants if CPD_CONSTANT.fullmatch(value) is None]
    require(not invalid, f"{label} contains an invalid CalcPad constant: {invalid[0] if invalid else ''}")
    return constants.tolist()


def require_symbols(series: pd.Series, label: str) -> list[str]:
    symbols = series.astype(str).str.strip()
    require((symbols != "").all(), f"{label} contains a blank symbol.")
    require(symbols.is_unique, f"{label} must be unique.")
    invalid = [value for value in symbols if CALCPAD_SYMBOL.fullmatch(value) is None]
    require(not invalid, f"{label} contains an invalid CalcPad symbol: {invalid[0] if invalid else ''}")
    return symbols.tolist()


def numeric_or_blank(series: pd.Series, label: str) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    invalid = series.notna() & numeric.isna()
    require(not invalid.any(), f"{label} contains a non-numeric populated value.")
    require(numeric.dropna().map(lambda value: math.isfinite(float(value))).all(), f"{label} contains a non-finite value.")
    return numeric
