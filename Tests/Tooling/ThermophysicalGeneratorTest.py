"""Regression tests for thermophysical raw-data schema validation and generation."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "Tools"))
sys.dont_write_bytecode = True
GENERATOR_PATH = REPOSITORY_ROOT / "Tools" / "GenerateThermophysicalLibrary.py"
DATA_PATH = REPOSITORY_ROOT / "Data" / "Sources" / "Thermophysical" / "ThermophysicalProperties.json"
MODULE_SPEC = importlib.util.spec_from_file_location("thermophysical_generator", GENERATOR_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"Could not load generator module: {GENERATOR_PATH}")
GENERATOR = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(GENERATOR)


class ThermophysicalGeneratorTests(unittest.TestCase):
    """Protect schema rejection and deterministic generated output."""

    def setUp(self) -> None:
        """Load an independent valid dataset before each test."""

        self.dataset = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    def test_valid_dataset_generates_guarded_library(self) -> None:
        """A valid dataset should produce the guarded typed API and provenance macros."""

        validated = GENERATOR.validate_dataset(self.dataset)
        generated = GENERATOR.generate_library(validated)
        self.assertIn("ThermophysicalPropertiesLibraryRevision$ = 0.1.0", generated)
        self.assertIn("WaterSaturationPressureT(temperature)", generated)
        self.assertIn("Eg50DynamicViscosityTStatus(temperature)", generated)
        self.assertIn("ThermoSourceCitation$", generated)
        self.assertIn("DRAT_DATA_WRAPPER_API ≥ 303", generated)

    def test_rejects_non_increasing_temperature_axis(self) -> None:
        """Curves with repeated or descending temperatures must be rejected."""

        invalid = copy.deepcopy(self.dataset)
        invalid["curves"][0]["temperature_c"][1] = invalid["curves"][0]["temperature_c"][0]
        with self.assertRaisesRegex(GENERATOR.SchemaError, "strictly increasing"):
            GENERATOR.validate_dataset(invalid)

    def test_rejects_duplicate_curve_key(self) -> None:
        """A fluid-property pair must have exactly one generated curve."""

        invalid = copy.deepcopy(self.dataset)
        duplicate = copy.deepcopy(invalid["curves"][0])
        duplicate["value_function"] = "DuplicateCurveValue"
        duplicate["status_function"] = "DuplicateCurveStatus"
        invalid["curves"].append(duplicate)
        with self.assertRaisesRegex(GENERATOR.SchemaError, "curve keys"):
            GENERATOR.validate_dataset(invalid)

    def test_rejects_unknown_unit_key(self) -> None:
        """Only audited CalcPad unit expressions may enter generated source."""

        invalid = copy.deepcopy(self.dataset)
        invalid["properties"][0]["unit_key"] = "arbitrary_code"
        with self.assertRaisesRegex(GENERATOR.SchemaError, "unit_key is unsupported"):
            GENERATOR.validate_dataset(invalid)

    def test_rejects_calc_pad_control_text(self) -> None:
        """Raw display text must not be able to inject CalcPad macros or HTML."""

        invalid = copy.deepcopy(self.dataset)
        invalid["sources"][0]["notes"] = "Unsafe $macro content"
        with self.assertRaisesRegex(GENERATOR.SchemaError, "control text"):
            GENERATOR.validate_dataset(invalid)

    def test_rejects_duplicate_public_function(self) -> None:
        """Generated typed helper names must remain globally unique."""

        invalid = copy.deepcopy(self.dataset)
        invalid["curves"][1]["value_function"] = invalid["curves"][0]["value_function"]
        with self.assertRaisesRegex(GENERATOR.SchemaError, "function names"):
            GENERATOR.validate_dataset(invalid)

    def test_check_mode_detects_stale_output(self) -> None:
        """Check mode must accept exact output and reject a stale committed file."""

        generated = GENERATOR.generate_library(GENERATOR.validate_dataset(self.dataset))
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "ThermophysicalProperties.cpd"
            output_path.write_text(generated, encoding="utf-8", newline="\n")
            GENERATOR.write_or_check(output_path, generated, True)
            output_path.write_text(generated + "'stale\n", encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(GENERATOR.SchemaError, "stale"):
                GENERATOR.write_or_check(output_path, generated, True)

    def test_failed_validation_preserves_existing_output(self) -> None:
        """An invalid source must fail before the maintained output is touched."""

        invalid = copy.deepcopy(self.dataset)
        invalid["curves"][0]["temperature_c"][1] = invalid["curves"][0]["temperature_c"][0]
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "ThermophysicalProperties.cpd"
            original = "'previous maintained output\n"
            output_path.write_text(original, encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(GENERATOR.SchemaError, "strictly increasing"):
                generated = GENERATOR.generate_library(GENERATOR.validate_dataset(invalid))
                GENERATOR.write_or_check(output_path, generated, False)
            self.assertEqual(output_path.read_text(encoding="utf-8"), original)
            self.assertEqual(list(output_path.parent.glob(f".{output_path.name}.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
