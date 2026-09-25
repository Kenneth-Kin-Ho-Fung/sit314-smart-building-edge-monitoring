from pathlib import Path
import csv
import json

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, Preformatted


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "report" / "assets"
OUT = ROOT / "report" / "project_report_submission_s222575621.pdf"
METRICS = ROOT / "simulation" / "outputs" / "scalability_metrics.csv"


def image(name, width, height=None):
    flow = Image(str(ASSETS / name), width=width, height=height) if height else Image(str(ASSETS / name), width=width)
    flow.hAlign = "CENTER"
    return flow


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D9D9D9"))
    canvas.line(.68 * inch, .50 * inch, 7.58 * inch, .50 * inch)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.setFont("Helvetica", 7.2)
    canvas.drawString(.68 * inch, .33 * inch, "SIT314 6.3D Final Project | Kin Ho Fung | s222575621")
    canvas.drawRightString(7.58 * inch, .33 * inch, f"Page {doc.page}")
    canvas.restoreState()


def table(data, widths, size=7.2):
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="CENTER")
    style = [
        ("GRID", (0, 0), (-1, -1), .32, colors.HexColor("#D6DCE5")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), size),
        ("LEADING", (0, 0), (-1, -1), size + 1.3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    for row in range(2, len(data), 2):
        style.append(("BACKGROUND", (0, row), (-1, row), colors.HexColor("#F5F7FA")))
    t.setStyle(TableStyle(style))
    return t


def main():
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=23, alignment=TA_CENTER, spaceAfter=3)
    sub = ParagraphStyle("sub", parent=styles["Normal"], fontSize=9.5, leading=11.5, alignment=TA_CENTER, spaceAfter=3)
    meta = ParagraphStyle("meta", parent=styles["Normal"], fontSize=7.6, leading=9, alignment=TA_CENTER, textColor=colors.HexColor("#555555"), spaceAfter=6)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=12.4, leading=14.5, spaceBefore=2, spaceAfter=3)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=9.4, leading=11, spaceBefore=3, spaceAfter=2)
    body = ParagraphStyle("body", parent=styles["Normal"], fontName="Helvetica", fontSize=8.05, leading=10.0, spaceAfter=3.5)
    small = ParagraphStyle("small", parent=body, fontSize=7.2, leading=8.6, spaceAfter=2.5)
    cap = ParagraphStyle("cap", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=6.8, leading=8.2, alignment=TA_CENTER, spaceBefore=1, spaceAfter=3)
    source = ParagraphStyle("source", parent=styles["Normal"], fontName="Courier", fontSize=5.35, leading=6.25, leftIndent=0, rightIndent=0)
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=.68 * inch, rightMargin=.68 * inch, topMargin=.47 * inch, bottomMargin=.61 * inch, title="SIT314 6.3D Final Project Report", author="Kin Ho Fung")
    p = lambda text, style=body: Paragraph(text, style)
    story = []

    # Main report: exactly five deliberately labelled pages.
    story += [
        p("Scalable Smart Building Edge Monitoring System", title),
        p("SIT314 Software Architecture and Scalability for IoT - 6.3D Final Project", sub),
        p("Kin Ho Fung | s222575621 | Source: github.com/Kenneth-Kin-Ho-Fung/sit314-smart-building-edge-monitoring", meta),
        p("1. Project outcome and architecture", h1),
        p("This project delivers a working edge-first smart-building monitoring system. A physical ESP32-S3 node samples temperature, humidity, MQ-2 response, motion and flame state, then publishes JSON telemetry to a Raspberry Pi Node.js gateway. The gateway authenticates devices, classifies readings, retains normal telemetry locally and forwards only warning or critical events to Node-RED and AWS Lambda."),
        table([["Layer", "Delivered result"], ["Physical node", "ESP32-S3, DHT, MQ-2, PIR, flame sensor, LED and buzzer"], ["Edge", "Authenticated HTTP ingestion, local filtering, JSONL log and dashboard"], ["Events/cloud", "Node-RED token validation and Lambda classification for non-normal events"], ["Scalability", "Offline 8-400 node model plus live Pi HTTP tests"]], [1.32*inch, 5.28*inch]),
        Spacer(1, 4), image("implemented_architecture.png", 6.25*inch, 3.04*inch),
        p("Figure 1. Implemented architecture: normal readings remain at the Pi; warning/critical events follow the Node-RED to Lambda path.", cap),
        p("Design rationale", h2),
        p("The separation reduces downstream traffic while preserving a physical, independently useful local safety response. The ESP32 can enable its LED/buzzer locally; the Pi maintains the dashboard and event record even when the cloud path is unavailable. The public repository includes the reproducible implementation and safe configuration templates; credentials and runtime logs are excluded."),
        PageBreak(),
        p("2. Physical implementation and edge behaviour", h1),
        p("The node sends device and room identity, sensor data, MQ-2 baseline/delta, readiness, motion, flame and local-alarm state. The MQ-2 is gated by a 15-minute warm-up or manual baseline. This avoids treating early calibration drift as a real gas incident. A ready MQ-2 absolute delta of 180 produces a warning and 320 produces critical; detected flame is always critical."),
        table([["Component", "Final role"], ["ESP32-S3", "Wi-Fi JSON publisher and local LED/buzzer controller"], ["Raspberry Pi", "Node.js gateway on port 3000 with validation, rules, logs and dashboard"], ["Node-RED", "Authenticated POST /edge-events microservice on the Pi"], ["AWS Lambda", "Deployed cloud event classifier with CloudWatch runtime logs"]], [1.45*inch, 5.15*inch]),
        Spacer(1, 4), image("WhatsApp Image 2026-09-25 at 07.30.19.jpeg", 3.75*inch, 2.81*inch),
        p("Figure 2. Physical final prototype: ESP32-S3 with the sensor/alarm circuit and Raspberry Pi edge gateway.", cap),
        p("A real post-baseline sensor event was captured with <i>mq2Ready: true</i>, MQ-2 absolute delta 2,064, alarm ON and an HTTP 200 acknowledgement from the Pi. The gateway classified it as critical. The unedited serial capture is retained as appendix evidence.", small),
        image("physical_to_nodered_forwarding.png", 5.92*inch, 4.10*inch),
        p("Figure 3. Pi dashboard during physical ESP32-S3 traffic: 47 forwarded events and 47 successful Node-RED forwards. Critical entries with low MQ-2 deltas can be flame-triggered.", cap),
        PageBreak(),
        p("3. Scalability evaluation", h1),
        p("The simulator reuses the physical telemetry schema. Its offline capacity model increased virtual rooms from 8 to 400, generating 93,960 readings. It filtered 89,179 normal readings locally and forwarded 4,781 events: a 94.9% reduction in downstream event volume. These figures are a modelled capacity experiment, not a claim that the Pi used 400 real workers."),
        image("scalability_chart.png", 5.55*inch, 1.98*inch),
        p("Figure 4. Offline modelled p95 latency and forwarded-event trend across virtual-node levels.", cap),
        p("The Pi was also tested directly. Four staged live tests sent 1,830 requests to POST /telemetry; all returned 2xx. A separate 10-worker concurrent run sent 250 requests with zero failures (p50 23.73 ms; p95 92.59 ms). The staged runs occurred before adding the device-token header; the supplied simulator now accepts <i>--device-token</i> so the experiment remains reproducible against the authenticated gateway.", small),
        table([["Evidence", "Measured result", "Interpretation"], ["Offline model", "93,960 readings; 94.9% filtered", "Higher-node capacity model"], ["Live staged Pi test", "1,830/1,830 successful HTTP POSTs", "Actual local network gateway timing"], ["Concurrent Pi test", "250/250 successful; 10 workers", "Concurrent client handling, not autoscaling"]], [1.45*inch, 2.1*inch, 3.05*inch], 6.75),
        p("The live gateway's sequential p95 values remained about 34-35 ms. The result supports an edge-first architecture: routine data does not force a dashboard or cloud service to process every measurement. A production rollout should additionally measure CPU, memory, queue depth and packet loss under sustained traffic."),
        PageBreak(),
        p("4. Event microservice and cloud deployment", h1),
        p("The event route was deployed on the Pi: ESP32-S3 -> authenticated Pi gateway -> Node-RED POST /edge-events -> AWS Lambda Function URL. The Node.js gateway sends only non-normal readings and includes X-Edge-Token. Node-RED validates this token before calling the deployed <i>sit314-edge-telemetry</i> Lambda function. This preserves the original physical endpoint while adding an event-driven microservice."),
        image("nodered_lambda_integration_test.png", 6.18*inch, 2.52*inch),
        p("Figure 5. Active Node-RED event route. Debug records an integration payload and the AWS Lambda response with <i>ok: true</i>.", cap),
        image("cloudwatch_lambda_runtime.png", 6.18*inch, 3.16*inch),
        p("Figure 6. CloudWatch START, END and REPORT entries for deployed Lambda invocations. It complements the Node-RED request/response evidence in Figure 5.", cap),
        p("AWS Lambda is a managed service capable of concurrency, but this project does not claim a cloud scale-out benchmark. The traceability table therefore records automatic scaling as partial rather than overstating it. The full flow JSON and Lambda implementation are included in Appendix A.", small),
        PageBreak(),
        p("5. Evaluation, security and traceability", h1),
        p("The final build proves a physical sensing-to-edge-to-event chain: the ESP32 publishes live telemetry, the Pi rules determine local versus forwarded handling, the dashboard records real forwarded events, Node-RED validates non-normal events, and Lambda provides a deployed cloud classifier. The simulator extends the evaluation beyond the single hardware prototype while clearly separating modelled and measured results."),
        p("Security and limitations", h2),
        p("Application-layer authentication is implemented at both boundaries. ESP32 requests include X-Device-Token and the Pi returns HTTP 401 for an unauthorised device. The Pi adds X-Edge-Token on the Node-RED/Lambda path. Shared token values are runtime configuration and are not included in this report or repository. The local ESP32-to-Pi connection remains HTTP on a private lab network, so it authenticates the sender but does not encrypt transport. Production work would use per-device credentials, rotation and HTTPS or MQTT over TLS. MQ-2 remains a gas-risk proxy; a safety deployment requires calibrated and redundant sensors."),
        table([["1.2D / 6.3D requirement", "Status and evidence"], ["Physical IoT prototype", "Delivered: Figures 1-3 and Appendix B"], ["Node.js edge processing", "Delivered: authenticated gateway, filtering, logs and dashboard"], ["Node-RED event architecture", "Delivered: Figure 5 and flow in Appendix A"], ["AWS deployment", "Delivered: Lambda and CloudWatch evidence in Figure 6"], ["Scalability evidence", "Delivered: offline 8-400 model plus 1,830 staged and 250 concurrent live requests"], ["Automatic scaling", "Partial: managed Lambda used; no scale-out benchmark claimed"], ["Secure deployment", "Partial: authenticated boundaries; TLS is future work"]], [2.0*inch, 4.6*inch], 6.55),
        p("Conclusion", h2),
        p("The project demonstrates a credible edge-first IoT architecture with a physical node, operational Pi gateway, event-based Node-RED extension, deployed Lambda integration and reproducible scalability evidence. Filtering 94.9% of modelled routine traffic is the central result: most readings are processed where they are generated, while meaningful events receive the richer downstream treatment."),
        PageBreak(),
    ]

    # Appendices are intentionally outside the five-page report body.
    story += [p("Appendix A. Full project code and configuration", h1), p("The task sheet requests project code and configuration files as an appendix. The following is the complete public, credential-safe source used by the submission. Real Wi-Fi credentials and runtime tokens are deliberately replaced by templates.", small)]
    sources = [
        ("A.1 ESP32-S3 firmware - esp32_s3_final_node.ino", ROOT / "esp32_s3_final_node" / "esp32_s3_final_node.ino"),
        ("A.2 ESP32 configuration template - private_config.h.example", ROOT / "esp32_s3_final_node" / "private_config.h.example"),
        ("A.3 Pi edge gateway - edge_server.js", ROOT / "edge_gateway" / "edge_server.js"),
        ("A.4 Node package configuration - package.json", ROOT / "edge_gateway" / "package.json"),
        ("A.5 Node-RED importable flow - smart_building_edge_flow.json", ROOT / "node_red" / "smart_building_edge_flow.json"),
        ("A.6 AWS Lambda implementation - index.mjs", ROOT / "aws" / "lambda" / "index.mjs"),
        ("A.7 Scalability simulator - simulate_edge_load.py", ROOT / "simulation" / "simulate_edge_load.py"),
    ]
    for index, (heading, path) in enumerate(sources):
        if index:
            story.append(PageBreak())
        story += [p(heading, h2), p(f"Repository path: {path.relative_to(ROOT)}", small), Preformatted(path.read_text(encoding="utf-8"), source)]
    story += [PageBreak(), p("Appendix B. Evidence captures", h1), p("Evidence captures are retained in the same single submission PDF, as required by the task sheet.", small), image("esp32_authenticated_http_200.png", 3.62*inch, 4.70*inch), p("Figure B1. Physical ESP32-S3 authenticated telemetry accepted by the Pi with HTTP 200.", cap), image("unauthorised_request_401.png", 5.45*inch, 3.76*inch), p("Figure B2. Request without X-Device-Token rejected by the Pi gateway with HTTP 401 Unauthorized.", cap), image("codex-clipboard-6f35bdef-0b60-417c-b41f-74fc2efc4e6f.png", 3.55*inch, 6.30*inch), p("Figure B3. Full serial evidence for a physical critical MQ-2 event and successful gateway acknowledgement.", cap)]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


if __name__ == "__main__":
    main()
