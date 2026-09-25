from pathlib import Path
import csv
import json

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, KeepTogether,
)


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "report"
ASSETS = REPORT / "assets"
OUT_PDF = REPORT / "project_report_s222575621.pdf"
METRICS = ROOT / "simulation" / "outputs" / "scalability_metrics.csv"
LIVE_OUTPUTS = [
    ROOT / "simulation" / "outputs" / f"live_pi_{nodes}" / "simulation_summary.json"
    for nodes in (8, 25, 50, 100)
]


def read_live_metrics():
    rows = []
    for path in LIVE_OUTPUTS:
        summary = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(summary["metrics"])
    return rows


def img(name, width, height=None):
    p = ASSETS / name
    flow = Image(str(p), width=width, height=height) if height else Image(str(p), width=width)
    flow.hAlign = "CENTER"
    return flow


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D9D9D9"))
    canvas.line(0.7 * inch, 0.53 * inch, 7.57 * inch, 0.53 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#595959"))
    canvas.drawString(0.7 * inch, 0.35 * inch, "SIT314 6.3D Final Project Report | Kin Ho Fung | s222575621")
    canvas.drawRightString(7.57 * inch, 0.35 * inch, f"Page {doc.page}")
    canvas.restoreState()


def make_table(data, widths, header=True, font_size=7.7):
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="CENTER")
    ts = [
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9D9D9")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
    ]
    if header:
        ts += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ]
        if len(data) > 2:
            for r in range(2, len(data), 2):
                ts.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F4F7FA")))
    table.setStyle(TableStyle(ts))
    return table


def main():
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22,
                           leading=26, alignment=TA_CENTER, textColor=colors.black, spaceAfter=4)
    subtitle = ParagraphStyle("subtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=10.5,
                              leading=13, alignment=TA_CENTER, textColor=colors.black, spaceAfter=3)
    meta = ParagraphStyle("meta", parent=styles["Normal"], fontName="Helvetica", fontSize=8.8,
                          leading=11, alignment=TA_CENTER, textColor=colors.HexColor("#595959"), spaceAfter=9)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14.2,
                        leading=17, textColor=colors.black, spaceBefore=4, spaceAfter=5)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5,
                        leading=13, textColor=colors.black, spaceBefore=5, spaceAfter=3)
    p = ParagraphStyle("body", parent=styles["Normal"], fontName="Helvetica", fontSize=9.25,
                       leading=12.2, spaceAfter=5, textColor=colors.black)
    small = ParagraphStyle("small", parent=p, fontSize=8.0, leading=10)
    caption = ParagraphStyle("caption", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=7.9,
                             leading=9.5, alignment=TA_CENTER, spaceBefore=2, spaceAfter=6)
    bullet = ParagraphStyle("bullet", parent=p, leftIndent=10, firstLineIndent=-7, fontSize=8.4, leading=10.8, spaceAfter=4)
    code = ParagraphStyle("code", parent=styles["Code"], fontName="Courier", fontSize=7.1, leading=8.3,
                          leftIndent=8, spaceAfter=0)

    doc = SimpleDocTemplate(
        str(OUT_PDF), pagesize=A4,
        leftMargin=0.68 * inch, rightMargin=0.68 * inch,
        topMargin=0.55 * inch, bottomMargin=0.66 * inch,
        title="SIT314 6.3D Final Project Report",
        author="Kin Ho Fung",
    )
    story = []
    P = lambda text, style=p: Paragraph(text, style)

    # Page 1
    story += [
        P("Scalable Smart Building Edge Monitoring System", title),
        P("SIT314 Software Architecture and Scalability for IoT", subtitle),
        P("Final Project Report | Kin Ho Fung | s222575621 | 6.3D<br/>Source repository: github.com/Kenneth-Kin-Ho-Fung/sit314-smart-building-edge-monitoring", meta),
        P("Project outcome", h1),
        P("This final project delivers a working edge-first smart building monitoring system. A physical ESP32-S3 sensor node publishes room telemetry to a Raspberry Pi gateway over Wi-Fi HTTP. The gateway validates and classifies readings, filters routine data locally, records warning and critical events, and exposes a dashboard. It forwards only non-normal events through Node-RED to an AWS Lambda classifier. A separate simulator uses the same schema to test growth from 8 to 400 virtual room nodes."),
        make_table([
            ["Layer", "Delivered evidence"],
            ["Physical sensing", "ESP32-S3, DHT, MQ-2, PIR, flame sensor, LED and buzzer"],
            ["Edge processing", "HTTP ingestion, normal filtering, event classification, JSONL logs and dashboard"],
            ["Event and cloud path", "Node-RED token validation and AWS Lambda classification for non-normal events"],
            ["Scalability", "93,960 simulated readings across six node-count experiments"],
        ], [1.5 * inch, 5.25 * inch]),
        Spacer(1, 8),
        img("implemented_architecture.png", 6.55 * inch, 3.18 * inch),
        P("Figure 1. Implemented architecture. Normal telemetry stays at the Pi; non-normal events traverse Node-RED to AWS Lambda.", caption),
        PageBreak(),
    ]

    # Page 2
    story += [
        P("Implementation and design decisions", h1),
        P("The physical node samples temperature, humidity, MQ-2 gas response, motion and flame state. A readable JSON payload includes device and room identity, sensor values, MQ-2 baseline and absolute delta, readiness state and local alarm state. The ESP32 posts compact JSON to POST /telemetry and receives an HTTP 200 acknowledgement from the Raspberry Pi."),
        make_table([
            ["Component", "Role in final build", "Implementation detail"],
            ["ESP32-S3", "Room sensor node", "Wi-Fi HTTP JSON publisher; local LED/buzzer alarm"],
            ["MQ-2", "Air-quality risk proxy", "15-minute warm-up or manual baseline; absolute-delta event rules"],
            ["Raspberry Pi", "Edge gateway", "Node.js service on port 3000; dashboard and JSONL logs"],
            ["Node-RED", "Event microservice", "Authenticates non-normal events on port 1880 and invokes Lambda"],
            ["AWS Lambda", "Cloud classifier", "Returns severity and action for authenticated edge events"],
            ["Simulator", "Scalability test", "Same schema; 8, 25, 50, 100, 200 and 400 virtual nodes"],
        ], [1.18 * inch, 1.5 * inch, 4.07 * inch], font_size=7.55),
        P("Edge filtering and alert logic", h2),
        P("The gateway keeps normal readings local and marks warning or critical records for forwarding to the dashboard/event path. Critical classification occurs for a detected flame or a ready MQ-2 absolute delta of at least 320. Warning classification starts at an MQ-2 absolute delta of 180; a latched local alarm alone is retained as a warning. MQ-2 readiness is checked before gas thresholds are applied so early calibration drift is not reported as a genuine incident."),
        Spacer(1, 2),
        img("WhatsApp Image 2026-09-25 at 07.30.19.jpeg", 5.15 * inch, 3.86 * inch),
        P("Figure 2. Physical final prototype: ESP32-S3 sensor node, DHT, MQ-2, PIR, flame module, LED/buzzer and edge gateway device.", caption),
        PageBreak(),
    ]

    # Page 3
    evidence_points = [
        "<b>Observed critical event</b>",
        "Temperature: 25.6 C; humidity: 46.5%",
        "MQ-2 raw: 127; baseline: 2191",
        "MQ-2 absolute delta: 2064",
        "MQ-2 ready: true",
        "Alarm output: ON",
        "ESP32 POST result: HTTP 200",
        "Gateway severity: critical",
        "Gateway action: forward_to_cloud_or_dashboard",
    ]
    right = [P(x if i == 0 else "- " + x, h2 if i == 0 else bullet) for i, x in enumerate(evidence_points)]
    evidence_table = Table([[img("codex-clipboard-6f35bdef-0b60-417c-b41f-74fc2efc4e6f.png", 3.35 * inch, 5.96 * inch), right]],
                           colWidths=[3.56 * inch, 3.19 * inch], hAlign="CENTER")
    evidence_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9D9D9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [
        P("Physical telemetry and safety event evidence", h1),
        P("This capture shows a real gas event after the MQ-2 baseline had been set. The ESP32 reports mq2Ready true, a 2,064 absolute delta, local alarm enabled and a successful HTTP 200 response. The gateway classifies the event as critical and records the reasons mq2_critical_delta, local_alarm_latched and motion_context."),
        evidence_table,
        P("Figure 3. ESP32-S3 critical MQ-2 event sent to the edge gateway and acknowledged successfully.", caption),
        P("Why the calibration step matters", h2),
        P("The MQ-2 heater and sensing element drift while warming up. The firmware waits for a 15-minute warm-up, or accepts a manual b command after the reading stabilises. Absolute delta detection is used because testing showed alcohol vapour can move the raw value in either direction.", small),
        PageBreak(),
    ]

    # Page 4
    story += [
        P("Physical edge to cloud forwarding evidence", h1),
        P("The updated Raspberry Pi dashboard proves that the physical ESP32-S3 route is connected to the event path. It shows a ready MQ-2 reading from esp32s3-real-01 classified as critical, with flame detection and an absolute gas delta of 2,032. The same screen records 47 forwarded events and 47 successful Node-RED forwards, so no forwarded Pi event was lost between the Node.js gateway and the deployed Node-RED flow."),
        img("physical_to_nodered_forwarding.png", 5.85 * inch, 4.88 * inch),
        P("Figure 4. Real ESP32-S3 critical events forwarded by the Pi gateway to Node-RED (47 successful forwards from 47 forwarded events). Critical rows with low MQ-2 delta are flame-triggered.", caption),
        P("Normal readings remain filter_local_only. Warning and critical events are forwarded asynchronously to Node-RED, which validates the shared token and invokes the AWS Lambda Function URL. This preserves the ESP32 endpoint while adding an event-driven cloud extension.", small),
        PageBreak(),
    ]

    # Page 5
    with METRICS.open(newline="", encoding="utf-8") as f:
        metrics = list(csv.DictReader(f))
    result_rows = [["Nodes", "Generated", "Filtered", "Forwarded", "Modelled p95 ms"]]
    result_rows += [[r["virtualNodes"], r["generated"], r["normalFiltered"], r["forwardedEvents"], r["p95LatencyMs"]] for r in metrics]
    story += [
        P("Scalability experiment", h1),
        P("The offline simulator reused the physical node's payload structure and increased the number of virtual room nodes from 8 to 400. It generated 93,960 readings. Edge filtering retained 89,179 normal readings locally and forwarded 4,781 non-normal events, reducing the modelled event-path volume by 94.9%. Its modelled p95 processing estimate increased from 24.45 ms at 8 nodes to 50.27 ms at 400 nodes. This result is explicitly a repeatable offline capacity model, not a claim that the Pi ran 400 concurrent workers."),
        img("codex-clipboard-1a461daf-eb02-4489-821c-551ad79aa0b9.png", 6.52 * inch, 1.85 * inch),
        P("Figure 5. Completed simulation run across six virtual-node levels.", caption),
        make_table(result_rows, [0.78 * inch, 1.32 * inch, 1.32 * inch, 1.32 * inch, 1.05 * inch], font_size=7.35),
        Spacer(1, 7),
        img("scalability_chart.png", 6.26 * inch, 2.24 * inch),
        P("Figure 6. Offline modelled latency and forwarded-event trend across increasing virtual ESP32-S3 nodes.", caption),
        PageBreak(),
    ]

    # Page 6
    live_metrics = read_live_metrics()
    live_rows = [["Virtual nodes", "POSTs", "2xx", "Failed", "HTTP p50", "HTTP p95"]]
    live_rows += [[
        row["virtualNodes"], row["generated"], row["postOk"], row["postFailed"],
        f"{row['httpP50LatencyMs']} ms", f"{row['httpP95LatencyMs']} ms",
    ] for row in live_metrics]
    story += [
        P("Live gateway load verification", h1),
        P("The simulator was also pointed at the deployed Raspberry Pi endpoint, POST /telemetry at 192.168.4.55:3000. Unlike the offline capacity model, these figures measure the complete local-network HTTP round trip through the running Node.js gateway. Four sequential test levels sent 1,830 telemetry messages in total. Every request returned a 2xx response; the generated schema included normal, warning and critical conditions so the gateway's real classification and logging path were exercised."),
        make_table(live_rows, [1.12 * inch, 0.78 * inch, 0.70 * inch, 0.72 * inch, 1.0 * inch, 1.0 * inch], font_size=7.4),
        P("Table 1. Measured live HTTP timing from the test runner to the deployed Raspberry Pi gateway. The 100-node level sent 1,000 requests with a p95 of 34.73 ms and no failed POSTs. These runs were measured before the later device-token update.", caption),
        P("Interpretation", h2),
        P("The stable p95 range of 34.48-35.26 ms demonstrates that the real single-process gateway handled the staged sequential workload consistently. It does not prove automatic horizontal scaling or a 400-node live concurrent deployment. The separate offline experiment is retained to explore higher virtual node counts and filtering ratios; the two methods are deliberately reported separately to avoid overstating the result."),
        P("A separate concurrent check used 25 simulated identities with 10 readings each, submitted by 10 concurrent workers. All 250 POSTs returned 2xx with zero failures; HTTP p50 was 23.73 ms and p95 was 92.59 ms. This is evidence of concurrent client handling, while still not a claim of automatic horizontal scaling."),
        P("Design evolution from the 1.2D plan", h2),
        P("The early distinction plan proposed MQTT, Node-RED and AWS as later integration layers. The delivered physical route retains HTTP and the Node.js edge service for the ESP32-S3 to Pi hop, then forwards only warning and critical records to Node-RED at POST /edge-events. Node-RED validates an application-layer shared token and invokes the Lambda Function URL. Figure 4 shows this extension operating on real ESP32 events without changing the working ESP32 endpoint."),
        P("AWS deployment verification", h2),
        P("A compatible Node.js 24 AWS Lambda function, <b>sit314-edge-telemetry</b>, was deployed in the Learner Lab us-east-1 region using the supplied LabRole. AWS CloudShell returned status 200 for a ready MQ-2 critical payload. The deployed Node-RED flow was also tested through its internal /edge-events route and returned HTTP 200 after invoking Lambda. The physical ESP32 continues to post to the Pi, so the edge layer remains the first filter rather than exposing every sensor reading to the cloud."),
        make_table([
            ["Cloud evidence", "Observed result"],
            ["Function/runtime", "sit314-edge-telemetry; Node.js 24.x; LabRole; us-east-1"],
            ["CloudShell test", "HTTP 200; critical classification for mq2AbsDelta 420"],
            ["Scaling claim", "Lambda provides managed concurrency; no cloud scale-out benchmark was claimed"],
        ], [1.45 * inch, 5.15 * inch], font_size=6.85),
        PageBreak(),
    ]

    # Page 7
    story += [
        P("Node-RED deployment verification", h1),
        P("Node-RED was deployed on the Raspberry Pi alongside the Node.js gateway. The active event route accepts POST /edge-events from the gateway, validates the edge token, and sends non-normal readings to AWS Lambda. The original POST /telemetry-flow route remains as an independently testable readiness-aware classification flow. This separation preserved the ESP32 endpoint at port 3000 while adding event-driven cloud forwarding."),
        img("nodered_lambda_integration_test.png", 6.35 * inch, 2.59 * inch),
        P("Figure 7. Deployed Node-RED event route on the Raspberry Pi. The Debug panel records the labelled integration-test-02 event and the AWS Lambda response with ok: true. This is an integration test; Figure 4 separately provides the physical ESP32-to-Pi forwarding evidence.", caption),
        P("The test payload used mq2Ready true and mq2AbsDelta 250, so it exercises the warning event path without needing to recreate a physical gas or flame condition. Node-RED authenticated the event, invoked the deployed Lambda Function URL, and returned a warning response. This verifies the Node-RED-to-Lambda segment independently of the physical sensor trial.", small),
        PageBreak(),
    ]

    # Page 8
    story += [
        P("AWS runtime evidence", h1),
        P("CloudWatch records continuous START, END and REPORT entries for the deployed sit314-edge-telemetry Lambda function, with successful executions and measured runtimes. Together with Figure 7, this confirms that the Node-RED event route reached the deployed AWS function rather than only a local mock endpoint."),
        img("cloudwatch_lambda_runtime.png", 6.35 * inch, 4.76 * inch),
        P("Figure 8. AWS CloudWatch runtime log for sit314-edge-telemetry. The repeated successful Lambda invocation entries are paired with the Node-RED request and response evidence in Figure 7.", caption),
        PageBreak(),
    ]

    # Page 9
    story += [
        P("Evaluation and conclusion", h1),
        P("The final build demonstrates the intended separation between sensing, edge processing and scalable workload generation. Live ESP32 values reach the Pi gateway, where normal telemetry is retained locally and warning or critical records enter the Node-RED to Lambda event path. The local alarm, dashboard records and 47/47 successful Node-RED forwards provide evidence that this is a working physical route rather than a simulated design."),
        P("The scalability experiment extends this beyond a single prototype. At 400 virtual nodes, 45,515 of 48,000 readings were filtered locally in the offline model. Separately, the deployed Pi returned 2xx to all 1,830 staged live test POSTs and all 250 concurrent test POSTs. The gateway now sends only non-normal events to the deployed Node-RED and Lambda route, retaining the same schema and edge rules."),
        P("Validation scope", h2),
        P("Validation combines physical ESP32 telemetry, gateway HTTP acknowledgement, dashboard evidence, deployed Node-RED event forwarding, Lambda response logging and repeatable sequential and concurrent load tests. The offline simulator deliberately remains a modelled capacity experiment, while the Pi tests measure actual local-network HTTP behaviour."),
        P("Scalability interpretation", h2),
        P("Filtering 89,179 routine readings locally means only 5.1% of the offline generated workload entered the forwarding path. This is the central scalability result: higher device volume does not force every measurement through a downstream dashboard or cloud service. The offline modelled latency rose gradually as load increased, while the live Pi test provides an independent, directly measured request-time check. A production deployment would additionally monitor resource use, queue depth, CPU/memory and failed requests under concurrent traffic."),
        P("Security and operational limitations", h2),
        P("The deployed build applies application-layer authentication at both event boundaries. The ESP32-S3 sends a shared device token to the Pi gateway; genuine telemetry was accepted with HTTP 200, while a request without that token was rejected with HTTP 401 (Figure 9). A separate shared edge token protects the Pi-to-Node-RED-to-Lambda event route and is stored in runtime configuration rather than the report or source-flow export. The ESP32-to-Pi hop remains HTTP on a private lab network, so the token is authenticated but not protected by transport encryption. A production deployment would use per-device credentials, rotated secrets and HTTPS or MQTT over TLS, and would restrict dashboard access. MQ-2 values remain a gas-risk proxy rather than calibrated air-quality measurements; a production safety system would require calibrated and redundant detection with formal safety review."),
        P("Requirements traceability", h2),
        make_table([
            ["Plan requirement", "Status and evidence"],
            ["Physical IoT prototype", "Delivered: Figures 1-4 show sensors, ESP32 telemetry, Pi gateway and real forwarded alerts"],
            ["Node.js edge processing", "Delivered: port 3000 gateway performs validation, filtering, logs and dashboard"],
            ["Node-RED event flow", "Delivered: Pi Node-RED receives gateway non-normal events; Figures 4, 7 and 8"],
            ["AWS deployment", "Delivered: Lambda sit314-edge-telemetry is invoked by Node-RED for event classification"],
            ["Scalability evidence", "Delivered: offline 8-400 model; 1,830 staged and 250 concurrent live Pi POSTs"],
            ["Automatic scaling", "Partial: Lambda managed concurrency is used; no formal cloud scale-out benchmark is claimed"],
            ["Secure deployment", "Partial: device token authenticates ESP32-to-Pi and edge token protects Pi-to-cloud; TLS remains future work"],
        ], [2.15 * inch, 4.45 * inch], font_size=6.4),
        PageBreak(),
        P("Appendix A Selected code and configuration", h1),
        P("The excerpts below provide implementation evidence for the physical node, edge gateway and repeatable scalability test.", small),
        P("ESP32-S3 endpoint and thresholds (esp32_s3_final_node.ino)", h2),
        P("const char* EDGE_TELEMETRY_URL = \"http://192.168.4.55:3000/telemetry\";<br/>const unsigned long MQ2_WARMUP_MS = 900000;<br/>const int MQ2_WARNING_DELTA = 180;<br/>const int MQ2_CRITICAL_DELTA = 320;<br/>http.addHeader(\"X-Device-Token\", DEVICE_SHARED_TOKEN);<br/>int httpCode = http.POST(payload);", code),
        P("Raspberry Pi edge rules (edge_server.js)", h2),
        P("if (!validDeviceToken(req.headers[\"x-device-token\"])) { sendJson(res, 401, { ok: false }); return; }<br/>const mq2Ready = bool(payload.mq2Ready);<br/>if (mq2Ready &amp;&amp; mq2AbsDelta &gt;= MQ2_CRITICAL_DELTA) { severity = \"critical\"; }<br/>if (reading.severity !== \"normal\") { forwardEventToNodeRed(reading); }<br/>headers: { \"X-Edge-Token\": EDGE_SHARED_TOKEN },", code),
        P("Reproducible scalability command (simulate_edge_load.py)", h2),
        P("python simulation\\simulate_edge_load.py --post-url http://&lt;pi-ip&gt;:3000/telemetry --device-token &lt;configured-device-token&gt; --nodes 100 --steps 10<br/>Outputs include modelled capacity metrics and measured HTTP p50/p95 values when --post-url is supplied.", code),
        P("Node-RED extension (node_red/smart_building_edge_flow.json)", h2),
        P("POST /edge-events from the Node.js gateway -&gt; token validation -&gt; AWS Lambda HTTP request -&gt; response. POST /telemetry-flow remains available for independent readiness-aware classification testing on Pi port 1880.", code),
        P("AWS Lambda configuration (aws/lambda/index.mjs)", h2),
        P("export const handler = async (event) =&gt; { ... }<br/>if (!mq2Ready) reasons.push(\"mq2_calibrating\");<br/>else if (delta &gt;= 320) { severity = \"critical\"; }<br/>return { statusCode: 200, body: JSON.stringify({ severity, action, reasons }) };", code),
        P("Telemetry schema used by physical and simulated nodes", h2),
        make_table([
            ["Fields", "Purpose"],
            ["deviceId, room, location, seq", "Device identity, room context and message ordering"],
            ["temperature, humidity", "Environmental context for each reading"],
            ["mq2Raw, mq2Baseline, mq2AbsDelta", "Gas-risk proxy and calibration-aware threshold evaluation"],
            ["mq2Ready, pirMotion, flameDetected, alarm", "Event context, readiness state and local safety output"],
        ], [2.65 * inch, 4.0 * inch], font_size=6.9),
        Spacer(1, 4),
        P("Files and evidence included", h2),
        make_table([
            ["File", "Purpose"],
            ["esp32_s3_final_node.ino", "Sensor reading, calibration, local alarm and HTTP telemetry"],
            ["edge_server.js", "Edge API, classification, dashboard and JSONL logging"],
            ["simulate_edge_load.py", "Repeatable virtual-node scalability experiment"],
            ["scalability_metrics.csv", "Offline modelled node-count results shown in Figure 6"],
            ["live_pi_*/simulation_summary.json", "Measured HTTP timing and 2xx outcomes shown in Table 1"],
            ["node_red/smart_building_edge_flow.json", "Importable Node-RED edge-processing configuration"],
            ["aws/lambda/index.mjs", "Deployed AWS Lambda cloud-classifier configuration"],
            ["aws/cloudshell_deployment_transcript.txt", "CloudShell deployment timestamp and successful critical test result"],
        ], [2.45 * inch, 4.2 * inch], font_size=7.45),
        PageBreak(),
        P("Appendix B Device authentication evidence", h1),
        P("The two captures below were taken after deploying the device-token update to the Raspberry Pi and reflashing the physical ESP32-S3. They demonstrate both the accepted-device and rejected-unauthorised cases without exposing the token value.", small),
        Table([[img("esp32_authenticated_http_200.png", 3.18 * inch, 4.13 * inch), img("unauthorised_request_401.png", 3.18 * inch, 2.20 * inch)]], colWidths=[3.25 * inch, 3.25 * inch], hAlign="CENTER", style=[("VALIGN", (0, 0), (-1, -1), "MIDDLE")]),
        P("Figure 9. Device authentication verification. Left: the physical ESP32-S3 posts authenticated telemetry and receives HTTP 200. Right: an otherwise valid request without X-Device-Token is rejected by the Raspberry Pi gateway with HTTP 401 Unauthorized.", caption),
    ]
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(OUT_PDF)


if __name__ == "__main__":
    main()
