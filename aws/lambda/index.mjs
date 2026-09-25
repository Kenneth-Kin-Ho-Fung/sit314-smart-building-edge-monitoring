export const handler = async (event) => {
  const headers = Object.fromEntries(
    Object.entries(event?.headers || {}).map(([key, value]) => [key.toLowerCase(), value]),
  );
  const expectedToken = process.env.EDGE_SHARED_TOKEN;
  if (expectedToken && headers["x-edge-token"] !== expectedToken) {
    return {
      statusCode: 401,
      body: JSON.stringify({ ok: false, error: "unauthorised edge event" }),
    };
  }

  let payload;
  try {
    payload = event?.body ? JSON.parse(event.body) : event;
  } catch {
    return {
      statusCode: 400,
      body: JSON.stringify({ ok: false, error: "invalid JSON payload" }),
    };
  }
  const bool = (value) => value === true || value === "true" || value === 1 || value === "1";
  const mq2Ready = bool(payload?.mq2Ready);
  const delta = Number(payload?.mq2AbsDelta) || 0;
  let severity = "normal";
  const reasons = [];

  if (bool(payload?.flameDetected)) {
    severity = "critical";
    reasons.push("flame_detected");
  }
  if (!mq2Ready) {
    reasons.push("mq2_calibrating");
  } else if (delta >= 320) {
    severity = "critical";
    reasons.push("mq2_critical_delta");
  } else if (delta >= 180 && severity !== "critical") {
    severity = "warning";
    reasons.push("mq2_warning_delta");
  }
  if (bool(payload?.alarm) && severity === "normal") {
    severity = "warning";
    reasons.push("local_alarm_latched");
  }

  // Keep CloudWatch evidence limited to event classification metadata, never credentials.
  console.log(JSON.stringify({
    source: "node-red-edge-event",
    deviceId: payload?.deviceId || "unknown-device",
    room: payload?.room || "unknown-room",
    mq2Ready,
    mq2AbsDelta: delta,
    flameDetected: bool(payload?.flameDetected),
    severity,
    action: severity === "normal" ? "filter_local_only" : "forward_to_cloud_or_dashboard",
    reasons,
  }));

  return {
    statusCode: 200,
    body: JSON.stringify({
      ok: true,
      deviceId: payload?.deviceId || "unknown-device",
      mq2Ready,
      severity,
      action: severity === "normal" ? "filter_local_only" : "forward_to_cloud_or_dashboard",
      reasons,
    }),
  };
};
