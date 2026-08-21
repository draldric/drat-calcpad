"""Regression tests for Engineering Materials source-workbook validation."""

from __future__ import annotations

import importlib
import sys
import unittest
import warnings
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "Tools"))
sys.dont_write_bytecode = True
VALIDATOR = importlib.import_module("ValidateEngineeringMaterialsSource")
SUPPORT = importlib.import_module("GeneratorSupport")
SOURCE = REPOSITORY_ROOT / "Data" / "Sources" / "EngineeringMaterials" / "EngineeringMaterialsDatabase.xlsx"


class EngineeringMaterialsSourceTests(unittest.TestCase):
    """Reject silent ID, type, provenance, and export drift."""

    @classmethod
    def setUpClass(cls) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            cls.source_sheets = VALIDATOR.read_sheets(SOURCE)

    def sheets(self):
        return {name: frame.copy(deep=True) for name, frame in self.source_sheets.items()}

    def test_committed_workbook_passes(self) -> None:
        summary = VALIDATOR.validate_dataset(self.sheets())
        self.assertEqual(summary["materials"], 126)
        self.assertEqual(summary["properties"], 18)
        self.assertEqual(summary["populated_values"], 2011)

    def test_duplicate_material_id_is_rejected(self) -> None:
        sheets = self.sheets()
        sheets["Materials"].loc[1, "Material_ID"] = sheets["Materials"].loc[0, "Material_ID"]
        with self.assertRaisesRegex(SUPPORT.GeneratorError, "material IDs must be unique"):
            VALIDATOR.validate_dataset(sheets)

    def test_non_numeric_property_is_rejected(self) -> None:
        sheets = self.sheets()
        sheets["Materials"]["Density_kg_m3"] = sheets["Materials"]["Density_kg_m3"].astype(object)
        sheets["Materials"].loc[0, "Density_kg_m3"] = "invalid"
        with self.assertRaisesRegex(SUPPORT.GeneratorError, "non-numeric"):
            VALIDATOR.validate_dataset(sheets)

    def test_numeric_export_drift_is_rejected(self) -> None:
        sheets = self.sheets()
        sheets["CPD Numeric Export"].loc[0, "P01_Density_kg_m3"] += 1
        with self.assertRaisesRegex(SUPPORT.GeneratorError, "does not match"):
            VALIDATOR.validate_dataset(sheets)

    def test_source_url_drift_is_rejected(self) -> None:
        sheets = self.sheets()
        sheets["Materials"].loc[0, "Source_URL"] = "https://example.invalid/"
        with self.assertRaisesRegex(SUPPORT.GeneratorError, "Source_URL does not match"):
            VALIDATOR.validate_dataset(sheets)

    def test_derived_modulus_drift_is_rejected(self) -> None:
        sheets = self.sheets()
        sheets["Materials"].loc[0, "Shear_Modulus_GPa_Derived"] += 1
        with self.assertRaisesRegex(SUPPORT.GeneratorError, "Derived shear modulus"):
            VALIDATOR.validate_dataset(sheets)


if __name__ == "__main__":
    unittest.main()
