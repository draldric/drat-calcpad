"""Generate the committed CalcPad thermophysical-property library from JSON data."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from GeneratorSupport import GeneratorError, write_or_check as safe_write_or_check


UNIT_EXPRESSIONS = {
    "kg_per_m3": "kg/m^3",
    "J_per_kgK": "J/(kg*K)",
    "Pa_s": "Pa*s",
    "W_per_mK": "W/(m*K)",
    "kPa": "kPa",
    "kJ_per_kg": "kJ/kg",
}
CONSTANT_PATTERN = re.compile(r"^THERMO_[A-Z][A-Z0-9_]*$")
FUNCTION_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9]*$")
REVISION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SchemaError(GeneratorError):
    """Report a deterministic raw-data schema failure."""


def require(condition: bool, message: str) -> None:
    """Raise a schema error when a required condition is false."""

    if not condition:
        raise SchemaError(message)


def require_mapping(value: Any, path: str) -> dict[str, Any]:
    """Return a mapping value or raise a path-specific schema error."""

    require(isinstance(value, dict), f"{path} must be an object.")
    return value


def require_list(value: Any, path: str) -> list[Any]:
    """Return a list value or raise a path-specific schema error."""

    require(isinstance(value, list), f"{path} must be an array.")
    return value


def require_integer(value: Any, path: str, minimum: int = 1, maximum: int = 999) -> int:
    """Return a bounded non-Boolean integer or raise a schema error."""

    require(isinstance(value, int) and not isinstance(value, bool), f"{path} must be an integer.")
    require(minimum <= value <= maximum, f"{path} must be between {minimum} and {maximum}.")
    return value


def require_text(value: Any, path: str) -> str:
    """Return safe single-line CalcPad text or raise a schema error."""

    require(isinstance(value, str) and value.strip() == value and value, f"{path} must be non-empty text without surrounding whitespace.")
    require("\n" not in value and "\r" not in value, f"{path} must be single-line text.")
    require("'" not in value, f"{path} must not contain an apostrophe because CalcPad treats it as formatted output.")
    require(not any(marker in value for marker in ("#", "$", "<", ">")), f"{path} contains CalcPad or HTML control text.")
    return value


def require_constant(value: Any, path: str) -> str:
    """Return a valid library-prefixed CalcPad constant name."""

    text = require_text(value, path)
    require(CONSTANT_PATTERN.fullmatch(text) is not None, f"{path} must match {CONSTANT_PATTERN.pattern}.")
    return text


def require_function(value: Any, path: str) -> str:
    """Return a valid PascalCase CalcPad function name."""

    text = require_text(value, path)
    require(FUNCTION_PATTERN.fullmatch(text) is not None, f"{path} must be a PascalCase identifier.")
    return text


def require_number(value: Any, path: str) -> float:
    """Return a finite numeric value or raise a schema error."""

    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{path} must be numeric.")
    number = float(value)
    require(math.isfinite(number), f"{path} must be finite.")
    return number


def validate_unique(values: list[Any], path: str) -> None:
    """Require every value in a schema collection to be unique."""

    require(len(values) == len(set(values)), f"{path} values must be unique.")


def validate_dataset(dataset: Any) -> dict[str, Any]:
    """Validate and return a thermophysical-property dataset."""

    root = require_mapping(dataset, "root")
    require(root.get("schema_version") == 1, "schema_version must equal 1.")

    library = require_mapping(root.get("library"), "library")
    for field in ("name", "revision", "date", "scope"):
        require_text(library.get(field), f"library.{field}")
    require(REVISION_PATTERN.fullmatch(library["revision"]) is not None, "library.revision must use numeric semantic versioning.")
    require(DATE_PATTERN.fullmatch(library["date"]) is not None, "library.date must use YYYY-MM-DD.")

    sources = require_list(root.get("sources"), "sources")
    fluids = require_list(root.get("fluids"), "fluids")
    properties = require_list(root.get("properties"), "properties")
    curves = require_list(root.get("curves"), "curves")
    require(sources and fluids and properties and curves, "sources, fluids, properties, and curves must not be empty.")

    source_ids: list[int] = []
    source_constants: list[str] = []
    for index, item in enumerate(sources):
        source = require_mapping(item, f"sources[{index}]")
        source_ids.append(require_integer(source.get("id"), f"sources[{index}].id"))
        source_constants.append(require_constant(source.get("constant"), f"sources[{index}].constant"))
        for field in ("name", "citation", "revision", "license", "notes"):
            require_text(source.get(field), f"sources[{index}].{field}")
    validate_unique(source_ids, "source IDs")
    validate_unique(source_constants, "source constants")

    fluid_ids: list[int] = []
    fluid_constants: list[str] = []
    for index, item in enumerate(fluids):
        fluid = require_mapping(item, f"fluids[{index}]")
        fluid_ids.append(require_integer(fluid.get("id"), f"fluids[{index}].id"))
        fluid_constants.append(require_constant(fluid.get("constant"), f"fluids[{index}].constant"))
        for field in ("name", "description"):
            require_text(fluid.get(field), f"fluids[{index}].{field}")
        concentration = fluid.get("concentration_mass_fraction")
        if concentration is not None:
            fraction = require_number(concentration, f"fluids[{index}].concentration_mass_fraction")
            require(0 <= fraction <= 1, f"fluids[{index}].concentration_mass_fraction must be between zero and one.")
    validate_unique(fluid_ids, "fluid IDs")
    validate_unique(fluid_constants, "fluid constants")

    property_ids: list[int] = []
    property_constants: list[str] = []
    for index, item in enumerate(properties):
        prop = require_mapping(item, f"properties[{index}]")
        property_ids.append(require_integer(prop.get("id"), f"properties[{index}].id"))
        property_constants.append(require_constant(prop.get("constant"), f"properties[{index}].constant"))
        for field in ("name", "symbol", "unit_key", "unit_label"):
            require_text(prop.get(field), f"properties[{index}].{field}")
        require(prop["unit_key"] in UNIT_EXPRESSIONS, f"properties[{index}].unit_key is unsupported.")
    validate_unique(property_ids, "property IDs")
    validate_unique(property_constants, "property constants")

    curve_keys: list[tuple[int, int]] = []
    function_names: list[str] = []
    for index, item in enumerate(curves):
        curve = require_mapping(item, f"curves[{index}]")
        fluid_id = require_integer(curve.get("fluid_id"), f"curves[{index}].fluid_id")
        property_id = require_integer(curve.get("property_id"), f"curves[{index}].property_id")
        source_id = require_integer(curve.get("source_id"), f"curves[{index}].source_id")
        require(fluid_id in fluid_ids, f"curves[{index}].fluid_id is unknown.")
        require(property_id in property_ids, f"curves[{index}].property_id is unknown.")
        require(source_id in source_ids, f"curves[{index}].source_id is unknown.")
        require_integer(curve.get("data_revision"), f"curves[{index}].data_revision", maximum=999999)
        curve_keys.append((fluid_id, property_id))
        function_names.append(require_function(curve.get("value_function"), f"curves[{index}].value_function"))
        function_names.append(require_function(curve.get("status_function"), f"curves[{index}].status_function"))

        temperatures = require_list(curve.get("temperature_c"), f"curves[{index}].temperature_c")
        values = require_list(curve.get("values"), f"curves[{index}].values")
        require(len(temperatures) >= 2, f"curves[{index}] must have at least two data points.")
        require(len(temperatures) == len(values), f"curves[{index}] temperature and value arrays must have equal lengths.")
        numeric_temperatures = [require_number(value, f"curves[{index}].temperature_c[{position}]") for position, value in enumerate(temperatures)]
        for position, value in enumerate(values):
            require_number(value, f"curves[{index}].values[{position}]")
        require(all(right > left for left, right in zip(numeric_temperatures, numeric_temperatures[1:])), f"curves[{index}].temperature_c must be strictly increasing.")

    validate_unique(curve_keys, "fluid-property curve keys")
    validate_unique(function_names, "typed public function names")
    require(len(set(source_constants + fluid_constants + property_constants)) == len(source_constants + fluid_constants + property_constants), "All generated CalcPad constants must be unique.")
    return root


def load_dataset(path: Path) -> dict[str, Any]:
    """Load and validate a UTF-8 JSON thermophysical dataset."""

    try:
        dataset = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SchemaError(f"Source dataset does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise SchemaError(f"Source dataset is not valid JSON: {error}") from error
    return validate_dataset(dataset)


def format_number(value: Any) -> str:
    """Format a validated numeric value deterministically for CalcPad."""

    number = float(value)
    if number == 0:
        return "0"
    return format(number, ".12g")


def calc_vector(values: list[Any]) -> str:
    """Render a CalcPad column-vector literal."""

    return "[" + "; ".join(format_number(value) for value in values) + "]"


def calc_matrix(rows: list[list[Any]]) -> str:
    """Render a CalcPad matrix literal from numeric rows."""

    return "[" + "|".join("; ".join(value if isinstance(value, str) else format_number(value) for value in row) for row in rows) + "]"


def append_text_macro(lines: list[str], name: str, argument: str, records: list[tuple[int, str]], unknown_condition: str, unknown_text: str) -> None:
    """Append a deterministic ID-to-text reporting macro."""

    lines.append(f"#def {name}({argument}$)")
    for record_id, text in records:
        lines.extend((f"    #if {argument}$ ≡ {record_id}", f"        '{text}", "    #end if"))
    lines.extend((f"    #if {unknown_condition}", f"        '<span class=\"err\">{unknown_text}</span>", "    #end if", "#end def", ""))


def generate_library(dataset: dict[str, Any]) -> str:
    """Render a validated dataset as a complete guarded CalcPad library."""

    library = dataset["library"]
    sources = dataset["sources"]
    fluids = dataset["fluids"]
    properties = dataset["properties"]
    curves = dataset["curves"]
    properties_by_id = {item["id"]: item for item in properties}

    curve_rows: list[list[Any]] = []
    metadata_rows: list[list[Any]] = []
    for curve in curves:
        key = curve["fluid_id"] * 1000 + curve["property_id"]
        minimum_temperature = f"{format_number(curve['temperature_c'][0])}°C"
        maximum_temperature = f"{format_number(curve['temperature_c'][-1])}°C"
        metadata_rows.append([key, minimum_temperature, maximum_temperature, curve["source_id"], curve["data_revision"]])
        curve_rows.extend([key, f"{format_number(temperature)}°C", value] for temperature, value in zip(curve["temperature_c"], curve["values"]))

    lines: list[str] = [
        "'<!-- GENERATED FILE. Edit Data/Sources/Thermophysical/ThermophysicalProperties.json and run Tools/GenerateThermophysicalLibrary.py. -->",
        "#if and(DRAT_CORE_API ≥ 40000; DRAT_CORE_API < 50000)",
        "#if and(DRAT_DATA_WRAPPER_API ≥ 303; DRAT_DATA_WRAPPER_API < 1000)",
        "#hide",
        "'<!-- Status-aware thermophysical property curves. -->",
        "",
        f"#def ThermophysicalPropertiesLibraryName$ = {library['name']}",
        f"#def ThermophysicalPropertiesLibraryRevision$ = {library['revision']}",
        f"#def ThermophysicalPropertiesLibraryDate$ = {library['date']}",
        f"#def ThermophysicalPropertiesLibraryScope$ = {library['scope']}",
        "",
    ]

    for source in sources:
        lines.append(f"{source['constant']} = {source['id']}")
    lines.extend(("", f"ThermoSourceIDs = {calc_vector([item['id'] for item in sources])}", ""))
    for fluid in fluids:
        lines.append(f"{fluid['constant']} = {fluid['id']}")
    lines.extend(("", f"ThermoFluidIDs = {calc_vector([item['id'] for item in fluids])}", ""))
    for prop in properties:
        lines.append(f"{prop['constant']} = {prop['id']}")
    lines.extend(
        (
            "THERMO_P_CP = THERMO_P_SPECIFIC_HEAT",
            "THERMO_P_VISCOSITY = THERMO_P_DYNAMIC_VISCOSITY",
            "THERMO_P_CONDUCTIVITY = THERMO_P_THERMAL_CONDUCTIVITY",
            "",
            f"ThermoPropertyIDs = {calc_vector([item['id'] for item in properties])}",
            "",
            f"ThermoCurveData = {calc_matrix(curve_rows)}",
            f"ThermoMetadata = {calc_matrix(metadata_rows)}",
            f"ThermoFluidCount = {len(fluids)}",
            f"ThermoPropertyCount = {len(properties)}",
            f"ThermoCurveCount = {len(curves)}",
            f"ThermoPointCount = {len(curve_rows)}",
            "",
            "ThermoHasFluid(fluid) = DBHasID(ThermoFluidIDs; fluid)",
            "ThermoHasProperty(property) = DBHasID(ThermoPropertyIDs; property)",
            "ThermoHasSource(source_id) = DBHasID(ThermoSourceIDs; source_id)",
            "ThermoHasCurve(fluid; property) = DBCurveExists(ThermoCurveData; DBKey(fluid; property))",
            "ThermoHasMetadata(fluid; property) = and(DBTableStatus(ThermoMetadata; DBKey(fluid; property); 2) ≡ DB_OK; DBTableStatus(ThermoMetadata; DBKey(fluid; property); 3) ≡ DB_OK; DBTableStatus(ThermoMetadata; DBKey(fluid; property); 4) ≡ DB_OK; DBTableStatus(ThermoMetadata; DBKey(fluid; property); 5) ≡ DB_OK)",
            "ThermoTMin(fluid; property) = DBTableRaw(ThermoMetadata; DBKey(fluid; property); 2)",
            "ThermoTMax(fluid; property) = DBTableRaw(ThermoMetadata; DBKey(fluid; property); 3)",
            "ThermoSourceID(fluid; property) = DBTableRaw(ThermoMetadata; DBKey(fluid; property); 4)",
            "ThermoDataRevision(fluid; property) = DBTableRaw(ThermoMetadata; DBKey(fluid; property); 5)",
            "",
        )
    )

    concentration_terms = []
    for fluid in fluids:
        concentration = fluid["concentration_mass_fraction"]
        raw = "DB_MISSING" if concentration is None else format_number(concentration)
        concentration_terms.extend((f"fluid ≡ {fluid['constant']}", raw))
    lines.append("ThermoFluidConcentrationMassFraction(fluid) = switch(" + "; ".join(concentration_terms + ["DB_MISSING"]) + ")")
    lines.append("ThermoFluidStatus(fluid) = if(ThermoHasFluid(fluid); DB_OK; DB_ERR_NAME)")
    lines.append("")

    unit_switch_terms: list[str] = []
    undefined_switch_terms: list[str] = []
    for prop in properties:
        expression = UNIT_EXPRESSIONS[prop["unit_key"]]
        unit_switch_terms.extend((f"property ≡ {prop['constant']}", f"setunits(value; {expression})"))
        undefined_switch_terms.extend((f"property ≡ {prop['constant']}", f"setunits(0/0; {expression})"))
    lines.extend(
        (
            "ThermoApplyUnits(property; value) = switch(" + "; ".join(unit_switch_terms + ["0/0"]) + ")",
            "ThermoUndefined(property) = switch(" + "; ".join(undefined_switch_terms + ["0/0"]) + ")",
            "",
            "ThermoDatasetOK = and(ThermoFluidCount ≡ len(ThermoFluidIDs); ThermoPropertyCount ≡ len(ThermoPropertyIDs); ThermoCurveCount ≡ n_rows(ThermoMetadata); n_cols(ThermoMetadata) ≡ 5; ThermoPointCount ≡ n_rows(ThermoCurveData); n_cols(ThermoCurveData) ≡ 3)",
            "ThermoDatasetStatus = if(ThermoDatasetOK; DB_OK; DB_ERR_MISSING)",
            "",
            "ThermoPROPStatus(fluid; property; temperature; method; bounds_policy) = _",
            "$block{",
            "    fluid_ok = ThermoHasFluid(fluid);",
            "    property_ok = ThermoHasProperty(property);",
            "    curve_ok = if(and(fluid_ok; property_ok); ThermoHasCurve(fluid; property); 0);",
            "    metadata_ok = if(curve_ok; ThermoHasMetadata(fluid; property); 0);",
            "    T_min = if(metadata_ok; ThermoTMin(fluid; property); 0°C);",
            "    T_max = if(metadata_ok; ThermoTMax(fluid; property); 0°C);",
            "    status = switch(ThermoDatasetStatus ≠ DB_OK; ThermoDatasetStatus; not(fluid_ok); DB_ERR_NAME; not(property_ok); DB_ERR_PROPERTY; not(curve_ok); DB_ERR_MISSING; not(metadata_ok); DB_ERR_MISSING; DBCurveStatus(ThermoCurveData; DBKey(fluid; property); temperature; T_min; T_max; method; bounds_policy));",
            "    status;",
            "}",
            "",
            "ThermoPROPEx(fluid; property; temperature; method; bounds_policy) = _",
            "$block{",
            "    status = ThermoPROPStatus(fluid; property; temperature; method; bounds_policy);",
            "    T_min = if(DBIsFatal(status); 0°C; ThermoTMin(fluid; property));",
            "    T_max = if(DBIsFatal(status); 0°C; ThermoTMax(fluid; property));",
            "    raw = if(DBIsFatal(status); 0/0; DBCurveRaw(ThermoCurveData; DBKey(fluid; property); temperature; T_min; T_max; method; bounds_policy));",
            "    value = if(DBIsFatal(status); ThermoUndefined(property); ThermoApplyUnits(property; raw));",
            "    value;",
            "}",
            "",
            "ThermoPROP(fluid; property; temperature) = ThermoPROPEx(fluid; property; temperature; DB_LINEAR; DB_STRICT)",
            "ThermoPROPAtC(fluid; property; temperature_C) = ThermoPROP(fluid; property; temperature_C*°C)",
            "ThermoPROPClamped(fluid; property; temperature) = ThermoPROPEx(fluid; property; temperature; DB_LINEAR; DB_CLAMP)",
            "ThermoPROPExtrapolated(fluid; property; temperature) = ThermoPROPEx(fluid; property; temperature; DB_LINEAR; DB_EXTRAPOLATE)",
            "",
        )
    )

    for curve in curves:
        fluid_constant = next(item["constant"] for item in fluids if item["id"] == curve["fluid_id"])
        property_constant = properties_by_id[curve["property_id"]]["constant"]
        lines.extend(
            (
                f"{curve['status_function']}(temperature) = ThermoPROPStatus({fluid_constant}; {property_constant}; temperature; DB_LINEAR; DB_STRICT)",
                f"{curve['value_function']}(temperature) = ThermoPROP({fluid_constant}; {property_constant}; temperature)",
            )
        )
    lines.append("")

    append_text_macro(lines, "ThermoFluidName$", "fluid", [(item["id"], item["name"]) for item in fluids], "not(ThermoHasFluid(fluid$))", "Unknown thermophysical fluid ID")
    append_text_macro(lines, "ThermoFluidDescription$", "fluid", [(item["id"], item["description"]) for item in fluids], "not(ThermoHasFluid(fluid$))", "Unknown thermophysical fluid ID")
    append_text_macro(lines, "ThermoPropertyName$", "property", [(item["id"], item["name"]) for item in properties], "not(ThermoHasProperty(property$))", "Unknown thermophysical property ID")
    append_text_macro(lines, "ThermoPropertySymbol$", "property", [(item["id"], item["symbol"]) for item in properties], "not(ThermoHasProperty(property$))", "Unknown thermophysical property ID")
    append_text_macro(lines, "ThermoPropertyUnit$", "property", [(item["id"], item["unit_label"]) for item in properties], "not(ThermoHasProperty(property$))", "Unknown thermophysical property ID")
    append_text_macro(lines, "ThermoSourceName$", "source", [(item["id"], item["name"]) for item in sources], "not(ThermoHasSource(source$))", "Unknown thermophysical source ID")
    append_text_macro(lines, "ThermoSourceCitation$", "source", [(item["id"], item["citation"]) for item in sources], "not(ThermoHasSource(source$))", "Unknown thermophysical source ID")
    append_text_macro(lines, "ThermoSourceRevision$", "source", [(item["id"], item["revision"]) for item in sources], "not(ThermoHasSource(source$))", "Unknown thermophysical source ID")
    append_text_macro(lines, "ThermoSourceLicense$", "source", [(item["id"], item["license"]) for item in sources], "not(ThermoHasSource(source$))", "Unknown thermophysical source ID")
    append_text_macro(lines, "ThermoSourceNotes$", "source", [(item["id"], item["notes"]) for item in sources], "not(ThermoHasSource(source$))", "Unknown thermophysical source ID")

    lines.extend(
        (
            "#def ShowThermoDatasetSummary$",
            "    #novar",
            "    '<table class=\"bordered data thermo-summary\" style=\"width:95%\"><tbody>",
            "    '<tr><td><strong>Library</strong></td><td>ThermophysicalPropertiesLibraryName$</td></tr>",
            "    '<tr><td><strong>Library revision</strong></td><td>ThermophysicalPropertiesLibraryRevision$</td></tr>",
            "    '<tr><td><strong>Dataset date</strong></td><td>ThermophysicalPropertiesLibraryDate$</td></tr>",
            "    '<tr><td><strong>Scope</strong></td><td>ThermophysicalPropertiesLibraryScope$</td></tr>",
            "    '<tr><td><strong>Fluid count</strong></td><td>'ThermoFluidCount'</td></tr>",
            "    '<tr><td><strong>Property count</strong></td><td>'ThermoPropertyCount'</td></tr>",
            "    '<tr><td><strong>Curve count</strong></td><td>'ThermoCurveCount'</td></tr>",
            "    '<tr><td><strong>Data point count</strong></td><td>'ThermoPointCount'</td></tr>",
            "    '<tr><td><strong>Dataset status</strong></td><td>",
            "    DBStatus$(ThermoDatasetStatus)",
            "    '</td></tr></tbody></table>",
            "    #equ",
            "#end def",
            "",
            "#def ShowThermoSourceRecord$(source$)",
            "    #hide",
            "    ζTHERMO_source_status = if(ThermoHasSource(source$); DB_OK; DB_ERR_NAME)",
            "    #show",
            "    #novar",
            "    '<table class=\"bordered data thermo-source-record\" style=\"width:95%\"><tbody>",
            "    '<tr><td><strong>Source ID</strong></td><td>'source$'</td></tr>",
            "    '<tr><td><strong>Name</strong></td><td>",
            "    ThermoSourceName$(source$)",
            "    '</td></tr>",
            "    '<tr><td><strong>Citation</strong></td><td>",
            "    ThermoSourceCitation$(source$)",
            "    '</td></tr>",
            "    '<tr><td><strong>Revision</strong></td><td>",
            "    ThermoSourceRevision$(source$)",
            "    '</td></tr>",
            "    '<tr><td><strong>License</strong></td><td>",
            "    ThermoSourceLicense$(source$)",
            "    '</td></tr>",
            "    '<tr><td><strong>Qualification note</strong></td><td>",
            "    ThermoSourceNotes$(source$)",
            "    '</td></tr>",
            "    '<tr><td><strong>Status</strong></td><td>",
            "    DBStatus$(ζTHERMO_source_status)",
            "    '</td></tr></tbody></table>",
            "    #equ",
            "#end def",
            "",
            "#def ShowThermoFluidRecord$(fluid$)",
            "    #hide",
            "    ζTHERMO_fluid_status = ThermoFluidStatus(fluid$)",
            "    ζTHERMO_concentration = ThermoFluidConcentrationMassFraction(fluid$)",
            "    #show",
            "    #novar",
            "    '<table class=\"bordered data thermo-fluid-record\" style=\"width:95%\"><tbody>",
            "    '<tr><td><strong>Fluid ID</strong></td><td>'fluid$'</td></tr>",
            "    '<tr><td><strong>Name</strong></td><td>",
            "    ThermoFluidName$(fluid$)",
            "    '</td></tr>",
            "    '<tr><td><strong>Description</strong></td><td>",
            "    ThermoFluidDescription$(fluid$)",
            "    '</td></tr>",
            "    #if not(DBIsMissing(ζTHERMO_concentration))",
            "        '<tr><td><strong>Mass concentration</strong></td><td>'ζTHERMO_concentration'</td></tr>",
            "    #end if",
            "    '<tr><td><strong>Status</strong></td><td>",
            "    DBStatus$(ζTHERMO_fluid_status)",
            "    '</td></tr></tbody></table>",
            "    #equ",
            "#end def",
            "",
            "#def ShowThermoProperty$(fluid$; property$; temperature$)",
            "    #hide",
            "    ζTHERMO_temperature = temperature$",
            "    ζTHERMO_property_status = ThermoPROPStatus(fluid$; property$; ζTHERMO_temperature; DB_LINEAR; DB_STRICT)",
            "    ζTHERMO_property_value = ThermoPROP(fluid$; property$; ζTHERMO_temperature)",
            "    ζTHERMO_source = if(DBIsFatal(ζTHERMO_property_status); 0; ThermoSourceID(fluid$; property$))",
            "    ζTHERMO_revision = if(DBIsFatal(ζTHERMO_property_status); 0; ThermoDataRevision(fluid$; property$))",
            "    ζTHERMO_T_min = if(DBIsFatal(ζTHERMO_property_status); 0°C; ThermoTMin(fluid$; property$))",
            "    ζTHERMO_T_max = if(DBIsFatal(ζTHERMO_property_status); 0°C; ThermoTMax(fluid$; property$))",
            "    #show",
            "    #novar",
            "    '<table class=\"bordered data thermo-property-record\" style=\"width:95%\"><tbody>",
            "    '<tr><td><strong>Fluid</strong></td><td>",
            "    ThermoFluidName$(fluid$)",
            "    '</td></tr>",
            "    '<tr><td><strong>Property</strong></td><td>",
            "    ThermoPropertyName$(property$)",
            "    '</td></tr>",
            "    '<tr><td><strong>Temperature</strong></td><td>'temperature$'</td></tr>",
            "    '<tr><td><strong>Status</strong></td><td>",
            "    DBStatus$(ζTHERMO_property_status)",
            "    '</td></tr>",
            "    #if not(DBIsFatal(ζTHERMO_property_status))",
            "        '<tr><td><strong>Value</strong></td><td>'ζTHERMO_property_value'</td></tr>",
            "        '<tr><td><strong>Valid temperature range</strong></td><td>'ζTHERMO_T_min' to 'ζTHERMO_T_max'</td></tr>",
            "        '<tr><td><strong>Source</strong></td><td>",
            "        ThermoSourceName$(ζTHERMO_source)",
            "        '</td></tr>",
            "        '<tr><td><strong>Data revision ID</strong></td><td>'ζTHERMO_revision'</td></tr>",
            "    #end if",
            "    '</tbody></table>",
            "    #equ",
            "#end def",
            "#show",
            "#else",
            "'<div style=\"margin:1em;padding:0.75em;border:2px solid #b00020;color:#b00020;background:#fff0f2;\"><strong>DRAT library load error:</strong> ThermophysicalProperties requires DataWrapper API 0.3.3 or newer. Load a compatible DratCore.cpd before this library.</div>",
            "#end if",
            "#else",
            "'<div style=\"margin:1em;padding:0.75em;border:2px solid #b00020;color:#b00020;background:#fff0f2;\"><strong>DRAT library load error:</strong> ThermophysicalProperties requires DRAT core API 4.x. Load a compatible DratCore.cpd before this library.</div>",
            "#end if",
            "",
        )
    )
    return "\n".join(lines)


def write_or_check(output_path: Path, generated: str, check: bool) -> None:
    """Check output or atomically replace it after temporary-file verification."""

    try:
        safe_write_or_check(output_path, generated, check)
    except GeneratorError as error:
        raise SchemaError(str(error)) from error


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    """Parse generator command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Schema-version-1 thermophysical JSON source.")
    parser.add_argument("output", type=Path, help="Generated CalcPad library path.")
    parser.add_argument("--check", action="store_true", help="Fail if the committed generated library differs.")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    """Run schema validation and generation, returning a process exit code."""

    options = parse_arguments(sys.argv[1:] if arguments is None else arguments)
    try:
        dataset = load_dataset(options.source)
        generated = generate_library(dataset)
        write_or_check(options.output, generated, options.check)
    except SchemaError as error:
        print(f"Thermophysical generator error: {error}", file=sys.stderr)
        return 1
    action = "Verified" if options.check else "Generated"
    print(f"{action} {options.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
