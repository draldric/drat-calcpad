"""Generate the embedded AISC v16 W-shape CalcPad library from the source workbook.

The generated .cpd is committed; this helper is retained to make its source-data
transformation auditable. Run it with the official workbook path as its argument.
"""

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
    ("D", "Depth", "in", "d"),
    ("BF", "Flange width", "in", "bf"),
    ("TW", "Web thickness", "in", "tw"),
    ("TF", "Flange thickness", "in", "tf"),
    ("IX", "Strong-axis inertia", "in^4", "Ix"),
    ("ZX", "Strong-axis plastic modulus", "in^3", "Zx"),
    ("SX", "Strong-axis elastic modulus", "in^3", "Sx"),
    ("RX", "Strong-axis radius of gyration", "in", "rx"),
    ("IY", "Weak-axis inertia", "in^4", "Iy"),
    ("ZY", "Weak-axis plastic modulus", "in^3", "Zy"),
    ("SY", "Weak-axis elastic modulus", "in^3", "Sy"),
    ("RY", "Weak-axis radius of gyration", "in", "ry"),
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
    sections = load_family(workbook, ["W"], PROPERTIES, {"W": 289})

    lines: list[str] = []
    emit(lines, "#if and(DRAT_CORE_API ≥ 10000; DRAT_CORE_API < 50000)")
    emit(lines, "#if and(DRAT_DATA_WRAPPER_API ≥ 302; DRAT_DATA_WRAPPER_API < 1000)")
    emit(lines, "#hide")
    emit(lines, "'<!-- AISC W-shape geometric-property library. Source: AISC Shapes Database v16.0 (August 2023). -->")
    emit(lines, "#def StructuralSectionsLibraryName$ = AISC W-Shape Structural Sections Library")
    emit(lines, "#def StructuralSectionsLibraryRevision$ = 0.1.0")
    emit(lines, "#def StructuralSectionsLibraryDate$ = 2026-08-10")
    emit(lines, "#def StructuralSectionsLibrarySource$ = AISC Shapes Database v16.0, August 2023. https://www.aisc.org/aisc/publications/steel-construction-manual/aisc-shapes-database-v160/")
    emit(lines, "#def StructuralSectionsLibraryScope$ = 289 AISC W-shapes with tabulated US customary geometric properties. This library does not provide material strength, member capacity, or code checks.")
    emit(lines, "#show")
    emit(lines, "'<style>table.data.section-record td:nth-child(2),table.data.section-record td:nth-child(2) p,table.data.section-property td:nth-child(2),table.data.section-property td:nth-child(2) p,table.data.section-summary td:nth-child(2),table.data.section-summary td:nth-child(2) p{text-align:right!important;overflow-wrap:anywhere;word-break:break-word;}</style>")
    emit(lines, "#hide")
    for index, row in sections.iterrows():
        item = 1001 + index
        name = symbol(row["AISC_Manual_Label"])
        emit(lines, f"AISC_{name} = {item}")
        emit(lines, f"{name} = AISC_{name}")
    emit(lines)
    emit(lines, "AiscWItemIDs = [" + "; ".join(str(1001 + index) for index in range(len(sections))) + "]")
    for index, (code, _, _, _) in enumerate(PROPERTIES, 1):
        emit(lines, f"AISC_W_P_{code} = {index}")
    emit(lines, "AiscWPropertyIDs = [1; 2; 3; 4; 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16]")
    emit(lines, "AiscWItemCount = len(AiscWItemIDs)")
    emit(lines, "AiscWPropertyCount = len(AiscWPropertyIDs)")
    emit(lines, "AiscWData = [")
    for index, row in sections.iterrows():
        values = "; ".join(number(row[column]) for _, _, _, column in PROPERTIES)
        end = "|" if index < len(sections) - 1 else "]"
        emit(lines, f"{1001 + index}; {values}{end}")
    emit(lines)
    emit(lines, "AiscWHasItem(item) = DBHasID(AiscWItemIDs; item)")
    emit(lines, "AiscWHasProperty(property) = DBHasID(AiscWPropertyIDs; property)")
    emit(lines, "AiscWPropertyStatus(item; property) = switch(not(AiscWHasItem(item)); DB_ERR_NAME; not(AiscWHasProperty(property)); DB_ERR_PROPERTY; DBTableStatus(AiscWData; item; property + 1))")
    emit(lines, "AiscWPropertyRaw(item; property) = if(DBIsFatal(AiscWPropertyStatus(item; property)); 0/0; DBTableRaw(AiscWData; item; property + 1))")
    emit(lines, "AiscWApplyUnits(property; value) = switch(property ≡ AISC_W_P_WEIGHT; setunits(value; lb/ft); property ≡ AISC_W_P_AREA; setunits(value; in^2); or(property ≡ AISC_W_P_D; property ≡ AISC_W_P_BF; property ≡ AISC_W_P_TW; property ≡ AISC_W_P_TF; property ≡ AISC_W_P_RX; property ≡ AISC_W_P_RY); setunits(value; in); or(property ≡ AISC_W_P_IX; property ≡ AISC_W_P_IY; property ≡ AISC_W_P_J); setunits(value; in^4); or(property ≡ AISC_W_P_ZX; property ≡ AISC_W_P_SX; property ≡ AISC_W_P_ZY; property ≡ AISC_W_P_SY); setunits(value; in^3); property ≡ AISC_W_P_CW; setunits(value; in^6); 0/0)")
    emit(lines, "AiscWProperty(item; property) = AiscWApplyUnits(property; AiscWPropertyRaw(item; property))")
    for code in ["WEIGHT", "AREA", "IX", "SX", "IY", "SY"]:
        emit(lines, f"AiscW{code.title()}(item) = AiscWProperty(item; AISC_W_P_{code})")
    emit(lines, "AiscWItemsAtLeast(property; minimum) = _")
    emit(lines, "$block{")
    emit(lines, "    property_ok = AiscWHasProperty(property);")
    emit(lines, "    safe_property = if(property_ok; property; AISC_W_P_WEIGHT);")
    emit(lines, "    values = AiscWApplyUnits(safe_property; col(AiscWData; safe_property + 1));")
    emit(lines, "    items = if(property_ok; lookup_ge(values; AiscWItemIDs; minimum); find_eq([0]; 1; 1));")
    emit(lines, "    items;")
    emit(lines, "}")
    emit(lines, "AiscWDataOK = and(AiscWItemCount ≡ 289; n_rows(AiscWData) ≡ AiscWItemCount; n_cols(AiscWData) ≡ AiscWPropertyCount + 1; norm_1(sort(col(AiscWData; 1)) - sort(AiscWItemIDs)) ≡ 0)")
    emit(lines, "AiscWDatasetStatus = if(AiscWDataOK; DB_OK; DB_ERR_MISSING)")
    emit(lines)
    emit(lines, "#def AiscWName$(item$)")
    for index, row in sections.iterrows():
        emit(lines, f"    #if item$ ≡ {1001 + index}")
        emit(lines, f"        '{row['AISC_Manual_Label']}")
        emit(lines, "    #end if")
    emit(lines, "    #if not(AiscWHasItem(item$))")
    emit(lines, "        '<span class=\"err\">Unknown AISC W-shape</span>")
    emit(lines, "    #end if")
    emit(lines, "#end def")
    emit(lines, "#def AiscWPropertyName$(property$)")
    for index, (_, name, _, _) in enumerate(PROPERTIES, 1):
        emit(lines, f"    #if property$ ≡ {index}")
        emit(lines, f"        '{name}")
        emit(lines, "    #end if")
    emit(lines, "#end def")
    emit(lines, "#def AiscWPropertyUnit$(property$)")
    for index, (_, _, unit, _) in enumerate(PROPERTIES, 1):
        emit(lines, f"    #if property$ ≡ {index}")
        emit(lines, f"        '{unit}")
        emit(lines, "    #end if")
    emit(lines, "#end def")
    emit(lines, "#def ShowAiscWDatasetSummary$")
    emit(lines, "    #novar")
    emit(lines, "    '<table class=\"bordered data section-summary\" style=\"width:95%\"><tbody>")
    for label, value in [("Library", "StructuralSectionsLibraryName$"), ("Library revision", "StructuralSectionsLibraryRevision$"), ("Source", "StructuralSectionsLibrarySource$"), ("Scope", "StructuralSectionsLibraryScope$")]:
        emit(lines, f"    '<tr><td><strong>{label}</strong></td><td>{value}</td></tr>")
    emit(lines, "    '<tr><td><strong>Section count</strong></td><td>'AiscWItemCount'</td></tr>")
    emit(lines, "    '<tr><td><strong>Property count</strong></td><td>'AiscWPropertyCount'</td></tr>")
    emit(lines, "    '<tr><td><strong>Dataset status</strong></td><td>")
    emit(lines, "    DBStatus$(AiscWDatasetStatus)")
    emit(lines, "    '</td></tr></tbody></table>")
    emit(lines, "#end def")
    emit(lines, "#def ShowAiscWRecord$(item$)")
    emit(lines, "    #hide")
    emit(lines, "    ζAISC_record_status = if(AiscWHasItem(item$); AiscWDatasetStatus; DB_ERR_NAME)")
    emit(lines, "    #show")
    emit(lines, "    #novar")
    emit(lines, "    '<table class=\"bordered data section-record\" style=\"width:95%\"><tbody>")
    emit(lines, "    '<tr><td><strong>Section</strong></td><td>")
    emit(lines, "    AiscWName$(item$)")
    emit(lines, "    '</td></tr>")
    emit(lines, "    '<tr><td><strong>Section ID</strong></td><td>'item$'</td></tr>")
    emit(lines, "    '<tr><td><strong>Status</strong></td><td>")
    emit(lines, "    DBStatus$(ζAISC_record_status)")
    emit(lines, "    '</td></tr>")
    emit(lines, "    '<tr><td><strong>Source</strong></td><td>StructuralSectionsLibrarySource$</td></tr>")
    emit(lines, "    '<tr><td><strong>Data basis</strong></td><td>Tabulated geometric properties only; verify the governing AISC edition before design use.</td></tr>")
    emit(lines, "    '</tbody></table>")
    emit(lines, "#end def")
    emit(lines, "#def ShowAiscWProperties$(item$)")
    emit(lines, "    #hide")
    emit(lines, "    ζAISC_property_item = item$")
    emit(lines, "    ζAISC_property_item_ok = AiscWHasItem(ζAISC_property_item)")
    emit(lines, "    #show")
    emit(lines, "    #novar")
    emit(lines, "    '<table class=\"bordered data section-property\" style=\"width:95%\"><thead><tr><th>Property</th><th>Value</th></tr></thead><tbody>")
    emit(lines, "    #if ζAISC_property_item_ok")
    emit(lines, "        #for ζAISC_property = 1 : AiscWPropertyCount")
    emit(lines, "            #hide")
    emit(lines, "            ζAISC_property_value = AiscWProperty(ζAISC_property_item; ζAISC_property)")
    emit(lines, "            #show")
    emit(lines, "            '<tr><td style=\"text-align:left\">")
    emit(lines, "            AiscWPropertyName$(ζAISC_property)")
    emit(lines, "            '</td><td>'ζAISC_property_value'</td></tr>")
    emit(lines, "        #loop")
    emit(lines, "    #end if")
    emit(lines, "    #if not(ζAISC_property_item_ok)")
    emit(lines, "        '<tr><td colspan=\"2\" class=\"status-cell\">")
    emit(lines, "        DBStatus$(DB_ERR_NAME)")
    emit(lines, "        '</td></tr>")
    emit(lines, "    #end if")
    emit(lines, "    '</tbody></table>")
    emit(lines, "#end def")
    emit(lines, "#show")
    emit(lines, "#else")
    emit(lines, "'<div style=\"margin:1em;padding:0.75em;border:2px solid #b00020;color:#b00020;background:#fff0f2;\"><strong>DRAT library load error:</strong> StructuralSections requires DataWrapper API 0.3.2 or newer. Load a compatible DratCore.cpd before this library.</div>")
    emit(lines, "#end if")
    emit(lines, "#else")
    emit(lines, "'<div style=\"margin:1em;padding:0.75em;border:2px solid #b00020;color:#b00020;background:#fff0f2;\"><strong>DRAT library load error:</strong> StructuralSections requires DRAT core API 1.x. Load DratCore.cpd before this library.</div>")
    emit(lines, "#end if")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Official AISC Shapes Database v16.0 workbook.")
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
        print(f"AISC W generator error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
