"""CLI for capability specs, local containers and real local/remote evaluation.

AWS deployment not implemented by this entrypoint and cannot be triggered
accidentally. Existing queue CDK is a distinct, explicitly optional example.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse

from agent_arch.__main__ import ROOT, bench

DEFAULT_SPEC = ROOT / "architectures" / "portable-research.json"
COMPOSE_FILE = ROOT / "deploy" / "local" / "compose.yaml"
KNOWN_TOOLS = {"search_docs", "lookup_customer", "remember", "recall"}
MAPPINGS = {
    "model": {"local": "Ollama chat + tool calls", "aws": "Amazon Bedrock"},
    "runtime": {"local": "Python tool-using HTTP agent", "aws": "AgentCore Runtime"},
    "memory": {"local": "SQLite session key/value", "aws": "AgentCore Memory"},
    "retrieval": {"local": "Lexical local document search", "aws": "Bedrock Knowledge Bases"},
    "tools": {"local": "Built-in tools; MCP planned", "aws": "AgentCore Gateway (MCP)"},
    "policy": {"local": "Deterministic tool allowlist", "aws": "AgentCore Policy (Cedar/Dogwood)"},
    "observability": {"local": "JSON tool trace and token counts", "aws": "CloudWatch/X-Ray/OTEL"},
}


def validated_spec(path):
    spec_path = Path(path).resolve()
    if not spec_path.is_relative_to(ROOT):
        raise ValueError("Specification must be a file inside this repository")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("schema_version") != 1 or not isinstance(spec.get("name"), str):
        raise ValueError("Expected schema_version 1 and name string")
    c = spec["capabilities"]
    if c["policy"]["default"] != "deny":
        raise ValueError("Only deterministic default-deny local policies are supported")
    tools = c["tools"]
    allowed = c["policy"]["allowed_tools"]
    if not isinstance(tools, list) or not isinstance(allowed, list):
        raise ValueError("tools/allowed_tools must be lists")
    if (not set(tools) <= KNOWN_TOOLS or not set(allowed) <= set(tools)
            or len(set(tools)) != len(tools)):
        raise ValueError("Tools must be unique built-in names; policy allowed_tools subset")
    if c["model"]["provider"] not in ("ollama", "rules"):
        raise ValueError("Local target supports only ollama or rules model provider")
    for key in ("max_model_turns", "max_tool_calls"):
        value = spec["limits"].get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 30:
            raise ValueError(key + " must be integer in [1,30]")
    fixture_path = (ROOT / spec["evaluation"]["fixture"]).resolve()
    if not fixture_path.is_relative_to(ROOT) or not fixture_path.is_file():
        raise ValueError("Evaluation fixture must exist within repository")
    return spec


def plan(spec, target):
    return {
        "architecture": spec["name"], "target": target,
        "deployment_status": "working local Docker Compose target"
        if target == "local" else "PLANNED ONLY: no AgentCore deployment implementation",
        "capability_bindings": {
            key: {"implementation": mapping[target],
                  "status": "local prototype" if target == "local" else "planned"}
            for key, mapping in MAPPINGS.items()
        },
        "limitations": (
            "Local providers are functional substitutes, not AWS emulators; "
            "Docker/Ollama hardware and model availability required."
            if target == "local" else
            "Do not treat the existing SQS/Lambda CDK skeleton as deployment of "
            "this AgentCore research agent."
        )
    }


def compose_command(verb, spec_path):
    env = os.environ.copy()
    env["AGENT_SPEC"] = str(Path(spec_path).resolve().relative_to(ROOT))
    args = ["docker", "compose", "-f", str(COMPOSE_FILE)]
    args += (["up", "-d", "--build"] if verb == "deploy" else ["down"])
    try:
        return subprocess.call(args, cwd=ROOT, env=env)
    except FileNotFoundError:
        print("Docker Compose is required for local deployment.", file=sys.stderr)
        return 2


def evaluated(spec, target, endpoint, timeout):
    fixture = spec["evaluation"]["fixture"]
    # Matches the old runner's profile inputs without inventing cloud prices.
    evaluation_profile = {
        "id": spec["name"] + ":" + target, "fixture": fixture,
        "driver": "http", "retry_attempts": 1,
        "model": {"input_usd_per_million": 0, "output_usd_per_million": 0}
    }
    result = bench(evaluation_profile, driver="http", endpoint=endpoint, timeout=timeout)
    result["target"] = target
    result["model_note"] = "Reported usage only; no model pricing or cloud billing reconciliation"
    return result


def write_report(report, path):
    output = json.dumps(report, indent=2) + "\n"
    if path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(output, encoding="utf-8")
    print(output)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Portable agent architecture workbench")
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC,
                        help="Path to versioned capability specification")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "deploy", "stop", "benchmark"):
        p = sub.add_parser(name)
        p.add_argument("--target", required=True, choices=("local", "aws"))
        if name == "benchmark":
            p.add_argument("--endpoint", default=None)
            p.add_argument("--timeout", type=float, default=120)
            p.add_argument("--output", type=Path)
            p.add_argument("--allow-paid", action="store_true")
    comp = sub.add_parser("compare")
    comp.add_argument("--targets", default="local,aws", help="local,aws")
    comp.add_argument("--local-endpoint", default="http://127.0.0.1:8000/agent")
    comp.add_argument("--aws-endpoint", required=True)
    comp.add_argument("--allow-paid", action="store_true")
    comp.add_argument("--same-model-confirmed", action="store_true")
    comp.add_argument("--output", type=Path)
    comp.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args(argv)
    try:
        spec = validated_spec(args.spec)
        if args.command == "plan":
            write_report(plan(spec, args.target), None)
            return 0
        if args.command in ("deploy", "stop"):
            if args.target == "aws":
                print("AWS AgentCore deployment NOT YET IMPLEMENTED. Use plan --target aws; "
                      "the separate infrastructure/ CDK stack is queue-only.", file=sys.stderr)
                return 2
            return compose_command(args.command, args.spec)
        if args.command == "benchmark":
            endpoint = args.endpoint or (
                "http://127.0.0.1:8000/agent" if args.target == "local" else None)
            if args.target == "aws" and not args.allow_paid:
                raise ValueError("AWS evaluation may incur charges; supply --allow-paid")
            if not endpoint:
                raise ValueError("Specify --endpoint for an externally deployed AWS agent")
            write_report(evaluated(spec, args.target, endpoint, args.timeout), args.output)
            return 0
        if args.targets != "local,aws":
            raise ValueError("Only --targets local,aws is supported")
        if not args.allow_paid:
            raise ValueError("AWS comparison may incur charges; supply --allow-paid")
        local = evaluated(spec, "local", args.local_endpoint, args.timeout)
        aws = evaluated(spec, "aws", args.aws_endpoint, args.timeout)
        write_report({
            "scenario": spec["name"],
            "comparison": [local, aws],
            "same_model_confirmed_by_operator": args.same_model_confirmed,
            "limitations": "Cloud endpoint supplied externally; AWS AgentCore deployment "
                           "not provided. No billing or infrastructure throughput parity. "
                           "Do not interpret host-only performance if models/prompts/tools differ."
        }, args.output)
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
