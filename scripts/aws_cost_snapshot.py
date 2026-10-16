"""Opt-in read-only AWS Cost Explorer snapshot.

Requires installed AWS CLI and permissions ce:GetCostAndUsage.
Makes a real (potentially billable) AWS Cost Explorer API call.
Does not create infrastructure or place hard spend restrictions.
"""
import argparse
import datetime as dt
import json
import subprocess
import sys


def main(argv=None):
    p = argparse.ArgumentParser(description="Read actual recorded AWS billing by service")
    p.add_argument("--start", help="Inclusive YYYY-MM-DD (default: month start)")
    p.add_argument("--end", help="Exclusive YYYY-MM-DD (default: tomorrow UTC)")
    p.add_argument("--profile", help="AWS CLI named profile")
    p.add_argument("--tag-key", help="Activated cost allocation tag key (with --tag-value)")
    p.add_argument("--tag-value", help="Cost allocation tag value (with --tag-key)")
    p.add_argument("--warn-usd", type=float, help="Return exit 2 if observed total exceeds amount")
    args = p.parse_args(argv)
    if bool(args.tag_key) != bool(args.tag_value):
        p.error("--tag-key and --tag-value must both be supplied")
    today = dt.datetime.now(dt.timezone.utc).date()
    start = args.start or today.replace(day=1).isoformat()
    end = args.end or (today + dt.timedelta(days=1)).isoformat()
    if dt.date.fromisoformat(end) <= dt.date.fromisoformat(start):
        p.error("end must be after start")
    cmd = ["aws"]
    if args.profile:
        cmd += ["--profile", args.profile]
    cmd += ["ce", "get-cost-and-usage", "--time-period",
            "Start=" + start + ",End=" + end,
            "--granularity", "MONTHLY", "--metrics", "UnblendedCost",
            "--group-by", "Type=DIMENSION,Key=SERVICE", "--output", "json"]
    if args.tag_key:
        cmd += ["--filter", json.dumps({"Tags": {"Key": args.tag_key,
                                                "Values": [args.tag_value]}})]
    try:
        output = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(output.stdout)
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError) as exc:
        print("Cost Explorer read failed:", exc, file=sys.stderr)
        return 2
    services = {}
    for period in data.get("ResultsByTime", []):
        for item in period.get("Groups", []):
            name = item["Keys"][0]
            services[name] = services.get(name, 0) + float(item["Metrics"]["UnblendedCost"]["Amount"])
    total = sum(services.values())
    print(json.dumps({
        "period": {"start": start, "end_exclusive": end},
        "source": "AWS Cost Explorer recorded UnblendedCost, potentially delayed",
        "amount_usd": round(total, 4),
        "by_service_usd": {name: round(amount, 4)
                           for name, amount in sorted(services.items(),
                                                      key=lambda row: -row[1])},
        "warning": "Cost Explorer data can lag and omit pending usage. This is NOT a hard cap."
    }, indent=2))
    if args.warn_usd is not None and total > args.warn_usd:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
