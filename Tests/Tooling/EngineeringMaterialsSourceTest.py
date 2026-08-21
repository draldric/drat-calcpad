"""Regression tests for workbook-driven Engineering Materials generation."""

from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPOSITORY_ROOT / "Tools"
sys.path.insert(0, str(TOOLS))
sys.dont_write_bytecode = True
VALIDATOR = importlib.import_module("ValidateEngineeringMaterialsSource")
GENERATOR = importlib.import_module("GenerateEngineeringMaterialsLibrary")
SUPPORT = importlib.import_module("GeneratorSupport")
SOURCE = REPOSITORY_ROOT / "Data/Sources/EngineeringMaterials/EngineeringMaterialsDatabase.xlsx"
TEMPLATE = REPOSITORY_ROOT / "Tools/Templates/EngineeringMaterialsLibraryTemplate.cpd"
LIBRARY = REPOSITORY_ROOT / "Libraries/Materials/EngineeringMaterials.cpd"


class EngineeringMaterialsSourceTests(unittest.TestCase):
    """Reject drift and prove record maintenance does not require code changes."""

    @classmethod
    def setUpClass(cls) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with pd.ExcelFile(SOURCE, engine="openpyxl") as workbook:
                cls.source_sheets = {name: pd.read_excel(workbook, sheet_name=name) for name in workbook.sheet_names}

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.workbook = self.root / "EngineeringMaterialsDatabase.xlsx"
        self.frames = {name: frame.copy(deep=True) for name, frame in self.source_sheets.items()}

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_workbook(self) -> None:
        with pd.ExcelWriter(self.workbook, engine="openpyxl") as writer:
            for name, frame in self.frames.items():
                frame.to_excel(writer, sheet_name=name, index=False)

    def test_committed_workbook_passes_and_reproduces_library(self) -> None:
        summary = VALIDATOR.validate_workbook(SOURCE)
        self.assertEqual(summary["materials"], 126)
        self.assertEqual(summary["properties"], 18)
        self.assertEqual(summary["populated_values"], 2011)
        self.assertEqual(GENERATOR.generate_library(SOURCE, TEMPLATE), LIBRARY.read_text(encoding="utf-8"))

    def test_duplicate_material_id_is_rejected(self) -> None:
        self.frames["Materials"].loc[1, "Material_ID"] = self.frames["Materials"].loc[0, "Material_ID"]
        self.write_workbook()
        with self.assertRaisesRegex(SUPPORT.GeneratorError, "material IDs must be unique"):
            VALIDATOR.load_and_validate(self.workbook)

    def test_non_numeric_property_is_rejected(self) -> None:
        self.frames["Materials"]["Density_kg_m3"] = self.frames["Materials"]["Density_kg_m3"].astype(object)
        self.frames["Materials"].loc[0, "Density_kg_m3"] = "invalid"
        self.write_workbook()
        with self.assertRaisesRegex(SUPPORT.GeneratorError, "non-numeric"):
            VALIDATOR.load_and_validate(self.workbook)

    def test_numeric_export_drift_is_rejected(self) -> None:
        self.frames["CPD Numeric Export"].loc[0, "P01_Density_kg_m3"] += 1
        self.write_workbook()
        with self.assertRaisesRegex(SUPPORT.GeneratorError, "does not match"):
            VALIDATOR.load_and_validate(self.workbook)

    def test_source_url_drift_is_rejected(self) -> None:
        self.frames["Materials"].loc[0, "Source_URL"] = "https://example.invalid/"
        self.write_workbook()
        with self.assertRaisesRegex(SUPPORT.GeneratorError, "Source_URL does not match"):
            VALIDATOR.load_and_validate(self.workbook)

    def test_derived_modulus_drift_is_rejected(self) -> None:
        self.frames["Materials"].loc[0, "Shear_Modulus_GPa_Derived"] += 1
        self.write_workbook()
        with self.assertRaisesRegex(SUPPORT.GeneratorError, "Derived shear modulus"):
            VALIDATOR.load_and_validate(self.workbook)

    def test_new_material_is_generated_without_count_or_validation_changes(self) -> None:
        material = self.frames["Materials"].iloc[-1].copy()
        material["Material_ID"] = 6011
        material["CPD_Constant"] = "TEST_MAINTAINED_MATERIAL"
        material["Material_Name"] = "Workbook-maintained test material"
        material["Duplicate_ID_Flag"] = "OK"
        self.frames["Materials"] = pd.concat([self.frames["Materials"], material.to_frame().T], ignore_index=True)
        exported = self.frames["CPD Numeric Export"].iloc[-1].copy()
        exported["Material_ID"] = 6011
        self.frames["CPD Numeric Export"] = pd.concat([self.frames["CPD Numeric Export"], exported.to_frame().T], ignore_index=True)
        self.write_workbook()

        generated = GENERATOR.generate_library(self.workbook, TEMPLATE)
        self.assertIn("TEST_MAINTAINED_MATERIAL = 6011", generated)
        self.assertIn("Workbook-maintained test material", generated)
        self.assertIn("127 common materials", generated)

    def test_failed_validation_preserves_existing_output(self) -> None:
        output = self.root / "EngineeringMaterials.cpd"
        original = "'previous maintained output\n"
        output.write_text(original, encoding="utf-8", newline="\n")
        self.frames["Materials"].loc[0, "Source_URL"] = "https://example.invalid/"
        self.write_workbook()
        with self.assertRaisesRegex(SUPPORT.GeneratorError, "Source_URL does not match"):
            generated = GENERATOR.generate_library(self.workbook, TEMPLATE)
            SUPPORT.write_or_check(output, generated, False)
        self.assertEqual(output.read_text(encoding="utf-8"), original)
        self.assertEqual(list(output.parent.glob(f".{output.name}.*.tmp")), [])

    def test_check_rejects_stale_output(self) -> None:
        output = self.root / "EngineeringMaterials.cpd"
        output.write_text("stale\n", encoding="utf-8")
        with self.assertRaisesRegex(SUPPORT.GeneratorError, "stale"):
            SUPPORT.write_or_check(output, GENERATOR.generate_library(SOURCE, TEMPLATE), True)


if __name__ == "__main__":
    unittest.main()
