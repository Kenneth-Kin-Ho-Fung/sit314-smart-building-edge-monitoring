# Node-RED edge-flow extension

This importable, core-node-only flow exposes `POST /telemetry-flow` on the
Node-RED host. It uses the same telemetry fields and decision rules as the
Node.js gateway:

- `flameDetected` is critical.
- MQ-2 thresholds are ignored until `mq2Ready` is true.
- An MQ-2 absolute delta of `180` is warning and `320` is critical.
- `alarm` alone produces at least warning, rather than silently filtering it.

## Run on the Raspberry Pi

1. Install and start Node-RED using the official Raspberry Pi instructions.
2. Open `http://<pi-ip>:1880` and select **Import**.
3. Paste the contents of `smart_building_edge_flow.json`, then click **Deploy**.
4. Test from a machine on the same network:

```powershell
Invoke-RestMethod -Method Post -Uri http://<pi-ip>:1880/telemetry-flow -ContentType 'application/json' -Body '{"deviceId":"esp32s3-real-01","mq2Ready":true,"mq2AbsDelta":250,"flameDetected":false,"alarm":false,"pirMotion":false}'
```

The Node-RED Debug sidebar shows normal readings separately from forwarded
warning/critical readings. This is an integration-ready extension; it must be
imported and deployed before it can be cited as deployed evidence.
