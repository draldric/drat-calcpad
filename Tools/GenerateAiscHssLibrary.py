"""Generate the embedded AISC v16 HSS CalcPad library from the source workbook."""

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
    ("HT", "Overall height", "in", "Ht"),
    ("B", "Overall width", "in", "B"),
    ("OD", "Outside diameter", "in", "OD"),
    ("TDES", "Design wall thickness", "in", "tdes"),
    ("IX", "Strong-axis inertia", "in^4", "Ix"),
    ("ZX", "Strong-axis plastic modulus", "in^3", "Zx"),
    ("SX", "Strong-axis elastic modulus", "in^3", "Sx"),
    ("RX", "Strong-axis radius of gyration", "in", "rx"),
    ("IY", "Weak-axis inertia", "in^4", "Iy"),
    ("ZY", "Weak-axis plastic modulus", "in^3", "Zy"),
    ("SY", "Weak-axis elastic modulus", "in^3", "Sy"),
    ("RY", "Weak-axis radius of gyration", "in", "ry"),
    ("J", "Torsional constant", "in^4", "J"),
    ("C", "HSS torsional property C", "in^3", "C"),
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
    sections = load_family(workbook, "HSS", ["HSS"], PROPERTIES, {"HSS": 714}, 2001)

    lines: list[str] = []
    emit(lines, "#if and(DRAT_CORE_API ≥ 10000; DRAT_CORE_API < 50000)")
    emit(lines, "#if and(DRAT_DATA_WRAPPER_API ≥ 302; DRAT_DATA_WRAPPER_API < 1000)")
    emit(lines, "#hide")
    emit(lines, "'<!-- AISC HSS geometric-property library. Source: AISC Shapes Database v16.0 (August 2023). -->")
    emit(lines, "#def AiscHssLibraryName$ = AISC HSS Structural Sections Library")
    emit(lines, "#def AiscHssLibraryRevision$ = 0.1.0")
    emit(lines, "#def AiscHssLibraryDate$ = 2026-08-10")
    emit(lines, "#def AiscHssLibrarySource$ = AISC Shapes Database v16.0, August 2023. https://www.aisc.org/aisc/publications/steel-construction-manual/aisc-shapes-database-v160/")
    emit(lines, "#def AiscHssLibraryScope$ = 714 AISC square, rectangular, and round HSS sections with tabulated US customary geometric properties. This library does not provide material strength, member capacity, or code checks.")
    emit(lines, "#show")
    emit(lines, "'<style>table.data.hss-record td:nth-child(2),table.data.hss-record td:nth-child(2) p,table.data.hss-property td:nth-child(2),table.data.hss-property td:nth-child(2) p,table.data.hss-summary td:nth-child(2),table.data.hss-summary td:nth-child(2) p{text-align:right!important;overflow-wrap:anywhere;word-break:break-word;}</style>")
    emit(lines, "#hide")
    for index, row in sections.iterrows():
        item = 2001 + index
        name = symbol(row["AISC_Manual_Label"])
        emit(lines, f"AISC_{name} = {item}")
        emit(lines, f"{name} = AISC_{name}")
    emit(lines)
    emit(lines, "AiscHssItemIDs = [" + "; ".join(str(2001 + index) for index in range(len(sections))) + "]")
    for index, (code, _, _, _) in enumerate(PROPERTIES, 1):
        emit(lines, f"AISC_HSS_P_{code} = {index}")
    emit(lines, "AiscHssPropertyIDs = [1; 2; 3; 4; 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16]")
    emit(lines, "AiscHssItemCount = len(AiscHssItemIDs)")
    emit(lines, "AiscHssPropertyCount = len(AiscHssPropertyIDs)")
    emit(lines, "AiscHssData = [")
    for index, row in sections.iterrows():
        values = "; ".join(number(row[column]) for _, _, _, column in PROPERTIES)
        emit(lines, f"{2001 + index}; {values}{'|' if index < len(sections) - 1 else ']'}")
    emit(lines)
    emit(lines, "AiscHssHasItem(item) = DBHasID(AiscHssItemIDs; item)")
    emit(lines, "AiscHssHasProperty(property) = DBHasID(AiscHssPropertyIDs; property)")
    emit(lines, "AiscHssPropertyStatus(item; property) = switch(not(AiscHssHasItem(item)); DB_ERR_NAME; not(AiscHssHasProperty(property)); DB_ERR_PROPERTY; DBTableStatus(AiscHssData; item; property + 1))")
    emit(lines, "AiscHssPropertyRaw(item; property) = if(DBIsFatal(AiscHssPropertyStatus(item; property)); 0/0; DBTableRaw(AiscHssData; item; property + 1))")
    emit(lines, "AiscHssApplyUnits(property; value) = switch(property ≡ AISC_HSS_P_WEIGHT; setunits(value; lb/ft); property ≡ AISC_HSS_P_AREA; setunits(value; in^2); or(property ≡ AISC_HSS_P_HT; property ≡ AISC_HSS_P_B; property ≡ AISC_HSS_P_OD; property ≡ AISC_HSS_P_TDES; property ≡ AISC_HSS_P_RX; property ≡ AISC_HSS_P_RY); setunits(value; in); or(property ≡ AISC_HSS_P_IX; property ≡ AISC_HSS_P_IY; property ≡ AISC_HSS_P_J); setunits(value; in^4); or(property ≡ AISC_HSS_P_ZX; property ≡ AISC_HSS_P_SX; property ≡ AISC_HSS_P_ZY; property ≡ AISC_HSS_P_SY; property ≡ AISC_HSS_P_C); setunits(value; in^3); 0/0)")
    emit(lines, "AiscHssProperty(item; property) = AiscHssApplyUnits(property; AiscHssPropertyRaw(item; property))")
    for code in ["WEIGHT", "AREA", "IX", "SX", "IY", "SY"]:
        emit(lines, f"AiscHss{code.title()}(item) = AiscHssProperty(item; AISC_HSS_P_{code})")
    emit(lines, "AiscHssItemsAtLeast(property; minimum) = _")
    emit(lines, "$block{")
    emit(lines, "    property_ok = AiscHssHasProperty(property);")
    emit(lines, "    safe_property = if(property_ok; property; AISC_HSS_P_WEIGHT);")
    emit(lines, "    values = AiscHssApplyUnits(safe_property; col(AiscHssData; safe_property + 1));")
    emit(lines, "    items = if(property_ok; lookup_ge(values; AiscHssItemIDs; minimum); find_eq([0]; 1; 1));")
    emit(lines, "    items;")
    emit(lines, "}")
    emit(lines, "AiscHssDataOK = and(AiscHssItemCount ≡ 714; n_rows(AiscHssData) ≡ AiscHssItemCount; n_cols(AiscHssData) ≡ AiscHssPropertyCount + 1; norm_1(sort(col(AiscHssData; 1)) - sort(AiscHssItemIDs)) ≡ 0)")
    emit(lines, "AiscHssDatasetStatus = if(AiscHssDataOK; DB_OK; DB_ERR_MISSING)")
    emit(lines)
    emit(lines, "#def AiscHssName$(item$)")
    for index, row in sections.iterrows():
        emit(lines, f"    #if item$ ≡ {2001 + index}")
        emit(lines, f"        '{row['AISC_Manual_Label']}")
        emit(lines, "    #end if")
    emit(lines, "    #if not(AiscHssHasItem(item$))")
    emit(lines, "        '<span class=\"err\">Unknown AISC HSS section</span>")
    emit(lines, "    #end if")
    emit(lines, "#end def")
    emit(lines, "#def AiscHssPropertyName$(property$)")
    for index, (_, name, _, _) in enumerate(PROPERTIES, 1):
        emit(lines, f"    #if property$ ≡ {index}")
        emit(lines, f"        '{name}")
        emit(lines, "    #end if")
    emit(lines, "#end def")
    emit(lines, "#def ShowAiscHssDatasetSummary$")
    emit(lines, "    #novar")
    emit(lines, "    '<table class=\"bordered data hss-summary\" style=\"width:95%\"><tbody>")
    for label, value in [("Library", "AiscHssLibraryName$"), ("Library revision", "AiscHssLibraryRevision$"), ("Source", "AiscHssLibrarySource$"), ("Scope", "AiscHssLibraryScope$")]:
        emit(lines, f"    '<tr><td><strong>{label}</strong></td><td>{value}</td></tr>")
    emit(lines, "    '<tr><td><strong>Section count</strong></td><td>'AiscHssItemCount'</td></tr>")
    emit(lines, "    '<tr><td><strong>Property count</strong></td><td>'AiscHssPropertyCount'</td></tr>")
    emit(lines, "    '<tr><td><strong>Dataset status</strong></td><td>")
    emit(lines, "    DBStatus$(AiscHssDatasetStatus)")
    emit(lines, "    '</td></tr></tbody></table>")
    emit(lines, "#end def")
    emit(lines, "#def ShowAiscHssRecord$(item$)")
    emit(lines, "    #hide")
    emit(lines, "    ζAISC_hss_record_status = if(AiscHssHasItem(item$); AiscHssDatasetStatus; DB_ERR_NAME)")
    emit(lines, "    #show")
    emit(lines, "    #novar")
    emit(lines, "    '<table class=\"bordered data hss-record\" style=\"width:95%\"><tbody>")
    emit(lines, "    '<tr><td><strong>Section</strong></td><td>")
    emit(lines, "    AiscHssName$(item$)")
    emit(lines, "    '</td></tr>")
    emit(lines, "    '<tr><td><strong>Section ID</strong></td><td>'item$'</td></tr>")
    emit(lines, "    '<tr><td><strong>Status</strong></td><td>")
    emit(lines, "    DBStatus$(ζAISC_hss_record_status)")
    emit(lines, "    '</td></tr>")
    emit(lines, "    '<tr><td><strong>Source</strong></td><td>AiscHssLibrarySource$</td></tr>")
    emit(lines, "    '<tr><td><strong>Data basis</strong></td><td>Tabulated geometric properties only; verify the governing AISC edition before design use.</td></tr>")
    emit(lines, "    '</tbody></table>")
    emit(lines, "#end def")
    emit(lines, "#def ShowAiscHssProperties$(item$)")
    emit(lines, "    #hide")
    emit(lines, "    ζAISC_hss_property_item = item$")
    emit(lines, "    ζAISC_hss_property_item_ok = AiscHssHasItem(ζAISC_hss_property_item)")
    emit(lines, "    ζAISC_hss_is_round = if(ζAISC_hss_property_item_ok; AiscHssPropertyStatus(ζAISC_hss_property_item; AISC_HSS_P_OD) ≡ DB_OK; 0)")
    emit(lines, "    ζAISC_hss_report_properties = if(ζAISC_hss_is_round; [1; 2; 5; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16]; [1; 2; 3; 4; 6; 7; 8; 9; 10; 11; 12; 13; 14; 15; 16])")
    emit(lines, "    ζAISC_hss_report_count = len(ζAISC_hss_report_properties)")
    emit(lines, "    #show")
    emit(lines, "    #novar")
    emit(lines, "    '<table class=\"bordered data hss-property\" style=\"width:95%\"><thead><tr><th>Property</th><th>Value</th></tr></thead><tbody>")
    emit(lines, "    #if ζAISC_hss_property_item_ok")
    emit(lines, "        #for ζAISC_hss_report_index = 1 : ζAISC_hss_report_count")
    emit(lines, "            #hide")
    emit(lines, "            ζAISC_hss_property = take(ζAISC_hss_report_index; ζAISC_hss_report_properties)")
    emit(lines, "            ζAISC_hss_property_value = AiscHssProperty(ζAISC_hss_property_item; ζAISC_hss_property)")
    emit(lines, "            #show")
    emit(lines, "            '<tr><td style=\"text-align:left\">")
    emit(lines, "            AiscHssPropertyName$(ζAISC_hss_property)")
    emit(lines, "            '</td><td>'ζAISC_hss_property_value'</td></tr>")
    emit(lines, "        #loop")
    emit(lines, "    #end if")
    emit(lines, "    #if not(ζAISC_hss_property_item_ok)")
    emit(lines, "        '<tr><td colspan=\"2\" class=\"status-cell\">")
    emit(lines, "        DBStatus$(DB_ERR_NAME)")
    emit(lines, "        '</td></tr>")
    emit(lines, "    #end if")
    emit(lines, "    '</tbody></table>")
    emit(lines, "#end def")
    emit(lines, "#show")
    emit(lines, "#else")
    emit(lines, "'<div style=\"margin:1em;padding:0.75em;border:2px solid #b00020;color:#b00020;background:#fff0f2;\"><strong>DRAT library load error:</strong> AiscHssSections requires DataWrapper API 0.3.2 or newer. Load a compatible DratCore.cpd before this library.</div>")
    emit(lines, "#end if")
    emit(lines, "#else")
    emit(lines, "'<div style=\"margin:1em;padding:0.75em;border:2px solid #b00020;color:#b00020;background:#fff0f2;\"><strong>DRAT library load error:</strong> AiscHssSections requires DRAT core API 1.x. Load DratCore.cpd before this library.</div>")
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
        print(f"AISC HSS generator error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
