"""Generate the embedded AISC v16 single-angle CalcPad library."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

from AiscGeneratorSupport import load_family
from GeneratorSupport import GeneratorError, write_or_check


PROPERTIES = [
    ("WEIGHT", "Nominal weight", "lb/ft", "W"),
    ("AREA", "Area", "in^2", "A"),
    ("D", "Long-leg length", "in", "d"),
    ("B", "Short-leg length", "in", "b"),
    ("T", "Angle thickness", "in", "t"),
    ("X", "Centroid x-coordinate", "in", "x"),
    ("Y", "Centroid y-coordinate", "in", "y"),
    ("IX", "x-axis inertia", "in^4", "Ix"),
    ("ZX", "x-axis plastic modulus", "in^3", "Zx"),
    ("SX", "x-axis elastic modulus", "in^3", "Sx"),
    ("RX", "x-axis radius of gyration", "in", "rx"),
    ("IY", "y-axis inertia", "in^4", "Iy"),
    ("ZY", "y-axis plastic modulus", "in^3", "Zy"),
    ("SY", "y-axis elastic modulus", "in^3", "Sy"),
    ("RY", "y-axis radius of gyration", "in", "ry"),
    ("IZ", "principal z-axis inertia", "in^4", "Iz"),
    ("RZ", "principal z-axis radius of gyration", "in", "rz"),
    ("SZ", "principal z-axis elastic modulus", "in^3", "Sz"),
    ("J", "Torsional constant", "in^4", "J"),
    ("CW", "Warping constant", "in^6", "Cw"),
]


def number(value: object) -> str:
    if pd.isna(value) or str(value).strip() in {"–", "-"}:
        return "DB_MISSING"
    return format(float(value), ".12g")


def symbol(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", label.replace(".", "P"))


def emit(lines: list[str], line: str = "") -> None:
    lines.append(line)


def build(workbook: Path) -> str:
    sections = load_family(workbook, "Angle", ["L"], PROPERTIES, 4001)

    lines: list[str] = []
    emit(lines, "#if and(DRAT_CORE_API ≥ 10000; DRAT_CORE_API < 50000)")
    emit(lines, "#if and(DRAT_DATA_WRAPPER_API ≥ 302; DRAT_DATA_WRAPPER_API < 1000)")
    emit(lines, "#hide")
    emit(lines, "'<!-- AISC single-angle geometric-property library. Source: AISC Shapes Database v16.0 (August 2023). -->")
    emit(lines, "#def AiscAngleLibraryName$ = AISC Single-Angle Structural Sections Library")
    emit(lines, "#def AiscAngleLibraryRevision$ = 0.1.0")
    emit(lines, "#def AiscAngleLibraryDate$ = 2026-08-10")
    emit(lines, "#def AiscAngleLibrarySource$ = AISC Shapes Database v16.0, August 2023. https://www.aisc.org/aisc/publications/steel-construction-manual/aisc-shapes-database-v160/")
    emit(lines, f"#def AiscAngleLibraryScope$ = {len(sections)} AISC single L angles with tabulated US customary geometric properties. Double angles are intentionally excluded.")
    emit(lines, "#show")
    emit(lines, "'<style>table.data.angle-record td:nth-child(2),table.data.angle-record td:nth-child(2) p,table.data.angle-property td:nth-child(2),table.data.angle-property td:nth-child(2) p,table.data.angle-summary td:nth-child(2),table.data.angle-summary td:nth-child(2) p{text-align:right!important;overflow-wrap:anywhere;word-break:break-word;}</style>")
    emit(lines, "#hide")
    for index, row in sections.iterrows():
        item = 4001 + index
        name = symbol(row["AISC_Manual_Label"])
        emit(lines, f"AISC_{name} = {item}")
        emit(lines, f"{name} = AISC_{name}")
    emit(lines)
    emit(lines, "AiscAngleItemIDs = [" + "; ".join(str(4001 + index) for index in range(len(sections))) + "]")
    for index, (code, _, _, _) in enumerate(PROPERTIES, 1):
        emit(lines, f"AISC_ANGLE_P_{code} = {index}")
    emit(lines, "AiscAnglePropertyIDs = [" + "; ".join(str(index) for index in range(1, len(PROPERTIES) + 1)) + "]")
    emit(lines, "AiscAngleItemCount = len(AiscAngleItemIDs)")
    emit(lines, "AiscAnglePropertyCount = len(AiscAnglePropertyIDs)")
    emit(lines, "AiscAngleData = [")
    for index, row in sections.iterrows():
        values = "; ".join(number(row[column]) for _, _, _, column in PROPERTIES)
        emit(lines, f"{4001 + index}; {values}{'|' if index < len(sections) - 1 else ']'}")
    emit(lines)
    emit(lines, "AiscAngleHasItem(item) = DBHasID(AiscAngleItemIDs; item)")
    emit(lines, "AiscAngleHasProperty(property) = DBHasID(AiscAnglePropertyIDs; property)")
    emit(lines, "AiscAnglePropertyStatus(item; property) = switch(not(AiscAngleHasItem(item)); DB_ERR_NAME; not(AiscAngleHasProperty(property)); DB_ERR_PROPERTY; DBTableStatus(AiscAngleData; item; property + 1))")
    emit(lines, "AiscAnglePropertyRaw(item; property) = if(DBIsFatal(AiscAnglePropertyStatus(item; property)); 0/0; DBTableRaw(AiscAngleData; item; property + 1))")
    emit(lines, "AiscAngleApplyUnits(property; value) = switch(property ≡ AISC_ANGLE_P_WEIGHT; setunits(value; lb/ft); property ≡ AISC_ANGLE_P_AREA; setunits(value; in^2); or(property ≡ AISC_ANGLE_P_D; property ≡ AISC_ANGLE_P_B; property ≡ AISC_ANGLE_P_T; property ≡ AISC_ANGLE_P_X; property ≡ AISC_ANGLE_P_Y; property ≡ AISC_ANGLE_P_RX; property ≡ AISC_ANGLE_P_RY; property ≡ AISC_ANGLE_P_RZ); setunits(value; in); or(property ≡ AISC_ANGLE_P_IX; property ≡ AISC_ANGLE_P_IY; property ≡ AISC_ANGLE_P_IZ; property ≡ AISC_ANGLE_P_J); setunits(value; in^4); or(property ≡ AISC_ANGLE_P_ZX; property ≡ AISC_ANGLE_P_SX; property ≡ AISC_ANGLE_P_ZY; property ≡ AISC_ANGLE_P_SY; property ≡ AISC_ANGLE_P_SZ); setunits(value; in^3); property ≡ AISC_ANGLE_P_CW; setunits(value; in^6); 0/0)")
    emit(lines, "AiscAngleProperty(item; property) = AiscAngleApplyUnits(property; AiscAnglePropertyRaw(item; property))")
    for code in ["WEIGHT", "AREA", "IX", "SX", "IY", "SY"]:
        emit(lines, f"AiscAngle{code.title()}(item) = AiscAngleProperty(item; AISC_ANGLE_P_{code})")
    emit(lines, "AiscAngleItemsAtLeast(property; minimum) = _")
    emit(lines, "$block{")
    emit(lines, "    property_ok = AiscAngleHasProperty(property);")
    emit(lines, "    safe_property = if(property_ok; property; AISC_ANGLE_P_WEIGHT);")
    emit(lines, "    values = AiscAngleApplyUnits(safe_property; col(AiscAngleData; safe_property + 1));")
    emit(lines, "    items = if(property_ok; lookup_ge(values; AiscAngleItemIDs; minimum); find_eq([0]; 1; 1));")
    emit(lines, "    items;")
    emit(lines, "}")
    emit(lines, "AiscAngleDataOK = and(n_rows(AiscAngleData) ≡ AiscAngleItemCount; n_cols(AiscAngleData) ≡ AiscAnglePropertyCount + 1; norm_1(sort(col(AiscAngleData; 1)) - sort(AiscAngleItemIDs)) ≡ 0)")
    emit(lines, "AiscAngleDatasetStatus = if(AiscAngleDataOK; DB_OK; DB_ERR_MISSING)")
    emit(lines)
    emit(lines, "#def AiscAngleName$(item$)")
    for index, row in sections.iterrows():
        emit(lines, f"    #if item$ ≡ {4001 + index}")
        emit(lines, f"        '{row['AISC_Manual_Label']}")
        emit(lines, "    #end if")
    emit(lines, "    #if not(AiscAngleHasItem(item$))")
    emit(lines, "        '<span class=\"err\">Unknown AISC single angle</span>")
    emit(lines, "    #end if")
    emit(lines, "#end def")
    emit(lines, "#def AiscAnglePropertyName$(property$)")
    for index, (_, name, _, _) in enumerate(PROPERTIES, 1):
        emit(lines, f"    #if property$ ≡ {index}")
        emit(lines, f"        '{name}")
        emit(lines, "    #end if")
    emit(lines, "#end def")
    emit(lines, "#def ShowAiscAngleDatasetSummary$")
    emit(lines, "    #novar")
    emit(lines, "    '<table class=\"bordered data angle-summary\" style=\"width:95%\"><tbody>")
    for label, value in [("Library", "AiscAngleLibraryName$"), ("Library revision", "AiscAngleLibraryRevision$"), ("Source", "AiscAngleLibrarySource$"), ("Scope", "AiscAngleLibraryScope$")]:
        emit(lines, f"    '<tr><td><strong>{label}</strong></td><td>{value}</td></tr>")
    emit(lines, "    '<tr><td><strong>Section count</strong></td><td>'AiscAngleItemCount'</td></tr>")
    emit(lines, "    '<tr><td><strong>Property count</strong></td><td>'AiscAnglePropertyCount'</td></tr>")
    emit(lines, "    '<tr><td><strong>Dataset status</strong></td><td>")
    emit(lines, "    DBStatus$(AiscAngleDatasetStatus)")
    emit(lines, "    '</td></tr></tbody></table>")
    emit(lines, "#end def")
    emit(lines, "#def ShowAiscAngleRecord$(item$)")
    emit(lines, "    #hide")
    emit(lines, "    ζAISC_angle_record_status = if(AiscAngleHasItem(item$); AiscAngleDatasetStatus; DB_ERR_NAME)")
    emit(lines, "    #show")
    emit(lines, "    #novar")
    emit(lines, "    '<table class=\"bordered data angle-record\" style=\"width:95%\"><tbody>")
    emit(lines, "    '<tr><td><strong>Section</strong></td><td>")
    emit(lines, "    AiscAngleName$(item$)")
    emit(lines, "    '</td></tr>")
    emit(lines, "    '<tr><td><strong>Section ID</strong></td><td>'item$'</td></tr>")
    emit(lines, "    '<tr><td><strong>Status</strong></td><td>")
    emit(lines, "    DBStatus$(ζAISC_angle_record_status)")
    emit(lines, "    '</td></tr>")
    emit(lines, "    '<tr><td><strong>Source</strong></td><td>AiscAngleLibrarySource$</td></tr>")
    emit(lines, "    '<tr><td><strong>Data basis</strong></td><td>Tabulated geometric properties only; verify the governing AISC edition before design use.</td></tr>")
    emit(lines, "    '</tbody></table>")
    emit(lines, "#end def")
    emit(lines, "#def ShowAiscAngleProperties$(item$)")
    emit(lines, "    #hide")
    emit(lines, "    ζAISC_angle_item = item$")
    emit(lines, "    ζAISC_angle_item_ok = AiscAngleHasItem(ζAISC_angle_item)")
    emit(lines, "    #show")
    emit(lines, "    #novar")
    emit(lines, "    '<table class=\"bordered data angle-property\" style=\"width:95%\"><thead><tr><th>Property</th><th>Value</th></tr></thead><tbody>")
    emit(lines, "    #if ζAISC_angle_item_ok")
    emit(lines, "        #for ζAISC_angle_property = 1 : AiscAnglePropertyCount")
    emit(lines, "            #hide")
    emit(lines, "            ζAISC_angle_value = AiscAngleProperty(ζAISC_angle_item; ζAISC_angle_property)")
    emit(lines, "            #show")
    emit(lines, "            '<tr><td style=\"text-align:left\">")
    emit(lines, "            AiscAnglePropertyName$(ζAISC_angle_property)")
    emit(lines, "            '</td><td>'ζAISC_angle_value'</td></tr>")
    emit(lines, "        #loop")
    emit(lines, "    #end if")
    emit(lines, "    #if not(ζAISC_angle_item_ok)")
    emit(lines, "        '<tr><td colspan=\"2\" class=\"status-cell\">")
    emit(lines, "        DBStatus$(DB_ERR_NAME)")
    emit(lines, "        '</td></tr>")
    emit(lines, "    #end if")
    emit(lines, "    '</tbody></table>")
    emit(lines, "#end def")
    emit(lines, "#show")
    emit(lines, "#else")
    emit(lines, "'<div style=\"margin:1em;padding:0.75em;border:2px solid #b00020;color:#b00020;background:#fff0f2;\"><strong>DRAT library load error:</strong> AiscAngleSections requires DataWrapper API 0.3.2 or newer. Load a compatible DratCore.cpd before this library.</div>")
    emit(lines, "#end if")
    emit(lines, "#else")
    emit(lines, "'<div style=\"margin:1em;padding:0.75em;border:2px solid #b00020;color:#b00020;background:#fff0f2;\"><strong>DRAT library load error:</strong> AiscAngleSections requires DRAT core API 1.x. Load DratCore.cpd before this library.</div>")
    emit(lines, "#end if")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Repository-owned DRAT structural-section source workbook.")
    parser.add_argument("output", help="Generated CalcPad library path or - for stdout.")
    parser.add_argument("--check", action="store_true", help="Fail if the committed generated library differs.")
    options = parser.parse_args()
    try:
        output = build(options.source)
        if options.output == "-":
            if options.check:
                raise GeneratorError("--check requires a file output path.")
            print(output, end="")
        else:
            write_or_check(Path(options.output), output, options.check)
    except (GeneratorError, OSError, ValueError) as error:
        print(f"AISC angle generator error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
