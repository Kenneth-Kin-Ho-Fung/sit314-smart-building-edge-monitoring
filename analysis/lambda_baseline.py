"""
SIT314 6.4HD cloud-first versus edge-first baseline calculator.

Reproduces Table 1, Table 2 and Figure 2 of the HD report from stated
assumptions. All outputs are calculated from the offline model and published
Lambda pricing; they are not measurements.

Usage:
  python analysis/lambda_baseline.py
  python analysis/lambda_baseline.py --rooms 400 --interval 5 --event-rate 0.051 --csv sensitivity.csv
"""

import argparse
import csv


PRICE_PER_MILLION_REQUESTS = 0.20
PRICE_PER_GB_SECOND = 0.0000166667


def monthly_readings(rooms, interval_s, days):
    return rooms * (86400 / interval_s) * days


def lambda_cost(invocations, billed_ms, memory_mb):
    request_cost = invocations / 1e6 * PRICE_PER_MILLION_REQUESTS
    duration_cost = invocations * (billed_ms / 1000) * (memory_mb / 1024) * PRICE_PER_GB_SECOND
    return request_cost + duration_cost


def validate_args(parser, args):
    if args.rooms <= 0:
        parser.error("--rooms must be greater than zero")
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")
    if args.days <= 0:
        parser.error("--days must be greater than zero")
    if not 0 <= args.event_rate <= 1:
        parser.error("--event-rate must be between 0 and 1")
    if args.billed_ms < 0 or args.max_ms < 0:
        parser.error("--billed-ms and --max-ms cannot be negative")
    if args.memory_mb <= 0:
        parser.error("--memory-mb must be greater than zero")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rooms", type=int, default=400)
    parser.add_argument("--interval", type=float, default=5.0, help="sampling interval in seconds (ESP32 firmware: 5 s)")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--event-rate", type=float, default=0.051, help="share of readings that are warning or critical (model: 0.051)")
    parser.add_argument("--billed-ms", type=float, default=2.0, help="typical billed duration observed in CloudWatch")
    parser.add_argument("--max-ms", type=float, default=12.0, help="longest billed duration observed in CloudWatch")
    parser.add_argument("--memory-mb", type=int, default=128)
    parser.add_argument("--csv", help="optional path for the event-rate sensitivity table")
    args = parser.parse_args()
    validate_args(parser, args)

    readings = monthly_readings(args.rooms, args.interval, args.days)
    cloud_first = readings
    edge_first = readings * args.event_rate
    cloud_cost = lambda_cost(cloud_first, args.billed_ms, args.memory_mb)
    edge_cost = lambda_cost(edge_first, args.billed_ms, args.memory_mb)

    print(
        f"Assumptions: {args.rooms} rooms, {args.interval:g} s interval, {args.days} days, "
        f"event rate {args.event_rate:.1%}, {args.billed_ms:g} ms billed at {args.memory_mb} MB"
    )
    print(f"Readings per month: {readings / 1e6:.1f} M\n")

    print("Table 1 - monthly baseline")
    print(f"  {'Design':34}{'Invocations':>14}{'Cost (US$)':>12}")
    print(f"  {'Cloud-first (every reading)':34}{cloud_first / 1e6:>12.1f} M{cloud_cost:>12.2f}")
    print(f"  {'Edge-first (event rate %.1f%%)' % (args.event_rate * 100):34}{edge_first / 1e6:>12.1f} M{edge_cost:>12.2f}")
    reduction = 1 - args.event_rate
    ratio = "not applicable" if args.event_rate == 0 else f"{cloud_first / edge_first:.1f}x fewer"
    print(f"  Reduction in invocations: {reduction:.1%}  ({ratio})\n")

    average_ingress = args.rooms / args.interval
    print("Table 2 - instantaneous load (timing scenarios, not measured throughput)")
    print(f"  Average sampling:        edge ingress {average_ingress:.0f} readings/s, cloud events {average_ingress * args.event_rate:.1f}/s")
    print(f"  Synchronised worst case: edge ingress up to {args.rooms} readings/s, cloud events up to {args.rooms}/s if every room is non-normal")
    print(f"  Lambda concurrency needed at worst case (Little's law, {args.max_ms:g} ms): about {args.rooms * args.max_ms / 1000:.1f}\n")

    rates = [0.0, 0.01, 0.051, 0.10, 0.25, 0.50, 0.75, 1.0]
    rows = [(rate, readings * rate, lambda_cost(readings * rate, args.billed_ms, args.memory_mb)) for rate in rates]
    print("Figure 2 - event-rate sensitivity (edge-first)")
    for rate, invocations, cost in rows:
        print(f"  {rate:>6.1%}  {invocations / 1e6:8.1f} M invocations  US${cost:7.2f}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "event_rate",
                "edge_first_invocations",
                "edge_first_cost_usd",
                "cloud_first_invocations",
                "cloud_first_cost_usd",
            ])
            for rate, invocations, cost in rows:
                writer.writerow([rate, round(invocations), round(cost, 4), round(cloud_first), round(cloud_cost, 4)])
        print(f"\nWrote {args.csv}")


if __name__ == "__main__":
    main()
