"""Generate the embedded AISC v16 C and MC channel library from the source workbook."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

from AiscGeneratorSupport import load_family
from GeneratorSupport import GeneratorError, write_or_check


PROPERTIES = [
    ("WEIGHT", "Nominal weight", "lb/ft", "W"), ("AREA", "Area", "in^2", "A"),
    ("D", "Depth", "in", "d"), ("BF", "Flange width", "in", "bf"),
    ("TW", "Web thickness", "in", "tw"), ("TF", "Flange thickness", "in", "tf"),
    ("X", "Centroid x-coordinate", "in", "x"), ("EO", "Shear-center eccentricity", "in", "eo"),
    ("IX", "Strong-axis inertia", "in^4", "Ix"), ("ZX", "Strong-axis plastic modulus", "in^3", "Zx"),
    ("SX", "Strong-axis elastic modulus", "in^3", "Sx"), ("RX", "Strong-axis radius of gyration", "in", "rx"),
    ("IY", "Weak-axis inertia", "in^4", "Iy"), ("ZY", "Weak-axis plastic modulus", "in^3", "Zy"),
    ("SY", "Weak-axis elastic modulus", "in^3", "Sy"), ("RY", "Weak-axis radius of gyration", "in", "ry"),
    ("J", "Torsional constant", "in^4", "J"), ("CW", "Warping constant", "in^6", "Cw"),
]


def n(value: object) -> str:
    return "DB_MISSING" if pd.isna(value) or str(value).strip() in {"–", "-"} else format(float(value), ".12g")


def symbol(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", label.replace(".", "P"))


def build(workbook: Path) -> str:
    data = load_family(workbook, ["C", "MC"], PROPERTIES, {"C": 32, "MC": 40})
    L: list[str] = []
    e = L.append
    e("#if and(DRAT_CORE_API ≥ 10000; DRAT_CORE_API < 50000)"); e("#if and(DRAT_DATA_WRAPPER_API ≥ 302; DRAT_DATA_WRAPPER_API < 1000)")
    e("#hide"); e("'<!-- AISC C and MC channel geometric-property library. Source: AISC Shapes Database v16.0 (August 2023). -->")
    e("#def AiscChannelLibraryName$ = AISC C and MC Channel Structural Sections Library"); e("#def AiscChannelLibraryRevision$ = 0.1.0"); e("#def AiscChannelLibraryDate$ = 2026-08-10")
    e("#def AiscChannelLibrarySource$ = AISC Shapes Database v16.0, August 2023. https://www.aisc.org/aisc/publications/steel-construction-manual/aisc-shapes-database-v160/")
    e("#def AiscChannelLibraryScope$ = 32 AISC C and 40 MC channels with tabulated US customary geometric properties. This library does not provide material strength, member capacity, or code checks.")
    e("#show"); e("'<style>table.data.channel-record td:nth-child(2),table.data.channel-record td:nth-child(2) p,table.data.channel-property td:nth-child(2),table.data.channel-property td:nth-child(2) p,table.data.channel-summary td:nth-child(2),table.data.channel-summary td:nth-child(2) p{text-align:right!important;overflow-wrap:anywhere;word-break:break-word;}</style>"); e("#hide")
    for i, row in data.iterrows():
        item, name = 3001 + i, symbol(row["AISC_Manual_Label"])
        e(f"AISC_{name} = {item}"); e(f"{name} = AISC_{name}")
    e("AISC_CHANNEL_C = 1"); e("AISC_CHANNEL_MC = 2")
    e("AiscChannelItemIDs = [" + "; ".join(str(3001+i) for i in range(len(data))) + "]")
    for i, (code, _, _, _) in enumerate(PROPERTIES, 1): e(f"AISC_CHANNEL_P_{code} = {i}")
    e("AiscChannelPropertyIDs = [" + "; ".join(str(i) for i in range(1, len(PROPERTIES)+1)) + "]")
    e("AiscChannelItemCount = len(AiscChannelItemIDs)"); e("AiscChannelPropertyCount = len(AiscChannelPropertyIDs)")
    e("AiscChannelFamilyByItem = [" + "; ".join("1" if row["Type"] == "C" else "2" for _, row in data.iterrows()) + "]")
    e("AiscChannelData = [")
    for i, row in data.iterrows():
        values = "; ".join(n(row[col]) for _, _, _, col in PROPERTIES)
        e(f"{3001+i}; {values}{'|' if i < len(data)-1 else ']'}")
    e("AiscChannelHasItem(item) = DBHasID(AiscChannelItemIDs; item)"); e("AiscChannelHasProperty(property) = DBHasID(AiscChannelPropertyIDs; property)")
    e("AiscChannelPropertyStatus(item; property) = switch(not(AiscChannelHasItem(item)); DB_ERR_NAME; not(AiscChannelHasProperty(property)); DB_ERR_PROPERTY; DBTableStatus(AiscChannelData; item; property + 1))")
    e("AiscChannelPropertyRaw(item; property) = if(DBIsFatal(AiscChannelPropertyStatus(item; property)); 0/0; DBTableRaw(AiscChannelData; item; property + 1))")
    e("AiscChannelApplyUnits(property; value) = switch(property ≡ AISC_CHANNEL_P_WEIGHT; setunits(value; lb/ft); property ≡ AISC_CHANNEL_P_AREA; setunits(value; in^2); or(property ≡ AISC_CHANNEL_P_D; property ≡ AISC_CHANNEL_P_BF; property ≡ AISC_CHANNEL_P_TW; property ≡ AISC_CHANNEL_P_TF; property ≡ AISC_CHANNEL_P_X; property ≡ AISC_CHANNEL_P_EO; property ≡ AISC_CHANNEL_P_RX; property ≡ AISC_CHANNEL_P_RY); setunits(value; in); or(property ≡ AISC_CHANNEL_P_IX; property ≡ AISC_CHANNEL_P_IY; property ≡ AISC_CHANNEL_P_J); setunits(value; in^4); or(property ≡ AISC_CHANNEL_P_ZX; property ≡ AISC_CHANNEL_P_SX; property ≡ AISC_CHANNEL_P_ZY; property ≡ AISC_CHANNEL_P_SY); setunits(value; in^3); property ≡ AISC_CHANNEL_P_CW; setunits(value; in^6); 0/0)")
    e("AiscChannelProperty(item; property) = AiscChannelApplyUnits(property; AiscChannelPropertyRaw(item; property))")
    for code in ["WEIGHT", "AREA", "IX", "SX", "IY", "SY"]: e(f"AiscChannel{code.title()}(item) = AiscChannelProperty(item; AISC_CHANNEL_P_{code})")
    e("AiscChannelItemsAtLeast(property; minimum) = _"); e("$block{"); e("    property_ok = AiscChannelHasProperty(property);"); e("    safe_property = if(property_ok; property; AISC_CHANNEL_P_WEIGHT);"); e("    values = AiscChannelApplyUnits(safe_property; col(AiscChannelData; safe_property + 1));"); e("    if(property_ok; lookup_ge(values; AiscChannelItemIDs; minimum); find_eq([0]; 1; 1));"); e("}")
    e("AiscChannelDataOK = and(AiscChannelItemCount ≡ 72; n_rows(AiscChannelData) ≡ 72; n_cols(AiscChannelData) ≡ AiscChannelPropertyCount + 1; norm_1(sort(col(AiscChannelData; 1)) - sort(AiscChannelItemIDs)) ≡ 0)"); e("AiscChannelDatasetStatus = if(AiscChannelDataOK; DB_OK; DB_ERR_MISSING)")
    e("#def AiscChannelName$(item$)")
    for i, row in data.iterrows(): e(f"    #if item$ ≡ {3001+i}"); e(f"        '{row['AISC_Manual_Label']}"); e("    #end if")
    e("    #if not(AiscChannelHasItem(item$))"); e("        '<span class=\"err\">Unknown AISC channel</span>"); e("    #end if"); e("#end def")
    e("#def AiscChannelPropertyName$(property$)")
    for i, (_, name, _, _) in enumerate(PROPERTIES, 1): e(f"    #if property$ ≡ {i}"); e(f"        '{name}"); e("    #end if")
    e("#end def")
    e("#def ShowAiscChannelDatasetSummary$"); e("    #novar"); e("    '<table class=\"bordered data channel-summary\" style=\"width:95%\"><tbody>")
    e("    '<tr><td><strong>Library</strong></td><td>AiscChannelLibraryName$</td></tr>"); e("    '<tr><td><strong>Library revision</strong></td><td>AiscChannelLibraryRevision$</td></tr>"); e("    '<tr><td><strong>Source</strong></td><td>AiscChannelLibrarySource$</td></tr>"); e("    '<tr><td><strong>Scope</strong></td><td>AiscChannelLibraryScope$</td></tr>"); e("    '<tr><td><strong>Section count</strong></td><td>'AiscChannelItemCount'</td></tr>"); e("    '<tr><td><strong>Property count</strong></td><td>'AiscChannelPropertyCount'</td></tr>"); e("    '<tr><td><strong>Dataset status</strong></td><td>"); e("    DBStatus$(AiscChannelDatasetStatus)"); e("    '</td></tr></tbody></table>"); e("#end def")
    e("#def ShowAiscChannelRecord$(item$)"); e("    #hide"); e("    ζAISC_channel_record_status = if(AiscChannelHasItem(item$); AiscChannelDatasetStatus; DB_ERR_NAME)"); e("    #show"); e("    #novar"); e("    '<table class=\"bordered data channel-record\" style=\"width:95%\"><tbody>")
    e("    '<tr><td><strong>Section</strong></td><td>"); e("    AiscChannelName$(item$)"); e("    '</td></tr>")
    e("    '<tr><td><strong>Section ID</strong></td><td>'item$'</td></tr>")
    e("    '<tr><td><strong>Status</strong></td><td>"); e("    DBStatus$(ζAISC_channel_record_status)"); e("    '</td></tr>")
    e("    '<tr><td><strong>Source</strong></td><td>AiscChannelLibrarySource$</td></tr>")
    e("    '<tr><td><strong>Data basis</strong></td><td>Tabulated geometric properties only; verify the governing AISC edition before design use.</td></tr>")
    e("    '</tbody></table>"); e("#end def")
    e("#def ShowAiscChannelProperties$(item$)"); e("    #hide"); e("    ζAISC_channel_item = item$"); e("    ζAISC_channel_ok = AiscChannelHasItem(ζAISC_channel_item)"); e("    #show"); e("    #novar"); e("    '<table class=\"bordered data channel-property\" style=\"width:95%\"><thead><tr><th>Property</th><th>Value</th></tr></thead><tbody>")
    e("    #if ζAISC_channel_ok"); e("        #for ζAISC_channel_property = 1 : AiscChannelPropertyCount"); e("            #hide"); e("            ζAISC_channel_value = AiscChannelProperty(ζAISC_channel_item; ζAISC_channel_property)"); e("            #show"); e("            '<tr><td style=\"text-align:left\">"); e("            AiscChannelPropertyName$(ζAISC_channel_property)"); e("            '</td><td>'ζAISC_channel_value'</td></tr>"); e("        #loop"); e("    #end if"); e("    #if not(ζAISC_channel_ok)"); e("        '<tr><td colspan=\"2\" class=\"status-cell\">"); e("        DBStatus$(DB_ERR_NAME)"); e("        '</td></tr>"); e("    #end if"); e("    '</tbody></table>"); e("#end def")
    e("#show"); e("#else"); e("'<div class=\"err\">DRAT library load error: AiscChannelSections requires DataWrapper API 0.3.2 or newer.</div>"); e("#end if"); e("#else"); e("'<div class=\"err\">DRAT library load error: AiscChannelSections requires DRAT core API 1.x.</div>"); e("#end if")
    return "\n".join(L) + "\n"


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
        print(f"AISC channel generator error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
