/*
  SIT314 6.3D Final Project - Raspberry Pi Edge Gateway

  Purpose:
  - Receive ESP32-S3 sensor JSON over HTTP POST /telemetry
  - Classify normal, warning and critical readings at the edge
  - Log all telemetry to data/telemetry_log.jsonl
  - Log forwarded warning/critical events to data/edge_alerts.jsonl
  - Provide a simple dashboard and JSON endpoints for evidence screenshots

  Run on Raspberry Pi:
    node edge_server.js

  Then browse:
    http://<raspberry-pi-ip>:3000/
*/

"use strict";

const http = require("http");
const https = require("https");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const PORT = Number(process.env.PORT || 3000);
const DATA_DIR = path.join(__dirname, "data");
const TELEMETRY_LOG = path.join(DATA_DIR, "telemetry_log.jsonl");
const ALERT_LOG = path.join(DATA_DIR, "edge_alerts.jsonl");

const MQ2_WARNING_DELTA = Number(process.env.MQ2_WARNING_DELTA || 180);
const MQ2_CRITICAL_DELTA = Number(process.env.MQ2_CRITICAL_DELTA || 320);
const NODE_RED_EVENT_URL = process.env.NODE_RED_EVENT_URL || "";
const EDGE_SHARED_TOKEN = process.env.EDGE_SHARED_TOKEN || "";
const DEVICE_SHARED_TOKEN = process.env.DEVICE_SHARED_TOKEN || "";
const FORWARD_TIMEOUT_MS = Number(process.env.FORWARD_TIMEOUT_MS || 3000);

fs.mkdirSync(DATA_DIR, { recursive: true });

let latestReading = null;
const recentReadings = [];
const recentAlerts = [];
const stats = {
  startedAt: new Date().toISOString(),
  received: 0,
  normalFiltered: 0,
  forwardedEvents: 0,
  warnings: 0,
  critical: 0,
  nodeRedForwardQueued: 0,
  nodeRedForwardSucceeded: 0,
  nodeRedForwardFailed: 0,
  nodeRedForwardSkipped: 0,
  byDevice: {},
};

function readRequestBody(req, maxBytes = 256 * 1024) {
  return new Promise((resolve, reject) => {
    let body = "";
    let exceeded = false;
    req.on("data", (chunk) => {
      if (exceeded) return;
      body += chunk;
      if (body.length > maxBytes) {
        exceeded = true;
        reject(Object.assign(new Error("Request body too large"), { statusCode: 413 }));
      }
    });
    req.on("end", () => resolve(body));
    req.on("error", reject);
  });
}

function appendJsonLine(filePath, value) {
  fs.appendFileSync(filePath, JSON.stringify(value) + "\n", "utf8");
}

function bool(value) {
  return value === true || value === "true" || value === 1 || value === "1";
}

function validDeviceToken(candidate) {
  if (!DEVICE_SHARED_TOKEN || typeof candidate !== "string") return false;
  const expected = Buffer.from(DEVICE_SHARED_TOKEN);
  const received = Buffer.from(candidate);
  return expected.length === received.length && crypto.timingSafeEqual(expected, received);
}

function numberOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function classifyTelemetry(payload) {
  const mq2AbsDelta = numberOrNull(payload.mq2AbsDelta) || 0;
  const mq2Ready = bool(payload.mq2Ready);
  const flameDetected = bool(payload.flameDetected);
  const alarm = bool(payload.alarm);
  const pirMotion = bool(payload.pirMotion);

  const reasons = [];
  let severity = "normal";

  if (flameDetected) {
    severity = "critical";
    reasons.push("flame_detected");
  }
  if (!mq2Ready) {
    reasons.push("mq2_calibrating");
  }
  if (mq2Ready && mq2AbsDelta >= MQ2_CRITICAL_DELTA) {
    severity = "critical";
    reasons.push("mq2_critical_delta");
  } else if (mq2Ready && mq2AbsDelta >= MQ2_WARNING_DELTA && severity !== "critical") {
    severity = "warning";
    reasons.push("mq2_warning_delta");
  }
  if (alarm && severity === "normal") {
    severity = "warning";
    reasons.push("local_alarm_latched");
  }
  if (pirMotion && severity !== "normal") {
    reasons.push("motion_context");
  }

  return {
    severity,
    action: severity === "normal" ? "filter_local_only" : "forward_to_cloud_or_dashboard",
    reasons,
  };
}

function normaliseTelemetry(payload, sourceIp) {
  const classification = classifyTelemetry(payload);
  const deviceId = String(payload.deviceId || "unknown-device");
  const reading = {
    receivedAt: new Date().toISOString(),
    sourceIp,
    deviceId,
    room: payload.room || "B1-F3-R302",
    location: payload.location || "building1/floor3/room302",
    temperature: numberOrNull(payload.temperature),
    humidity: numberOrNull(payload.humidity),
    mq2Raw: numberOrNull(payload.mq2Raw),
    mq2Baseline: numberOrNull(payload.mq2Baseline),
    mq2Delta: numberOrNull(payload.mq2Delta),
    mq2AbsDelta: numberOrNull(payload.mq2AbsDelta),
    mq2EventPeakAbsDelta: numberOrNull(payload.mq2EventPeakAbsDelta),
    mq2Ready: bool(payload.mq2Ready),
    pirMotion: bool(payload.pirMotion),
    flameDetected: bool(payload.flameDetected),
    flameDigitalRaw: numberOrNull(payload.flameDigitalRaw),
    flameAnalogRaw: numberOrNull(payload.flameAnalogRaw),
    alarm: bool(payload.alarm),
    uptimeMs: numberOrNull(payload.uptimeMs),
    seq: numberOrNull(payload.seq),
    severity: classification.severity,
    action: classification.action,
    reasons: classification.reasons,
  };
  return reading;
}

function updateStats(reading) {
  stats.received += 1;
  stats.byDevice[reading.deviceId] = (stats.byDevice[reading.deviceId] || 0) + 1;
  if (reading.severity === "normal") {
    stats.normalFiltered += 1;
  } else {
    stats.forwardedEvents += 1;
    if (reading.severity === "warning") stats.warnings += 1;
    if (reading.severity === "critical") stats.critical += 1;
  }
}

function storeReading(reading) {
  latestReading = reading;
  recentReadings.unshift(reading);
  recentReadings.splice(20);

  appendJsonLine(TELEMETRY_LOG, reading);
  updateStats(reading);

  if (reading.severity !== "normal") {
    recentAlerts.unshift(reading);
    recentAlerts.splice(20);
    appendJsonLine(ALERT_LOG, reading);
  }
}

// Forward only non-normal records after edge classification. This is deliberately
// asynchronous so a cloud-path delay never prevents the ESP32 receiving its HTTP ack.
function forwardEventToNodeRed(reading) {
  if (!NODE_RED_EVENT_URL) {
    stats.nodeRedForwardSkipped += 1;
    return;
  }
  if (!EDGE_SHARED_TOKEN) {
    stats.nodeRedForwardSkipped += 1;
    console.warn("Node-RED forwarding skipped: EDGE_SHARED_TOKEN is not configured");
    return;
  }

  let target;
  try {
    target = new URL(NODE_RED_EVENT_URL);
  } catch {
    stats.nodeRedForwardFailed += 1;
    console.error("Node-RED forwarding failed: NODE_RED_EVENT_URL is invalid");
    return;
  }

  const body = JSON.stringify({
    ...reading,
    edgeForwardedAt: new Date().toISOString(),
    edgeForwarder: "nodejs-edge-gateway",
  });
  const client = target.protocol === "https:" ? https : http;
  const request = client.request({
    protocol: target.protocol,
    hostname: target.hostname,
    port: target.port || (target.protocol === "https:" ? 443 : 80),
    path: `${target.pathname}${target.search}`,
    method: "POST",
    timeout: FORWARD_TIMEOUT_MS,
    headers: {
      "Content-Type": "application/json",
      "Content-Length": Buffer.byteLength(body),
      "X-Edge-Token": EDGE_SHARED_TOKEN,
    },
  }, (response) => {
    response.resume();
    if (response.statusCode >= 200 && response.statusCode < 300) {
      stats.nodeRedForwardSucceeded += 1;
      console.log(`  Node-RED forward HTTP ${response.statusCode}`);
    } else {
      stats.nodeRedForwardFailed += 1;
      console.error(`  Node-RED forward returned HTTP ${response.statusCode}`);
    }
  });
  request.on("timeout", () => request.destroy(new Error("Node-RED forwarding timeout")));
  request.on("error", (error) => {
    stats.nodeRedForwardFailed += 1;
    console.error(`  Node-RED forward failed: ${error.message}`);
  });
  request.write(body);
  request.end();
  stats.nodeRedForwardQueued += 1;
}

function sendJson(res, statusCode, value) {
  const body = JSON.stringify(value, null, 2);
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  });
  res.end(body);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderDashboard() {
  const latest = latestReading || {};
  const rows = recentReadings.slice(0, 10).map((r) => `
    <tr>
      <td>${escapeHtml(r.receivedAt || "")}</td>
      <td>${escapeHtml(r.deviceId || "")}</td>
      <td>${escapeHtml(r.room || "")}</td>
      <td><span class="badge ${escapeHtml(r.severity)}">${escapeHtml(r.severity)}</span></td>
      <td>${escapeHtml(r.temperature ?? "")}</td>
      <td>${escapeHtml(r.humidity ?? "")}</td>
      <td>${escapeHtml(r.mq2AbsDelta ?? "")}</td>
      <td>${escapeHtml(r.action || "")}</td>
    </tr>
  `).join("");

  const alertRows = recentAlerts.slice(0, 8).map((r) => `
    <tr>
      <td>${escapeHtml(r.receivedAt || "")}</td>
      <td>${escapeHtml(r.room || "")}</td>
      <td><span class="badge ${escapeHtml(r.severity)}">${escapeHtml(r.severity)}</span></td>
      <td>${escapeHtml((r.reasons || []).join(", "))}</td>
    </tr>
  `).join("");

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="5">
  <title>SIT314 Smart Building Edge Gateway</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 28px; color: #162033; background: #f5f7fb; }
    h1 { margin: 0 0 4px; font-size: 28px; }
    h2 { margin-top: 26px; font-size: 18px; }
    .sub { color: #56657a; margin-bottom: 20px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 18px 0; }
    .card { background: white; border: 1px solid #d8e0ea; border-radius: 8px; padding: 14px; }
    .label { color: #64748b; font-size: 12px; }
    .value { font-size: 26px; font-weight: 700; margin-top: 5px; }
    table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #d8e0ea; }
    th, td { padding: 8px 10px; border-bottom: 1px solid #edf1f7; text-align: left; font-size: 13px; }
    th { background: #eaf2fb; color: #173b65; }
    .badge { display: inline-block; padding: 3px 8px; border-radius: 999px; font-weight: 700; font-size: 12px; }
    .normal { background: #e7f8ed; color: #176b36; }
    .warning { background: #fff4cf; color: #8a5b00; }
    .critical { background: #ffe1df; color: #a31d16; }
    pre { white-space: pre-wrap; background: #101826; color: #e8eef8; padding: 14px; border-radius: 8px; }
  </style>
</head>
<body>
  <h1>SIT314 Smart Building Edge Gateway</h1>
  <div class="sub">Physical ESP32-S3 telemetry + edge filtering + alert forwarding evidence</div>
  <div class="grid">
    <div class="card"><div class="label">Received</div><div class="value">${stats.received}</div></div>
    <div class="card"><div class="label">Normal filtered</div><div class="value">${stats.normalFiltered}</div></div>
    <div class="card"><div class="label">Forwarded events</div><div class="value">${stats.forwardedEvents}</div></div>
    <div class="card"><div class="label">Warnings</div><div class="value">${stats.warnings}</div></div>
    <div class="card"><div class="label">Critical</div><div class="value">${stats.critical}</div></div>
    <div class="card"><div class="label">Node-RED forwards</div><div class="value">${stats.nodeRedForwardSucceeded}/${stats.nodeRedForwardQueued}</div></div>
  </div>

  <h2>Latest reading</h2>
  <pre>${escapeHtml(JSON.stringify(latest, null, 2))}</pre>

  <h2>Recent telemetry</h2>
  <table>
    <thead><tr><th>Time</th><th>Device</th><th>Room</th><th>Severity</th><th>Temp</th><th>Humidity</th><th>MQ-2 abs delta</th><th>Edge action</th></tr></thead>
    <tbody>${rows || '<tr><td colspan="8">No telemetry received yet.</td></tr>'}</tbody>
  </table>

  <h2>Recent forwarded alerts</h2>
  <table>
    <thead><tr><th>Time</th><th>Room</th><th>Severity</th><th>Reasons</th></tr></thead>
    <tbody>${alertRows || '<tr><td colspan="4">No warning or critical events yet.</td></tr>'}</tbody>
  </table>
</body>
</html>`;
}

async function handleTelemetry(req, res) {
  try {
    if (!validDeviceToken(req.headers["x-device-token"])) {
      sendJson(res, 401, { ok: false, error: "unauthorised device" });
      return;
    }
    const body = await readRequestBody(req);
    const payload = JSON.parse(body || "{}");
    const reading = normaliseTelemetry(payload, req.socket.remoteAddress);
    storeReading(reading);

    console.log(`[${reading.receivedAt}] ${reading.deviceId} ${reading.room} ${reading.severity} ${reading.action}`);
    if (reading.severity !== "normal") {
      console.log(`  ALERT reasons=${reading.reasons.join(",")} mq2AbsDelta=${reading.mq2AbsDelta} flame=${reading.flameDetected}`);
      forwardEventToNodeRed(reading);
    }

    sendJson(res, 200, {
      ok: true,
      receivedAt: reading.receivedAt,
      severity: reading.severity,
      action: reading.action,
      reasons: reading.reasons,
      stats,
    });
  } catch (error) {
    sendJson(res, error.statusCode || 400, { ok: false, error: error.message });
  }
}

const server = http.createServer((req, res) => {
  // Use a fixed base so an invalid client Host header cannot crash routing.
  let url;
  try {
    url = new URL(req.url, "http://localhost");
  } catch {
    sendJson(res, 400, { ok: false, error: "Bad request" });
    return;
  }

  if (req.method === "POST" && url.pathname === "/telemetry") {
    handleTelemetry(req, res);
    return;
  }
  if (req.method === "GET" && url.pathname === "/latest") {
    sendJson(res, 200, latestReading || {});
    return;
  }
  if (req.method === "GET" && url.pathname === "/stats") {
    sendJson(res, 200, stats);
    return;
  }
  if (req.method === "GET" && url.pathname === "/alerts") {
    sendJson(res, 200, recentAlerts);
    return;
  }
  if (req.method === "GET" && url.pathname === "/telemetry") {
    sendJson(res, 200, recentReadings);
    return;
  }
  if (req.method === "GET" && url.pathname === "/") {
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" });
    res.end(renderDashboard());
    return;
  }

  sendJson(res, 404, { ok: false, error: "Not found" });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log("SIT314 edge gateway started");
  console.log(`Listening on http://0.0.0.0:${PORT}`);
  console.log(`Telemetry endpoint: POST http://<raspberry-pi-ip>:${PORT}/telemetry`);
  console.log(`Dashboard: http://<raspberry-pi-ip>:${PORT}/`);
  console.log(NODE_RED_EVENT_URL
    ? `Alert forwarding: ${NODE_RED_EVENT_URL}`
    : "Alert forwarding: disabled (NODE_RED_EVENT_URL is not configured)");
  console.log(`Logs: ${TELEMETRY_LOG}`);
});
