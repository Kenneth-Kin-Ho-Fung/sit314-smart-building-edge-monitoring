"""
SIT314 6.3D Final Project - Smart Building Edge Load Simulation

This simulation uses the same JSON schema as the physical ESP32-S3 node.
It can run offline to generate scalability evidence, or POST simulated
telemetry to the Raspberry Pi edge gateway.

Examples:
  Offline scalability outputs:
    python simulate_edge_load.py

  Send a small live run to the Raspberry Pi:
    python simulate_edge_load.py --post-url http://192.168.1.50:3000/telemetry --nodes 8 --steps 20

Outputs:
  outputs/simulated_telemetry.jsonl
  outputs/edge_alerts.jsonl
  outputs/scalability_metrics.csv
  outputs/simulation_summary.json
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib import request


ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"

MQ2_WARNING_DELTA = 180
MQ2_CRITICAL_DELTA = 320


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify(payload: dict) -> tuple[str, str, list[str]]:
    reasons: list[str] = []
    severity = "normal"

    if payload["flameDetected"]:
        severity = "critical"
        reasons.append("flame_detected")

    mq2_ready = bool(payload.get("mq2Ready", False))
    mq2_abs_delta = abs(int(payload["mq2AbsDelta"]))
    if not mq2_ready:
        reasons.append("mq2_calibrating")
    elif mq2_abs_delta >= MQ2_CRITICAL_DELTA:
        severity = "critical"
        reasons.append("mq2_critical_delta")
    elif mq2_abs_delta >= MQ2_WARNING_DELTA and severity != "critical":
        severity = "warning"
        reasons.append("mq2_warning_delta")

    if payload["alarm"] and severity == "normal":
        severity = "warning"
        reasons.append("local_alarm_latched")

    if payload["pirMotion"] and severity != "normal":
        reasons.append("motion_context")

    action = "filter_local_only" if severity == "normal" else "forward_to_cloud_or_dashboard"
    return severity, action, reasons


def generate_payload(node_index: int, seq: int, rng: random.Random) -> dict:
    floor = 1 + (node_index // 12)
    room = 300 + node_index
    device_id = f"sim-esp32s3-{node_index:03d}"

    temperature = round(rng.normalvariate(24.2, 1.6), 1)
    humidity = round(max(25, min(75, rng.normalvariate(45, 8))), 1)
    mq2_baseline = int(rng.normalvariate(1750, 70))
    mq2_delta = int(rng.normalvariate(0, 45))

    # Inject occasional warning/critical gas events.
    event_roll = rng.random()
    if event_roll < 0.012:
        mq2_delta = rng.choice([-1, 1]) * rng.randint(350, 1200)
    elif event_roll < 0.045:
        mq2_delta = rng.choice([-1, 1]) * rng.randint(185, 330)

    flame_detected = rng.random() < 0.006
    pir_motion = rng.random() < 0.18
    mq2_abs_delta = abs(mq2_delta)
    alarm = flame_detected or mq2_abs_delta >= MQ2_CRITICAL_DELTA

    return {
        "deviceId": device_id,
        "room": f"B1-F{floor}-R{room}",
        "location": f"building1/floor{floor}/room{room}",
        "seq": seq,
        "uptimeMs": seq * 5000,
        "temperature": temperature,
        "humidity": humidity,
        "mq2Raw": mq2_baseline + mq2_delta,
        "mq2Baseline": mq2_baseline,
        "mq2Delta": mq2_delta,
        "mq2AbsDelta": mq2_abs_delta,
        "mq2PeakRaw": mq2_baseline + abs(mq2_delta),
        "mq2EventPeakAbsDelta": mq2_abs_delta if mq2_abs_delta >= MQ2_WARNING_DELTA else 0,
        "mq2Ready": True,
        "pirMotion": pir_motion,
        "flameDigitalRaw": 1 if flame_detected else 0,
        "flameDetected": flame_detected,
        "flameAnalogRaw": 130 if flame_detected else 4095,
        "alarm": alarm,
        "simulatedAt": iso_now(),
    }


def post_payload(url: str, payload: dict, device_token: str = "", timeout: float = 3.0) -> tuple[int, str, float]:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if device_token:
        headers["X-Device-Token"] = device_token
    req = request.Request(
        url,
        data=body,
        method="POST",
        headers=headers,
    )
    started = time.perf_counter()
    with request.urlopen(req, timeout=timeout) as response:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return response.status, response.read().decode("utf-8", errors="replace"), elapsed_ms


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * fraction)
    return round(ordered[index], 2)


def run_for_nodes(
    node_count: int,
    steps: int,
    rng: random.Random,
    post_url: str | None = None,
    device_token: str = "",
    concurrency: int = 1,
) -> dict:
    telemetry: list[dict] = []
    alerts: list[dict] = []
    post_ok = 0
    post_failed = 0
    http_latencies_ms: list[float] = []
    start = time.perf_counter()

    for seq in range(1, steps + 1):
        for node_index in range(1, node_count + 1):
            payload = generate_payload(node_index, seq, rng)
            severity, action, reasons = classify(payload)
            enriched = {
                **payload,
                "severity": severity,
                "action": action,
                "reasons": reasons,
            }
            telemetry.append(enriched)
            if severity != "normal":
                alerts.append(enriched)

    if post_url:
        payloads = [item["payload"] if "payload" in item else item for item in telemetry]

        def post_one(payload: dict) -> float:
            status, _, latency_ms = post_payload(post_url, payload, device_token)
            if not 200 <= status < 300:
                raise RuntimeError(f"Gateway returned HTTP {status}")
            return latency_ms

        if concurrency <= 1:
            futures = ((payload, None) for payload in payloads)
            for payload, _ in futures:
                try:
                    http_latencies_ms.append(post_one(payload))
                    post_ok += 1
                except Exception as exc:  # noqa: BLE001 - this is a test runner
                    post_failed += 1
                    if post_failed <= 5:
                        print(f"POST failed for {payload['deviceId']}: {exc}")
        else:
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = {executor.submit(post_one, payload): payload for payload in payloads}
                for future in as_completed(futures):
                    payload = futures[future]
                    try:
                        http_latencies_ms.append(future.result())
                        post_ok += 1
                    except Exception as exc:  # noqa: BLE001 - this is a test runner
                        post_failed += 1
                        if post_failed <= 5:
                            print(f"POST failed for {payload['deviceId']}: {exc}")

    elapsed_ms = (time.perf_counter() - start) * 1000
    generated = len(telemetry)
    forwarded = len(alerts)
    normal_filtered = generated - forwarded
    warnings = sum(1 for item in alerts if item["severity"] == "warning")
    critical = sum(1 for item in alerts if item["severity"] == "critical")

    # The offline model is kept separate from live HTTP timing. It models edge
    # work increasing slowly with node count while filtering reduces forwarding.
    modelled_p95_latency_ms = round(18 + (node_count ** 0.45) * 2.1 + (forwarded / max(generated, 1)) * 22, 2)

    return {
        "virtualNodes": node_count,
        "concurrency": concurrency,
        "steps": steps,
        "generated": generated,
        "normalFiltered": normal_filtered,
        "forwardedEvents": forwarded,
        "warnings": warnings,
        "critical": critical,
        "modelledEdgeWorkers": max(1, round(node_count / 100)),
        "modelledP95LatencyMs": modelled_p95_latency_ms,
        "httpP50LatencyMs": percentile(http_latencies_ms, 0.50),
        "httpP95LatencyMs": percentile(http_latencies_ms, 0.95),
        "httpMinLatencyMs": round(min(http_latencies_ms), 2) if http_latencies_ms else None,
        "httpMaxLatencyMs": round(max(http_latencies_ms), 2) if http_latencies_ms else None,
        "elapsedMs": round(elapsed_ms, 2),
        "postOk": post_ok,
        "postFailed": post_failed,
        "telemetry": telemetry,
        "alerts": alerts,
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--post-url", default="", help="Optional Raspberry Pi edge endpoint, e.g. http://192.168.1.50:3000/telemetry")
    parser.add_argument("--device-token", default="", help="Optional X-Device-Token required by an authenticated gateway")
    parser.add_argument("--nodes", type=int, default=0, help="If set, run only this node count instead of the full scalability sweep")
    parser.add_argument("--steps", type=int, default=120, help="Readings per virtual node")
    parser.add_argument("--concurrency", type=int, default=1, help="Concurrent HTTP POST workers when --post-url is supplied")
    parser.add_argument("--seed", type=int, default=31463)
    parser.add_argument("--output-dir", default="", help="Optional directory for this run's outputs")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else OUTPUTS
    output_dir.mkdir(parents=True, exist_ok=True)

    node_counts = [args.nodes] if args.nodes else [8, 25, 50, 100, 200, 400]
    post_url = args.post_url.strip() or None

    all_telemetry: list[dict] = []
    all_alerts: list[dict] = []
    metrics: list[dict] = []

    print("SIT314 6.3D edge simulation started")
    if post_url:
        print(f"Posting generated telemetry to {post_url}")

    for node_count in node_counts:
        result = run_for_nodes(node_count, args.steps, rng, post_url, args.device_token, max(1, args.concurrency))
        all_telemetry.extend(result.pop("telemetry"))
        all_alerts.extend(result.pop("alerts"))
        metrics.append(result)
        print(
            f"nodes={node_count:3d} generated={result['generated']:5d} "
            f"filtered={result['normalFiltered']:5d} forwarded={result['forwardedEvents']:4d} "
            f"warning={result['warnings']:3d} critical={result['critical']:3d} "
            f"concurrency={result['concurrency']:2d} "
            f"modelledP95={result['modelledP95LatencyMs']}ms "
            f"httpP95={result['httpP95LatencyMs']}ms"
        )

    write_jsonl(output_dir / "simulated_telemetry.jsonl", all_telemetry)
    write_jsonl(output_dir / "edge_alerts.jsonl", all_alerts)

    with (output_dir / "scalability_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(metrics[0].keys()))
        writer.writeheader()
        writer.writerows(metrics)

    summary = {
        "generatedAt": iso_now(),
        "postUrl": post_url,
        "totalGenerated": sum(row["generated"] for row in metrics),
        "totalNormalFiltered": sum(row["normalFiltered"] for row in metrics),
        "totalForwardedEvents": sum(row["forwardedEvents"] for row in metrics),
        "totalWarnings": sum(row["warnings"] for row in metrics),
        "totalCritical": sum(row["critical"] for row in metrics),
        "metrics": metrics,
    }
    (output_dir / "simulation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("Simulation outputs written to:")
    print(f"  {output_dir}")


if __name__ == "__main__":
    main()
