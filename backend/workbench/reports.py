from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT


def generate_note(state, target: Path):
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.top_margin = section.bottom_margin = Inches(.75)
    section.left_margin = section.right_margin = Inches(.8)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Calibri", Pt(11)
    normal.paragraph_format.space_after = Pt(8)
    for name in ("Title", "Subtitle", "Heading 1", "Heading 2"):
        doc.styles[name].font.color.rgb = RGBColor(0, 0, 0)
    doc.core_properties.title = "Inspection review draft"
    doc.add_paragraph("Inspection review draft", "Title")
    doc.add_paragraph("Engineering review required. No approval verdict has been issued.")
    if state.get("synthetic"):
        doc.add_paragraph("Synthetic demonstration data. Do not use this note for an operating decision.")
    doc.add_paragraph(f"Job {state['job_id']}\nSource {state.get('name', 'Inspection report')}")
    if state.get("source_sha256"):
        digest = doc.add_paragraph("Source SHA256 " + state["source_sha256"])
        digest.paragraph_format.space_after = Pt(12)
        for run in digest.runs:
            run.font.size = Pt(9)
    doc.add_heading("Measurements for source verification", 1)
    table = doc.add_table(rows=1, cols=4)
    table.autofit = False
    widths = [1.5, 1.7, 1.7, 1.5]
    for cell, text, width in zip(table.rows[0].cells, ("Asset tag", "Thickness", "Pressure", "Source"), widths):
        cell.text, cell.width = text, Inches(width)
    repeat_header = OxmlElement("w:tblHeader")
    table.rows[0]._tr.get_or_add_trPr().append(repeat_header)
    for value in state.get("measurements", []):
        cells = table.add_row().cells
        fields = [value["tag"], f"{value['thickness']:g} {value['thickness_unit']}",
                  f"{value['pressure']:g} {value['pressure_unit']}" if value.get("pressure") is not None else "Not extracted",
                  f"Report page {value['page']}"]
        for cell, text, width in zip(cells, fields, widths):
            cell.text, cell.width = text, Inches(width)
    for i, row in enumerate(table.rows):
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            props = cell._tc.get_or_add_tcPr()
            borders = OxmlElement("w:tcBorders")
            for edge in ("top", "left", "bottom", "right"):
                border = OxmlElement("w:"+edge)
                for key, value in (("val", "single"), ("sz", "4"), ("color", "D9D9D9")):
                    border.set(qn("w:"+key), value)
                borders.append(border)
            props.append(borders)
            shading = OxmlElement("w:shd")
            shading.set(qn("w:fill"), "E7EEF4" if i == 0 else "FFFFFF" if i % 2 else "F5F7F9")
            props.append(shading)
            margins = OxmlElement("w:tcMar")
            for edge in ("top", "left", "bottom", "right"):
                margin = OxmlElement("w:"+edge)
                margin.set(qn("w:w"), "100")
                margin.set(qn("w:type"), "dxa")
                margins.append(margin)
            props.append(margins)
    doc.add_paragraph()
    doc.add_heading("Calculation and decision status", 1)
    summary = state.get("summary")
    if summary:
        doc.add_paragraph(f"The independently checked measurement summary contains {summary['count']} readings. "
            f"Minimum thickness is {summary['minimum_thickness_mm']:g} mm; mean thickness is {summary['mean_thickness_mm']:.3f} mm. "
            "These descriptive values do not establish fitness for service.")
    else:
        doc.add_paragraph("The sandbox calculation was unavailable. No computed result is presented.")
    doc.add_paragraph("Safety factor and remaining life have not been evaluated. Approved engineering formulas, "
                      "thresholds, units and governing standard editions are required before this branch can be enabled.")
    sources = state.get("retrieval", {}).get("sources", [])
    doc.add_heading("Local knowledge evidence", 1)
    doc.add_paragraph("Retrieval mode " + state.get("retrieval", {}).get("mode", "empty"))
    if not sources:
        doc.add_paragraph("No applicable local source was retrieved. No SOP limit is asserted.")
    for i, source in enumerate(sources, 1):
        marker = " Synthetic fixture." if source.get("synthetic") else ""
        doc.add_paragraph(f"[{i}] {source['name']}, page {source['page']}, {source['section']}.{marker}\n{source['text'][:900]}")
    doc.add_heading("Required review", 1)
    warnings = state.get("warnings", [])
    for warning in warnings[:20]:
        doc.add_paragraph(warning, style="List Bullet")
    doc.add_paragraph("Verify each reading against its source page and supply the approved engineering rules. "
                      "A recorded human review does not convert this draft into an engineering approval.")
    target.parent.mkdir(parents=True, exist_ok=True)
    doc.save(target)
    return target
