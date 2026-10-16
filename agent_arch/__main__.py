"""Offline-first architecture / cost / benchmark CLI. No AWS API calls."""
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RATE_FILE = ROOT / "catalog" / "rates.json"


def load_json(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def load_profile(path):
    profile = load_json(path)
    needed = ("id", "scenario", "target", "driver", "fixture", "model",
              "workload", "usage", "cost_policy", "retry_attempts")
    missing = [key for key in needed if key not in profile]
    if missing:
        raise ValueError("Missing profile fields: " + ", ".join(missing))
    if profile["target"] not in ("aws", "local"):
        raise ValueError("target must be aws or local")
    if profile["driver"] not in ("fixture", "http"):
        raise ValueError("driver must be fixture or http")
    retries = profile["retry_attempts"]
    if not isinstance(retries, int) or isinstance(retries, bool) or not 1 <= retries <= 10:
        raise ValueError("retry_attempts must be an integer between 1 and 10")
    available_meters = load_json(RATE_FILE)["meters"]
    unknown = set(profile["usage"]) - set(available_meters)
    if unknown:
        raise ValueError("Unknown usage meter(s): " + ", ".join(sorted(unknown)))
    for section in ("usage", "workload"):
        for key, value in profile[section].items():
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError("Invalid non-negative number in " + section + "." + key)
    for key in ("input_usd_per_million", "output_usd_per_million"):
        value = profile["model"].get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise ValueError("Model rate must be finite and non-negative: " + key)
    limit = profile["cost_policy"].get("monthly_estimate_cap_usd")
    if not isinstance(limit, (float, int)) or isinstance(limit, bool) or not math.isfinite(limit) or limit < 0:
        raise ValueError("monthly_estimate_cap_usd must be finite and non-negative")
    fixture = (ROOT / profile["fixture"]).resolve()
    if not fixture.is_relative_to(ROOT.resolve()) or not fixture.is_file():
        raise ValueError("Fixture must be an existing file inside the repository")
    return profile


def cost_estimate(profile):
    rates = load_json(RATE_FILE)["meters"]
    items = []
    for key, count in sorted(profile["usage"].items()):
        items.append({"item": key, "quantity": count,
                      "usd": round(count * rates[key]["usd_per_unit"], 6)})
    w = profile["workload"]
    calls = w["monthly_tasks"] * w["model_calls_per_task"]
    model_usd = (calls * w["input_tokens_per_call"] / 1000000 *
                 profile["model"]["input_usd_per_million"] +
                 calls * w["output_tokens_per_call"] / 1000000 *
                 profile["model"]["output_usd_per_million"])
    items.append({"item": "model.token_assumption", "quantity": calls,
                  "usd": round(model_usd, 6)})
    total = round(sum(x["usd"] for x in items), 4)
    limit = profile["cost_policy"]["monthly_estimate_cap_usd"]
    return {"profile": profile["id"], "currency": "USD", "region_assumed": "us-east-1",
            "monthly_partial_estimate_usd": total, "local_threshold_usd": limit,
            "under_local_threshold": total <= limit, "items": items,
            "limitations": "Partial offline estimate only. No free tier, egress, DynamoDB, logs, vector DB, storage extras, tax or actual AWS billing. The threshold is NOT a hard cloud cap."}


def percentile(values, share):
    ordered = sorted(values)
    if not ordered:
        return None
    return round(ordered[max(0, math.ceil(len(ordered) * share) - 1)], 3)


def invoke_endpoint(url, task, token_env, timeout):
    if not url or not url.startswith(("https://", "http://127.0.0.1:", "http://localhost:")):
        raise ValueError("Endpoint must be HTTPS or local HTTP")
    headers = {"Content-Type": "application/json"}
    token = os.getenv(token_env)
    if token:
        headers["Authorization"] = "Bearer " + token
    # Never send expected answers, even when fixture data contains them.
    payload = json.dumps({"task_id": task["id"], "input": task["input"],
                          "context": task.get("context", {})}).encode("utf-8")
    request = Request(url, data=payload, headers=headers, method="POST")
    with urlopen(request, timeout=timeout) as response:
        output = json.loads(response.read(1024 * 1024).decode("utf-8"))
    if not isinstance(output, dict) or not isinstance(output.get("answer"), str):
        raise ValueError("Endpoint must respond with JSON and string answer")
    return output


def bench(profile, driver=None, endpoint=None, token_env="AGENT_API_TOKEN", timeout=20):
    mode = driver or profile["driver"]
    if mode not in ("fixture", "http"):
        raise ValueError("Unsupported driver")
    if mode == "http" and (not endpoint or not endpoint.startswith(("https://", "http://127.0.0.1:", "http://localhost:"))):
        raise ValueError("Provide a trusted HTTPS or localhost HTTP endpoint")
    tasks = load_json(ROOT / profile["fixture"])
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("Fixture must be a nonempty JSON array")
    outcomes = []
    for task in tasks:
        start = time.perf_counter()
        response = None
        error = None
        attempts = 0
        for attempts in range(1, profile["retry_attempts"] + 1):
            try:
                if mode == "fixture":
                    if attempts <= task.get("transient_failures", 0):
                        raise RuntimeError("injected tool failure")
                    response = {"answer": task["expected"]}
                else:
                    response = invoke_endpoint(endpoint, task, token_env, timeout)
                error = None
                break
            except Exception as exc:
                error = str(exc)[:200]
        elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
        correct = False
        if response is not None:
            answer = response["answer"].strip()
            if "expected" in task:
                correct = answer == str(task["expected"]).strip()
            elif "expected_contains" in task:
                required = task["expected_contains"]
                if not isinstance(required, list) or not required:
                    raise ValueError("expected_contains must be a nonempty string list")
                correct = all(isinstance(fragment, str) and
                              fragment.casefold() in answer.casefold()
                              for fragment in required)
            else:
                raise ValueError("Task missing expected or expected_contains")
        usage = response.get("usage", {}) if response else {}
        if not isinstance(usage, dict):
            usage = {}
        outcomes.append({"task_id": task["id"], "success": correct, "attempts": attempts,
                         "elapsed_ms": elapsed_ms, "answer": response.get("answer") if response else None,
                         "error": error, "usage": usage})
    success = sum(x["success"] for x in outcomes)
    observed_model_estimate = None
    if mode == "http" and all("input_tokens" in o["usage"] and "output_tokens" in o["usage"] for o in outcomes):
        try:
            input_tokens = sum(o["usage"]["input_tokens"] for o in outcomes)
            output_tokens = sum(o["usage"]["output_tokens"] for o in outcomes)
            observed_model_estimate = round((
                input_tokens * profile["model"]["input_usd_per_million"] +
                output_tokens * profile["model"]["output_usd_per_million"]
            ) / 1000000, 6)
        except (TypeError, ValueError):
            observed_model_estimate = None
    return {
        "profile": profile["id"], "driver": mode,
        "evidence_class": "SYNTHETIC RUNNER SELF-TEST: NOT LLM OR AWS PERFORMANCE"
        if mode == "fixture" else "HTTP AGENT TASK EVALUATION: NOT AWS LOAD TEST",
        "total_tasks": len(outcomes), "successful_tasks": success,
        "success_rate": round(success / len(outcomes), 4),
        "attempts": sum(x["attempts"] for x in outcomes),
        "p50_elapsed_ms": percentile([o["elapsed_ms"] for o in outcomes], 0.5),
        "p95_elapsed_ms": percentile([o["elapsed_ms"] for o in outcomes], 0.95),
        "estimated_model_usd_from_reported_usage": observed_model_estimate,
        "results": outcomes
    }


def run(argv=None):
    parser = argparse.ArgumentParser(description="Declarative agent architecture profiling")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("catalog")
    for command in ("validate", "estimate", "guard", "bench"):
        subs.add_parser(command).add_argument("profile", type=Path)
    compare = subs.add_parser("compare")
    compare.add_argument("profiles", type=Path, nargs="+")
    bench_args = subs.choices["bench"]
    bench_args.add_argument("--driver", choices=("fixture", "http"))
    bench_args.add_argument("--endpoint")
    bench_args.add_argument("--token-env", default="AGENT_API_TOKEN")
    bench_args.add_argument("--timeout", type=float, default=20)
    bench_args.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            for name, meter in load_json(RATE_FILE)["meters"].items():
                print(name, "USD", meter["usd_per_unit"], "/", meter["unit"])
            return 0
        if args.command == "compare":
            outputs = [bench(load_profile(p), driver="fixture") for p in args.profiles]
            print(json.dumps([{k: v for k, v in x.items() if k not in ("results",)} for x in outputs], indent=2))
            return 0
        profile = load_profile(args.profile)
        if args.command == "validate":
            print("VALID:", profile["id"])
            return 0
        if args.command in ("estimate", "guard"):
            result = cost_estimate(profile)
            print(json.dumps(result, indent=2))
            return 0 if args.command == "estimate" or result["under_local_threshold"] else 2
        result = bench(profile, driver=args.driver, endpoint=args.endpoint,
                       token_env=args.token_env, timeout=args.timeout)
        serialized = json.dumps(result, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized + "\n", encoding="utf-8")
        print(serialized)
        return 0
    except (ValueError, KeyError, OSError, TypeError, json.JSONDecodeError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
