# AWS Lambda cloud-classifier deployment

The AWS Learner Lab deployment is a small serverless extension of the Raspberry
Pi edge rules. It is deliberately not connected directly to the physical ESP32
in this submission: the physical path remains ESP32 -> Raspberry Pi, and the
Lambda is an independently invoked cloud validation endpoint.

## Deployment record

- Function: `sit314-edge-telemetry`
- Region: `us-east-1`
- Runtime: Node.js 24.x
- Execution role: Learner Lab `LabRole`
- Deployment method: AWS CloudShell, `aws lambda update-function-code`
- Test result: an MQ-2 ready payload with `mq2AbsDelta: 420` returned HTTP 200,
  `severity: critical`, and `action: forward_to_cloud_or_dashboard`.

The Lambda service provides managed concurrency in a production architecture,
but this project did not run a cloud concurrency/scale-out experiment. The
directly measured scalability evidence is the separate local Pi HTTP test.
