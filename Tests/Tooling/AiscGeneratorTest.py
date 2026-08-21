"""Regression tests for the curated structural-section workbook and generators."""

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
CONFIGURATIONS = [
    (GENERATORS[0], "W", (("W", 289),), 1001, "Libraries/Steel/StructuralSections.cpd"),
    (GENERATORS[1], "HSS", (("HSS", 714),), 2001, "Libraries/Steel/AiscHssSections.cpd"),
    (GENERATORS[2], "Channel", (("C", 32), ("MC", 40)), 3001, "Libraries/Steel/AiscChannelSections.cpd"),
    (GENERATORS[3], "Angle", (("L", 137),), 4001, "Libraries/Steel/AiscAngleSections.cpd"),
]


class AiscGeneratorTests(unittest.TestCase):
    """Protect the curated schema and every generator's deterministic output."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.workbook = self.root / "drat-structural-sections.xlsx"
        self.frames: dict[str, pd.DataFrame] = {}
        property_rows: list[dict[str, object]] = []
        for generator, sheet, families, first_id, _ in CONFIGURATIONS:
            rows: list[dict[str, object]] = []
            item_id = first_id
            for family, count in families:
                for index in range(1, count + 1):
                    row: dict[str, object] = {
                        "Section_ID": item_id,
                        "Type": family,
                        "AISC_Manual_Label": f"{family}{index}X1",
                    }
                    row.update({column: float(index) for _, _, _, column in generator.PROPERTIES})
                    rows.append(row)
                    item_id += 1
            self.frames[sheet] = pd.DataFrame(rows)
            for property_id, (code, name, unit, column) in enumerate(generator.PROPERTIES, 1):
                property_rows.append(
                    {
                        "Family": sheet,
                        "Property ID": property_id,
                        "CalcPad code": code,
                        "Property name": name,
                        "Unit": unit,
                        "Source column": column,
                        "Required": "Yes" if code in {"WEIGHT", "AREA"} else "No",
                    }
                )
        self.properties = pd.DataFrame(property_rows)
        self.readme = pd.DataFrame(
            [
                ["Dataset ID", SUPPORT.DATASET_ID],
                ["Dataset revision", SUPPORT.DATASET_REVISION],
                ["Source basis", SUPPORT.SOURCE_REVISION],
            ]
        )
        self.write_workbook()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_workbook(self, omitted_sheet: str | None = None) -> None:
        with pd.ExcelWriter(self.workbook, engine="openpyxl") as writer:
            self.readme.to_excel(writer, sheet_name=SUPPORT.README_SHEET, index=False, header=False)
            self.properties.to_excel(writer, sheet_name=SUPPORT.PROPERTIES_SHEET, index=False)
            for sheet, frame in self.frames.items():
                if sheet != omitted_sheet:
                    frame.to_excel(writer, sheet_name=sheet, index=False)

    def test_committed_source_reproduces_every_library(self) -> None:
        source = REPOSITORY_ROOT / "Data/Sources/AiscShapesV16/DratStructuralSectionsSource.xlsx"
        for generator, _, _, _, output in CONFIGURATIONS:
            with self.subTest(generator=generator.__name__):
                self.assertEqual(generator.build(source), (REPOSITORY_ROOT / output).read_text(encoding="utf-8"))

    def test_every_generator_is_deterministic(self) -> None:
        for generator in GENERATORS:
            with self.subTest(generator=generator.__name__):
                first = generator.build(self.workbook)
                second = generator.build(self.workbook)
                self.assertEqual(first, second)
                self.assertIn("DRAT_CORE_API < 50000", first)

    def test_missing_required_worksheet_is_rejected(self) -> None:
        self.write_workbook(omitted_sheet="W")
        with self.assertRaisesRegex(OUTPUT_SUPPORT.GeneratorError, "missing worksheet"):
            GENERATORS[0].build(self.workbook)

    def test_missing_property_column_is_rejected(self) -> None:
        self.frames["W"].drop(columns=[GENERATORS[0].PROPERTIES[0][3]], inplace=True)
        self.write_workbook()
        with self.assertRaisesRegex(OUTPUT_SUPPORT.GeneratorError, "missing required columns"):
            GENERATORS[0].build(self.workbook)

    def test_property_contract_drift_is_rejected(self) -> None:
        row = self.properties.index[(self.properties["Family"] == "W") & (self.properties["CalcPad code"] == "AREA")][0]
        self.properties.loc[row, "Unit"] = "in"
        self.write_workbook()
        with self.assertRaisesRegex(OUTPUT_SUPPORT.GeneratorError, "does not match the generator API"):
            GENERATORS[0].build(self.workbook)

    def test_duplicate_label_is_rejected(self) -> None:
        self.frames["W"].loc[1, "AISC_Manual_Label"] = self.frames["W"].loc[0, "AISC_Manual_Label"]
        self.write_workbook()
        with self.assertRaisesRegex(OUTPUT_SUPPORT.GeneratorError, "must be unique"):
            GENERATORS[0].build(self.workbook)

    def test_invalid_numeric_value_is_rejected(self) -> None:
        column = GENERATORS[1].PROPERTIES[0][3]
        self.frames["HSS"][column] = self.frames["HSS"][column].astype(object)
        self.frames["HSS"].loc[0, column] = "invalid"
        self.write_workbook()
        with self.assertRaisesRegex(OUTPUT_SUPPORT.GeneratorError, "non-numeric"):
            GENERATORS[1].build(self.workbook)

    def test_unstable_section_id_is_rejected(self) -> None:
        self.frames["Angle"].loc[0, "Section_ID"] = 4999
        self.write_workbook()
        with self.assertRaisesRegex(OUTPUT_SUPPORT.GeneratorError, "unique, ordered, and contiguous"):
            GENERATORS[3].build(self.workbook)

    def test_new_section_is_generated_without_count_validation_changes(self) -> None:
        row = self.frames["W"].iloc[-1].copy()
        row["Section_ID"] = int(row["Section_ID"]) + 1
        row["AISC_Manual_Label"] = "WMAINTAINEDX1"
        self.frames["W"] = pd.concat([self.frames["W"], row.to_frame().T], ignore_index=True)
        self.write_workbook()
        generated = GENERATORS[0].build(self.workbook)
        self.assertIn("290 AISC W-shapes", generated)
        self.assertIn("WMAINTAINEDX1", generated)

    def test_failed_validation_preserves_output(self) -> None:
        output = self.root / "StructuralSections.cpd"
        original = "'previous maintained output\n"
        output.write_text(original, encoding="utf-8", newline="\n")
        self.frames["W"].drop(index=0, inplace=True)
        self.write_workbook()
        with self.assertRaisesRegex(OUTPUT_SUPPORT.GeneratorError, "unique, ordered, and contiguous"):
            generated = GENERATORS[0].build(self.workbook)
            OUTPUT_SUPPORT.write_or_check(output, generated, False)
        self.assertEqual(output.read_text(encoding="utf-8"), original)
        self.assertEqual(list(output.parent.glob(f".{output.name}.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
