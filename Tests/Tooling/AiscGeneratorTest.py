"""Regression tests for AISC workbook validation and deterministic generation."""

from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPOSITORY_ROOT / "Tools"
sys.path.insert(0, str(TOOLS))
sys.dont_write_bytecode = True

SUPPORT = importlib.import_module("AiscGeneratorSupport")
OUTPUT_SUPPORT = importlib.import_module("GeneratorSupport")
GENERATORS = [
    importlib.import_module("GenerateAiscWLibrary"),
    importlib.import_module("GenerateAiscHssLibrary"),
    importlib.import_module("GenerateAiscChannelLibrary"),
    importlib.import_module("GenerateAiscAngleLibrary"),
]


class AiscGeneratorTests(unittest.TestCase):
    """Protect shared schema rejection and every AISC generator's determinism."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.workbook = self.root / "aisc-v16.xlsx"
        property_columns = sorted({item[3] for module in GENERATORS for item in module.PROPERTIES})
        rows: list[dict[str, object]] = []
        families = (("W", 289), ("HSS", 714), ("C", 32), ("MC", 40), ("L", 137))
        for family, count in families:
            for index in range(1, count + 1):
                row: dict[str, object] = {
                    "Type": family,
                    "AISC_Manual_Label": f"{family}{index}X1",
                }
                row.update({column: float(index) for column in property_columns})
                rows.append(row)
        with pd.ExcelWriter(self.workbook, engine="openpyxl") as writer:
            pd.DataFrame(rows).to_excel(writer, sheet_name=SUPPORT.DATABASE_SHEET, index=False)
            pd.DataFrame({"Revision": [SUPPORT.SOURCE_REVISION]}).to_excel(
                writer, sheet_name=SUPPORT.README_SHEET, index=False
            )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def rewrite_database(self, transform) -> None:
        data = pd.read_excel(self.workbook, sheet_name=SUPPORT.DATABASE_SHEET, engine="openpyxl")
        transform(data)
        with pd.ExcelWriter(self.workbook, engine="openpyxl") as writer:
            data.to_excel(writer, sheet_name=SUPPORT.DATABASE_SHEET, index=False)
            pd.DataFrame({"Revision": [SUPPORT.SOURCE_REVISION]}).to_excel(
                writer, sheet_name=SUPPORT.README_SHEET, index=False
            )

    def test_every_generator_is_deterministic(self) -> None:
        for generator in GENERATORS:
            with self.subTest(generator=generator.__name__):
                first = generator.build(self.workbook)
                second = generator.build(self.workbook)
                self.assertEqual(first, second)
                self.assertIn("DRAT_CORE_API < 50000", first)

    def test_missing_required_worksheet_is_rejected(self) -> None:
        invalid = self.root / "missing-readme.xlsx"
        pd.DataFrame({"Type": ["W"]}).to_excel(invalid, sheet_name=SUPPORT.DATABASE_SHEET, index=False)
        with self.assertRaisesRegex(OUTPUT_SUPPORT.GeneratorError, "missing worksheet"):
            GENERATORS[0].build(invalid)

    def test_missing_property_column_is_rejected(self) -> None:
        def transform(data: pd.DataFrame) -> None:
            data.drop(columns=[GENERATORS[0].PROPERTIES[0][3]], inplace=True)

        self.rewrite_database(transform)
        with self.assertRaisesRegex(OUTPUT_SUPPORT.GeneratorError, "missing required columns"):
            GENERATORS[0].build(self.workbook)

    def test_duplicate_label_is_rejected(self) -> None:
        def transform(data: pd.DataFrame) -> None:
            indexes = data.index[data["Type"].eq("W")][:2]
            data.loc[indexes[1], "AISC_Manual_Label"] = data.loc[indexes[0], "AISC_Manual_Label"]

        self.rewrite_database(transform)
        with self.assertRaisesRegex(OUTPUT_SUPPORT.GeneratorError, "must be unique"):
            GENERATORS[0].build(self.workbook)

    def test_invalid_numeric_value_is_rejected(self) -> None:
        def transform(data: pd.DataFrame) -> None:
            index = data.index[data["Type"].eq("HSS")][0]
            column = GENERATORS[1].PROPERTIES[0][3]
            data[column] = data[column].astype(object)
            data.loc[index, column] = "invalid"

        self.rewrite_database(transform)
        with self.assertRaisesRegex(OUTPUT_SUPPORT.GeneratorError, "non-numeric"):
            GENERATORS[1].build(self.workbook)

    def test_failed_validation_preserves_output(self) -> None:
        output = self.root / "StructuralSections.cpd"
        original = "'previous maintained output\n"
        output.write_text(original, encoding="utf-8", newline="\n")

        def transform(data: pd.DataFrame) -> None:
            data.drop(data.index[data["Type"].eq("W")][0], inplace=True)

        self.rewrite_database(transform)
        with self.assertRaisesRegex(OUTPUT_SUPPORT.GeneratorError, "Expected 289 W records"):
            generated = GENERATORS[0].build(self.workbook)
            OUTPUT_SUPPORT.write_or_check(output, generated, False)
        self.assertEqual(output.read_text(encoding="utf-8"), original)
        self.assertEqual(list(output.parent.glob(f".{output.name}.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
