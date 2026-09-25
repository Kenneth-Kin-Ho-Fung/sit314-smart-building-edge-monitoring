from pathlib import Path
import csv
import shutil

import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "report"
ASSET_DIR = OUT_DIR / "assets"
OUT_DOCX = OUT_DIR / "SIT314_6_3D_Final_Project_Report_s222575621.docx"

SERIAL = Path(r"C:\Users\Blade\AppData\Local\Temp\codex-clipboard-6f35bdef-0b60-417c-b41f-74fc2efc4e6f.png")
DASHBOARD = Path(r"C:\Users\Blade\AppData\Local\Temp\codex-clipboard-d5c2f5a7-a4c0-46a4-85f7-61078023f11c.png")
TERMINAL = Path(r"C:\Users\Blade\AppData\Local\Temp\codex-clipboard-cbb9e491-e9ea-4ae8-b832-00e3d1827b21.png")
SIMULATION = Path(r"C:\Users\Blade\AppData\Local\Temp\codex-clipboard-1a461daf-eb02-4489-821c-551ad79aa0b9.png")
HARDWARE = Path(r"C:\Users\Blade\Downloads\WhatsApp Image 2026-09-25 at 07.30.19.jpeg")
METRICS = ROOT / "simulation" / "outputs" / "scalability_metrics.csv"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_border(cell, color="D9D9D9"):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        edge = borders.find(qn(f"w:{side}"))
        if edge is None:
            edge = OxmlElement(f"w:{side}")
            borders.append(edge)
        edge.set(qn("w:val"), "single")
        edge.set(qn("w:sz"), "4")
        edge.set(qn("w:color"), color)


def set_cell_margins(cell, top=100, start=120, bottom=100, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def style_run(run, bold=False, size=None, color=None, font="Aptos"):
    run.bold = bold
    if size:
        run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor(*color)
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:ascii"), font)
    run._element.rPr.rFonts.set(qn("w:hAnsi"), font)


def add_text(p, text, bold=False, size=None, color=None, italic=False):
    r = p.add_run(text)
    style_run(r, bold, size, color)
    r.italic = italic
    return r


def heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.space_before = Pt(6 if level == 1 else 4)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    style_run(r, True, 15 if level == 1 else 12, (0, 0, 0))
    return p


def body(doc, text, after=5):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.08
    add_text(p, text, size=9.7)
    return p


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(6)
    add_text(p, text, size=8.4, italic=True)
    return p


def add_image(doc, path, width):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(0)
    p.add_run().add_picture(str(path), width=Inches(width))
    return p


def compact_table(doc, headers, rows, widths=None, font_size=8.0):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    hdr = table.rows[0].cells
    for i, label in enumerate(headers):
        cell = hdr[i]
        if widths:
            cell.width = Inches(widths[i])
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_shading(cell, "17365D")
        set_cell_border(cell)
        set_cell_margins(cell)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_text(p, label, True, font_size, (255, 255, 255))
    for ri, row in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cell = cells[i]
            if widths:
                cell.width = Inches(widths[i])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_border(cell)
            set_cell_margins(cell)
            if ri % 2:
                set_cell_shading(cell, "F4F7FA")
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i != 0 else WD_ALIGN_PARAGRAPH.LEFT
            add_text(p, str(value), size=font_size)
    for row in table.rows:
        row._tr.get_or_add_trPr()
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def generate_architecture(path):
    width, height = 1920, 820
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 40)
        body_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 25)
        small_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
    except OSError:
        title_font = body_font = small_font = ImageFont.load_default()
    navy = "#17365D"
    boxes = [
        (50, 245, 350, 525, "Physical room node", "ESP32-S3\nDHT, MQ-2, PIR, flame\nLED and buzzer"),
        (430, 245, 760, 525, "Wi-Fi HTTP JSON", "POST /telemetry\nCommon payload schema\nHTTP 200 acknowledgement"),
        (840, 160, 1160, 440, "Raspberry Pi gateway", "Validate payload\nFilter normal telemetry\nClassify warning and critical"),
        (1240, 160, 1550, 440, "Node-RED event flow", "Token validation\nForward non-normal events\nHTTP response"),
        (1630, 160, 1900, 440, "AWS Lambda", "Classify cloud event\nReturn severity/action\nCloudWatch logs"),
        (840, 540, 1160, 735, "Logs and dashboard", "JSONL telemetry and alerts\nLocal dashboard\nNormal readings retained"),
    ]
    colors = ["#E8F1FB", "#F5F8FC", "#E7F5EA", "#E8EEF9", "#F3E8FC", "#FFF4D8"]
    draw.text((55, 42), "Implemented smart building edge architecture", fill=navy, font=title_font)
    for (x1, y1, x2, y2, title, text), fill in zip(boxes, colors):
        draw.rounded_rectangle((x1, y1, x2, y2), radius=18, fill=fill, outline=navy, width=4)
        draw.text((x1 + 22, y1 + 22), title, fill=navy, font=body_font)
        y = y1 + 86
        for line in text.split("\n"):
            draw.text((x1 + 22, y), line, fill="#17212B", font=small_font)
            y += 36
    for x1, y1, x2, y2 in ((350, 385, 430, 385), (760, 385, 840, 385), (1160, 300, 1240, 300), (1550, 300, 1630, 300)):
        draw.line((x1, y1, x2 - 22, y2), fill=navy, width=6)
        draw.polygon([(x2 - 22, y2 - 13), (x2 - 22, y2 + 13), (x2, y2)], fill=navy)
    draw.line((1000, 440, 1000, 540), fill=navy, width=6)
    draw.polygon([(987, 522), (1013, 522), (1000, 540)], fill=navy)
    img.save(path)


def generate_chart(path, metrics):
    nodes = [int(r["virtualNodes"]) for r in metrics]
    latency = [float(r["p95LatencyMs"]) for r in metrics]
    forwarded = [int(r["forwardedEvents"]) for r in metrics]
    fig, ax1 = plt.subplots(figsize=(9.2, 3.3), dpi=180)
    ax1.plot(nodes, latency, marker="o", color="#1F5AA6", linewidth=2.4, label="p95 latency")
    ax1.set_xlabel("Virtual ESP32-S3 nodes")
    ax1.set_ylabel("p95 latency (ms)", color="#1F5AA6")
    ax1.tick_params(axis="y", labelcolor="#1F5AA6")
    ax1.grid(axis="y", color="#D9E2F3", linewidth=0.8)
    ax1.set_xticks(nodes)
    ax2 = ax1.twinx()
    ax2.plot(nodes, forwarded, marker="s", color="#D97706", linewidth=2.4, label="forwarded events")
    ax2.set_ylabel("Forwarded events", color="#D97706")
    ax2.tick_params(axis="y", labelcolor="#D97706")
    fig.suptitle("Simulation scalability result", x=0.12, ha="left", fontsize=14, fontweight="bold")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def code_block(doc, label, code):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    add_text(p, label, bold=True, size=8.5)
    for line in code.splitlines():
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.18)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.keep_together = True
        r = p.add_run(line)
        style_run(r, size=7.1, font="Consolas")


def main():
    OUT_DIR.mkdir(exist_ok=True)
    ASSET_DIR.mkdir(exist_ok=True)
    for source in (SERIAL, DASHBOARD, TERMINAL, SIMULATION, HARDWARE):
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copy2(source, ASSET_DIR / source.name)

    architecture = ASSET_DIR / "implemented_architecture.png"
    chart = ASSET_DIR / "scalability_chart.png"
    generate_architecture(architecture)
    with METRICS.open(newline="", encoding="utf-8") as f:
        metrics = list(csv.DictReader(f))
    generate_chart(chart, metrics)

    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Inches(0.58)
    sec.bottom_margin = Inches(0.55)
    sec.left_margin = Inches(0.68)
    sec.right_margin = Inches(0.68)

    styles = doc.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"]._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    styles["Normal"]._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    styles["Normal"].font.size = Pt(9.7)
    for style_name in ("Title", "Heading 1", "Heading 2"):
        styles[style_name].font.color.rgb = RGBColor(0, 0, 0)
        styles[style_name].font.name = "Aptos Display"
        styles[style_name]._element.rPr.rFonts.set(qn("w:ascii"), "Aptos Display")
        styles[style_name]._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos Display")

    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_text(footer, "SIT314 6.3D Final Project Report | Kin Ho Fung | s222575621", size=7.5, color=(89, 89, 89))

    # Page 1
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(5)
    add_text(title, "Scalable Smart Building Edge Monitoring System", True, 23)
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.paragraph_format.space_after = Pt(4)
    add_text(sub, "SIT314 Software Architecture and Scalability for IoT", size=11)
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.paragraph_format.space_after = Pt(10)
    add_text(meta, "Final Project Report | Kin Ho Fung | s222575621 | 6.3D", size=9.2, color=(89, 89, 89))
    heading(doc, "Project outcome")
    body(doc, "This final project delivers a working edge-first smart building monitoring system. A physical ESP32-S3 sensor node publishes room telemetry to a Raspberry Pi gateway over Wi-Fi HTTP. The gateway validates and classifies readings, filters routine data locally, records warning and critical events, and exposes a dashboard. A separate simulator uses the same schema to test growth from 8 to 400 virtual room nodes.")
    compact_table(doc, ["Layer", "Delivered evidence"], [
        ("Physical sensing", "ESP32-S3, DHT, MQ-2, PIR, flame sensor, LED and buzzer"),
        ("Edge processing", "HTTP ingestion, normal filtering, event classification, JSONL logs and dashboard"),
        ("Scalability", "93,960 simulated readings across six node-count experiments"),
    ], [1.45, 5.2], 8.2)
    add_image(doc, architecture, 6.65)
    caption(doc, "Figure 1. Implemented architecture. Real and simulated nodes use the same telemetry schema.")
    doc.add_page_break()

    # Page 2
    heading(doc, "Implementation and design decisions")
    body(doc, "The physical node samples temperature, humidity, MQ-2 gas response, motion and flame state. A readable JSON payload includes device and room identity, sensor values, MQ-2 baseline and absolute delta, readiness state and local alarm state. The ESP32 posts the compact JSON payload to POST /telemetry and receives an HTTP 200 acknowledgement from the Raspberry Pi.")
    compact_table(doc, ["Component", "Role in final build", "Implementation detail"], [
        ("ESP32-S3", "Room sensor node", "Wi-Fi HTTP JSON publisher; local LED/buzzer alarm"),
        ("MQ-2", "Air-quality risk proxy", "15-minute warm-up or manual baseline; absolute-delta warning and critical rules"),
        ("Raspberry Pi", "Edge gateway", "Node.js service on port 3000; dashboard and JSONL event logs"),
        ("Simulator", "Scalability test", "Same schema; node counts 8, 25, 50, 100, 200 and 400"),
    ], [1.25, 1.55, 3.85], 7.8)
    heading(doc, "Edge filtering and alert logic", 2)
    body(doc, "The gateway keeps normal readings local and marks warning or critical records for forwarding to the dashboard/event path. Critical classification occurs for a detected flame, a ready MQ-2 absolute delta of at least 320, or a local alarm state. Warning classification starts at an MQ-2 absolute delta of 180. MQ-2 readiness is checked before applying gas thresholds so early calibration drift is not reported as a genuine incident.")
    add_image(doc, HARDWARE, 5.35)
    caption(doc, "Figure 2. Physical final prototype: ESP32-S3 sensor node, DHT, MQ-2, PIR, flame module, LED/buzzer and edge gateway device.")
    doc.add_page_break()

    # Page 3
    heading(doc, "Physical telemetry and safety event evidence")
    body(doc, "The following capture shows a real gas event after the MQ-2 baseline had been set. The ESP32 reports mq2Ready true, a 2,064 absolute delta, local alarm enabled and a successful HTTP 200 response. The gateway classifies the event as critical and records the reasons mq2_critical_delta, local_alarm_latched and motion_context.")
    tbl = doc.add_table(rows=1, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    left, right = tbl.rows[0].cells
    left.width, right.width = Inches(3.7), Inches(2.95)
    for c in (left, right):
        set_cell_border(c)
        set_cell_margins(c, 90, 90, 90, 90)
        c.vertical_alignment = WD_ALIGN_VERTICAL.TOP
    p = left.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(SERIAL), width=Inches(3.45))
    p = right.paragraphs[0]
    add_text(p, "Observed critical event", True, 10.5)
    points = [
        "Temperature: 25.6 C; humidity: 46.5%",
        "MQ-2 raw: 127; baseline: 2191",
        "MQ-2 absolute delta: 2064",
        "MQ-2 ready: true",
        "Alarm output: ON",
        "ESP32 POST result: HTTP 200",
        "Gateway severity: critical",
        "Gateway action: forward_to_cloud_or_dashboard",
    ]
    for point in points:
        q = right.add_paragraph()
        q.paragraph_format.space_after = Pt(5)
        add_text(q, "- " + point, size=8.6)
    caption(doc, "Figure 3. ESP32-S3 critical MQ-2 event sent to the edge gateway and acknowledged successfully.")
    heading(doc, "Why the calibration step matters", 2)
    body(doc, "The MQ-2 heater and sensing element drift while warming up. The firmware waits for a 15-minute warm-up, or accepts a manual b command after the reading stabilises. The result uses an absolute delta rather than only an increasing threshold because testing showed alcohol vapour could move the raw value in either direction.")
    doc.add_page_break()

    # Page 4
    heading(doc, "Edge gateway evidence")
    body(doc, "The browser dashboard demonstrates that the gateway is processing real device data. It displays total received telemetry, normal readings filtered locally, forwarded events, warning and critical counts, the latest JSON reading, recent telemetry and recorded alert reasons. The terminal evidence below confirms the same gateway classified both critical and normal readings in sequence.")
    add_image(doc, DASHBOARD, 6.55)
    caption(doc, "Figure 4. Raspberry Pi edge gateway dashboard showing normal, warning and critical readings from the ESP32-S3 node.")
    add_image(doc, TERMINAL, 3.4)
    caption(doc, "Figure 5. Raspberry Pi terminal log showing critical alerts forwarded and later normal readings filtered locally.")
    doc.add_page_break()

    # Page 5
    heading(doc, "Scalability experiment")
    body(doc, "The simulation reused the physical node's payload structure and increased the number of virtual room nodes from 8 to 400. In total it generated 93,960 readings. Edge filtering retained 89,179 normal readings locally and forwarded 4,781 non-normal events, reducing the event path volume by 94.9%. p95 processing latency increased from 24.45 ms at 8 nodes to 50.27 ms at 400 nodes while the simulated edge worker count increased from 1 to 4.")
    add_image(doc, SIMULATION, 6.55)
    caption(doc, "Figure 6. Completed simulation run across six virtual-node levels.")
    compact_table(doc, ["Nodes", "Generated", "Filtered", "Forwarded", "p95 ms"], [
        (r["virtualNodes"], r["generated"], r["normalFiltered"], r["forwardedEvents"], r["p95LatencyMs"])
        for r in metrics
    ], [0.7, 1.25, 1.25, 1.25, 1.0], 7.5)
    add_image(doc, chart, 6.25)
    caption(doc, "Figure 7. Latency and forwarded-event trend across increasing virtual ESP32-S3 nodes.")
    doc.add_page_break()

    # Page 6
    heading(doc, "Evaluation and conclusion")
    body(doc, "The final build demonstrates the intended separation between sensing, edge processing and scalable workload generation. The physical node validates the end-to-end path: live sensor values are posted to the gateway, a critical MQ-2 event activates the local alarm and the gateway records the event. The normal sequence in the Pi terminal also demonstrates the filtering rule rather than forwarding every reading.")
    body(doc, "The scalability experiment extends this beyond a single prototype. At 400 virtual nodes, 45,515 of 48,000 readings were filtered locally and p95 processing latency remained below 51 ms. The gateway records non-normal data in a format ready for a cloud or dashboard consumer. A future extension would replace the local event destination with a secured cloud endpoint while retaining the same schema and edge rules.")
    heading(doc, "Appendix A Selected code and configuration")
    body(doc, "The core project source is included below as representative implementation evidence. The three files implement the physical node, edge gateway and reproducible load test.", after=3)
    code_block(doc, "ESP32-S3 endpoint and thresholds (esp32_s3_final_node.ino)", "const char* EDGE_TELEMETRY_URL = \"http://192.168.4.55:3000/telemetry\";\nconst unsigned long MQ2_WARMUP_MS = 900000;\nconst int MQ2_WARNING_DELTA = 180;\nconst int MQ2_CRITICAL_DELTA = 320;\nint httpCode = http.POST(payload);")
    code_block(doc, "Raspberry Pi edge rules (edge_server.js)", "const MQ2_WARNING_DELTA = Number(process.env.MQ2_WARNING_DELTA || 180);\nconst MQ2_CRITICAL_DELTA = Number(process.env.MQ2_CRITICAL_DELTA || 320);\nif (mq2Ready && mq2AbsDelta >= MQ2_CRITICAL_DELTA) {\n  severity = \"critical\";\n}\nserver.listen(PORT, \"0.0.0.0\");")
    code_block(doc, "Reproducible scalability command (simulate_edge_load.py)", "python simulation\\simulate_edge_load.py\n# Outputs: simulated_telemetry.jsonl, edge_alerts.jsonl,\n# scalability_metrics.csv and simulation_summary.json")
    heading(doc, "Files and evidence included", 2)
    compact_table(doc, ["File", "Purpose"], [
        ("esp32_s3_final_node.ino", "Sensor reading, calibration, local alarm and HTTP telemetry"),
        ("edge_server.js", "Edge API, classification, dashboard and JSONL logging"),
        ("simulate_edge_load.py", "Repeatable virtual-node scalability experiment"),
        ("scalability_metrics.csv", "Measured node-count results shown in Figure 7"),
    ], [2.5, 4.1], 7.4)

    doc.save(OUT_DOCX)
    print(OUT_DOCX)


if __name__ == "__main__":
    main()
