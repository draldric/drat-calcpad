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
HELMHOLTZ_DATA_PATH = REPOSITORY_ROOT / "Data" / "Sources" / "Thermophysical" / "HelmholtzFluids.json"
GLYCOL_DATA_PATH = REPOSITORY_ROOT / "Data" / "Sources" / "Thermophysical" / "IncompressibleGlycols.json"
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
        self.helmholtz_dataset = json.loads(HELMHOLTZ_DATA_PATH.read_text(encoding="utf-8"))
        self.glycol_dataset = json.loads(GLYCOL_DATA_PATH.read_text(encoding="utf-8"))

    def validate_helmholtz(self, dataset: dict | None = None) -> dict:
        """Validate the curated Helmholtz source with the generator's strict helpers."""

        return GENERATOR.validate_helmholtz(
            self.helmholtz_dataset if dataset is None else dataset,
            GENERATOR.require,
            GENERATOR.require_mapping,
            GENERATOR.require_list,
            GENERATOR.require_integer,
            GENERATOR.require_text,
            GENERATOR.require_constant,
            GENERATOR.require_number,
            GENERATOR.validate_unique,
        )

    def test_valid_dataset_generates_guarded_library(self) -> None:
        """A valid dataset should produce the guarded typed API and provenance macros."""

        validated = GENERATOR.validate_dataset(self.dataset)
        helmholtz_validated = self.validate_helmholtz()
        glycol_validated = GENERATOR.validate_glycols(self.glycol_dataset, GENERATOR.require)
        generated = GENERATOR.generate_library(validated, helmholtz_validated, glycol_validated)
        self.assertIn("ThermophysicalPropertiesLibraryRevision$ = 0.7.0", generated)
        self.assertIn("WaterSaturationPressureT(temperature)", generated)
        self.assertIn("Eg50DynamicViscosityTStatus(temperature)", generated)
        self.assertIn("If97RegionPT(pressure; temperature)", generated)
        self.assertIn("If97EnthalpyPT(pressure; temperature)", generated)
        self.assertIn("If97SaturationTemperatureP(pressure)", generated)
        self.assertIn("ThermoProps(output; input_1; value_1; input_2; value_2; fluid)", generated)
        self.assertIn("ThermoPropsStatus(output; input_1; value_1; input_2; value_2; fluid)", generated)
        self.assertIn("PropsSI(output; input_1; value_1; input_2; value_2; fluid)", generated)
        self.assertIn("PropsSIIncompressible(output; input_1; value_1; input_2; value_2; family; glycol_mass_fraction)", generated)
        self.assertIn("#def PropsSI$(output$; input_1$; value_1$; input_2$; value_2$; fluid$)", generated)
        self.assertIn("THERMO_NITROGEN = 301", generated)
        self.assertIn("THERMO_CARBON_DIOXIDE = 302", generated)
        self.assertIn("THERMO_R11 = 303", generated)
        self.assertIn("THERMO_R717 = 311", generated)
        self.assertIn("THERMO_PROPYLENE_GLYCOL = 312", generated)
        self.assertIn("THERMO_R744 = THERMO_CARBON_DIOXIDE", generated)
        self.assertIn("THERMO_R718 = THERMO_WATER", generated)
        self.assertIn("CP_CP = 7", generated)
        self.assertIn("CP_C = 9", generated)
        self.assertIn("CP_ISOBARIC_HEAT_CAPACITY = CP_CP", generated)
        self.assertIn("CP_SPEED_OF_SOUND = CP_C", generated)
        self.assertIn("CP_SPECIFIC_VOLUME = CP_VSPEC", generated)
        self.assertIn("HelmholtzN2AlphaR(delta; tau)", generated)
        self.assertIn("HelmholtzCO2AlphaR(delta; tau)", generated)
        self.assertIn("HelmholtzR717AlphaR(delta; tau)", generated)
        self.assertIn("Valid thermophysical state", generated)
        self.assertIn("HelmholtzPropertyPT(output; fluid; pressure; temperature)", generated)
        self.assertIn("GlycolPROP(family; property; temperature; glycol_mass_fraction)", generated)
        self.assertIn("EgWaterDensityTX(temperature; glycol_mass_fraction)", generated)
        self.assertIn("PgWaterDynamicViscosityTX(temperature; glycol_mass_fraction)", generated)
        self.assertIn("ThermoSourceCitation$", generated)
        self.assertIn("DRAT_DATA_WRAPPER_API ≥ 303", generated)

    def test_rejects_incomplete_if97_coefficient_series(self) -> None:
        """Every official IF97 coefficient array must retain its fixed published length."""

        invalid = copy.deepcopy(self.dataset)
        invalid["if97"]["regions"]["region1"]["n"].pop()
        with self.assertRaisesRegex(GENERATOR.SchemaError, "exactly 34"):
            GENERATOR.validate_dataset(invalid)

    def test_rejects_unknown_if97_unit_key(self) -> None:
        """IF97 output dimensions must be selected from the audited unit map."""

        invalid = copy.deepcopy(self.dataset)
        invalid["if97"]["properties"][0]["unit_key"] = "arbitrary_code"
        with self.assertRaisesRegex(GENERATOR.SchemaError, "unit_key is unsupported"):
            GENERATOR.validate_dataset(invalid)

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

    def test_rejects_unknown_helmholtz_term_family(self) -> None:
        """Only explicitly implemented equation-term families may be imported."""

        invalid = copy.deepcopy(self.helmholtz_dataset)
        invalid["fluids"][0]["residual"][0]["type"] = "ResidualHelmholtzUnknown"
        with self.assertRaisesRegex(GENERATOR.SchemaError, "unsupported residual term family"):
            self.validate_helmholtz(invalid)

    def test_rejects_misaligned_helmholtz_coefficients(self) -> None:
        """Parallel coefficient arrays must remain aligned term by term."""

        invalid = copy.deepcopy(self.helmholtz_dataset)
        invalid["fluids"][0]["residual"][0]["n"].pop()
        with self.assertRaisesRegex(GENERATOR.SchemaError, "equal length"):
            self.validate_helmholtz(invalid)

    def test_rejects_duplicate_helmholtz_fluid_id(self) -> None:
        """Equation-fluid IDs share the generated catalog and must be unique."""

        invalid = copy.deepcopy(self.helmholtz_dataset)
        invalid["fluids"][1]["id"] = invalid["fluids"][0]["id"]
        with self.assertRaisesRegex(GENERATOR.SchemaError, "helmholtz fluid IDs"):
            self.validate_helmholtz(invalid)

    def test_rejects_incomplete_glycol_family_set(self) -> None:
        """Both aqueous-glycol families are required for deterministic generation."""

        invalid = copy.deepcopy(self.glycol_dataset)
        invalid["families"].pop()
        with self.assertRaisesRegex(GENERATOR.SchemaError, "exactly two families"):
            GENERATOR.validate_glycols(invalid, GENERATOR.require)

    def test_rejects_unknown_glycol_equation_family(self) -> None:
        """Unimplemented correlation forms must not enter generated CalcPad source."""

        invalid = copy.deepcopy(self.glycol_dataset)
        invalid["families"][0]["properties"]["viscosity"]["type"] = "lookup"
        with self.assertRaisesRegex(GENERATOR.SchemaError, "equation family is unsupported"):
            GENERATOR.validate_glycols(invalid, GENERATOR.require)

    def test_rejects_glycol_metadata_control_text(self) -> None:
        """Generated provenance macros must reject CalcPad control text."""

        invalid = copy.deepcopy(self.glycol_dataset)
        invalid["source"]["name"] = "Unsafe $macro"
        with self.assertRaisesRegex(GENERATOR.SchemaError, "control text"):
            GENERATOR.validate_glycols(invalid, GENERATOR.require)

    def test_check_mode_detects_stale_output(self) -> None:
        """Check mode must accept exact output and reject a stale committed file."""

        generated = GENERATOR.generate_library(GENERATOR.validate_dataset(self.dataset), self.validate_helmholtz(), GENERATOR.validate_glycols(self.glycol_dataset, GENERATOR.require))
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
                generated = GENERATOR.generate_library(GENERATOR.validate_dataset(invalid), self.validate_helmholtz(), GENERATOR.validate_glycols(self.glycol_dataset, GENERATOR.require))
                GENERATOR.write_or_check(output_path, generated, False)
            self.assertEqual(output_path.read_text(encoding="utf-8"), original)
            self.assertEqual(list(output_path.parent.glob(f".{output_path.name}.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
