"""Benchmark task-specific models on labeled data, without an LLM agent wrapper.

Hugging Face requests require explicit --allow-paid. The offline majority
baseline is a sanity check, not a model-quality claim. Zero SDK/network use in
offline mode. Provider availability, model license and data privacy are caller's
responsibility.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import sys
import time

from agent_arch.__main__ import ROOT, percentile


def experiment_from(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("Experiment must live inside the repository")
    data = json.loads(path.read_text(encoding="utf-8"))
    labels = data["labels"]
    if not isinstance(labels, list) or len(labels) < 2 or not all(isinstance(x, str) for x in labels):
        raise ValueError("At least two string labels required")
    if len(set(labels)) != len(labels):
        raise ValueError("Labels must be distinct")
    fixture = (ROOT / data["fixture"]).resolve()
    if not fixture.is_relative_to(ROOT.resolve()) or not fixture.is_file():
        raise ValueError("Fixture must be in the repository")
    tasks = json.loads(fixture.read_text(encoding="utf-8"))
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("Fixture must be a nonempty list")
    for task in tasks:
        if (task.get("label") not in labels or
                not isinstance(task.get("text"), str) or not task["text"].strip()):
            raise ValueError("Every task must have nonempty text and a valid label")
    candidates = data["candidates"]
    if not isinstance(candidates, dict) or not candidates:
        raise ValueError("Candidates required")
    for name, cfg in candidates.items():
        if cfg.get("type") not in ("majority-baseline", "hf-text-classification", "hf-chat-classification"):
            raise ValueError("Unsupported candidate type: " + name)
        if cfg["type"].startswith("hf-") and not cfg.get("model_id"):
            raise ValueError("Hosted candidate must specify model_id: " + name)
        if cfg["type"] == "majority-baseline" and cfg.get("label") not in labels:
            raise ValueError("Invalid majority baseline label")
    return data, tasks


def _field(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _label_from_text(answer, labels):
    stripped = answer.strip().strip(' "\'\t\n.,:;!').casefold()
    exact = {lab.casefold(): lab for lab in labels}
    # Strict label matching: no keyword substring guessing such as "not positive".
    return exact.get(stripped)


class HostedClassifier:
    def __init__(self, cfg, token=None, client=None):
        self.cfg = cfg
        if client is None:
            token = token or os.getenv("HF_TOKEN")
            if not token:
                raise ValueError("HF_TOKEN required for hosted model evaluation")
            try:
                from huggingface_hub import InferenceClient
            except ImportError as exc:
                raise RuntimeError("Install Hugging Face support with pip install -e '.[hf]'") from exc
            client = InferenceClient(api_key=token, provider=cfg.get("inference_provider", "auto"))
        self.client = client

    def predict(self, text, labels):
        model = self.cfg["model_id"]
        if self.cfg["type"] == "hf-text-classification":
            response = self.client.text_classification(text, model=model)
            if not isinstance(response, list):
                response = [response]
            if not response:
                raise ValueError("Classifier returned no predictions")
            best = max(response, key=lambda x: float(_field(x, "score", 0)))
            return {"label": _field(best, "label"), "confidence": _field(best, "score"),
                    "input_tokens": None, "output_tokens": None}
        prompt = ("Classify the financial sentiment of the text below. Respond with exactly "
                  "one of these labels and nothing else: " + ", ".join(labels) + ".")
        response = self.client.chat_completion(model=model,
                                               messages=[{"role": "system", "content": prompt},
                                                         {"role": "user", "content": text}],
                                               max_tokens=20, temperature=0, stream=False)
        choices = _field(response, "choices") or []
        if not choices:
            raise ValueError("Chat provider returned no response choices")
        content = _field(_field(choices[0], "message"), "content") or ""
        usage = _field(response, "usage")
        return {"label": _label_from_text(content, labels), "raw_response": content[:100],
                "confidence": None, "input_tokens": _field(usage, "prompt_tokens"),
                "output_tokens": _field(usage, "completion_tokens")}


def measure(experiment, tasks, candidate_name, predictor=None, max_tasks=20, allow_paid=False):
    candidates = experiment["candidates"]
    if candidate_name not in candidates:
        raise ValueError("Unknown candidate: " + candidate_name)
    cfg = candidates[candidate_name]
    paid = cfg["type"].startswith("hf-")
    if paid and not allow_paid:
        raise ValueError("Hosted inference can incur charges: explicitly supply --allow-paid")
    if not isinstance(max_tasks, int) or not 1 <= max_tasks <= 100:
        raise ValueError("max_tasks must be integer in [1, 100]")
    workload = tasks[:max_tasks]
    if predictor is None and paid:
        predictor = HostedClassifier(cfg)
    outcomes = []
    for task in workload:
        start = time.perf_counter()
        predicted, confidence, usage = None, None, {}
        error = None
        try:
            if cfg["type"] == "majority-baseline":
                predicted = cfg["label"]
            else:
                record = predictor.predict(task["text"], experiment["labels"])
                predicted = record["label"]
                confidence = record.get("confidence")
                usage = {"input_tokens": record.get("input_tokens"),
                         "output_tokens": record.get("output_tokens")}
        except Exception as exc:
            error = "%s: %s" % (type(exc).__name__, str(exc)[:240])
        outcomes.append({
            "id": task["id"], "expected": task["label"], "predicted": predicted,
            "correct": predicted == task["label"], "confidence": confidence,
            "latency_ms": round((time.perf_counter() - start) * 1000, 3),
            "usage": usage, "error": error
        })
    confusion = {expected: {pred: 0 for pred in experiment["labels"] + ["invalid"]}
                 for expected in experiment["labels"]}
    for outcome in outcomes:
        predicted = outcome["predicted"]
        confusion[outcome["expected"]][predicted if predicted in experiment["labels"] else "invalid"] += 1
    macro_f1 = []
    for label in experiment["labels"]:
        tp = confusion[label][label]
        fp = sum(confusion[other][label] for other in experiment["labels"] if other != label)
        fn = sum(n for other, n in confusion[label].items() if other != label)
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        macro_f1.append(2 * precision * recall / (precision + recall) if precision + recall else 0)
    priced = None
    # Do not pretend HF text-classification per-call billing is inferable from missing tokens.
    if paid and all(all(outcome["usage"].get(key) is not None
                        for key in ("input_tokens", "output_tokens")) for outcome in outcomes):
        rates = cfg.get("hypothetical_token_prices_usd_per_million")
        if rates and not any(outcome["error"] for outcome in outcomes):
            priced = round(sum(
                outcome["usage"]["input_tokens"] * rates["input"] +
                outcome["usage"]["output_tokens"] * rates["output"]
                for outcome in outcomes
            ) / 1000000, 6)
    successes = sum(outcome["correct"] for outcome in outcomes)
    elapsed = [outcome["latency_ms"] for outcome in outcomes]
    return {
        "experiment": experiment["id"], "candidate": candidate_name, "candidate_type": cfg["type"],
        "model_id": cfg.get("model_id"), "inference_provider": cfg.get("inference_provider"),
        "model_revision": cfg.get("revision"), "license": cfg.get("license"),
        "evidence_class": "DETERMINISTIC MAJORITY-CLASS BASELINE; NOT MODEL INFERENCE"
        if not paid else "REAL HOSTED INFERENCE; PROVIDER PERFORMANCE NOT CLOUD ARCHITECTURE PERFORMANCE",
        "attempts": len(outcomes), "correct": successes,
        "accuracy": round(successes / len(outcomes), 4),
        "macro_f1": round(sum(macro_f1) / len(macro_f1), 4),
        "p50_latency_ms": percentile(elapsed, 0.5),
        "p95_latency_ms": percentile(elapsed, 0.95),
        "confusion": confusion, "results": outcomes,
        "estimated_inference_usd": priced,
        "cost_limitations": "No billing reconciliation. Null cost means unpriced/unknown, NOT free. "
                            "Provider auto-routing and revisions may change unless pinned. "
                            "Some models are unavailable on hosted inference."
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate specialist vs generalist models on labeled domain tasks")
    parser.add_argument("--experiment", type=Path, default=ROOT / "experiments" / "finance-sentiment.json")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--max-tasks", type=int, default=20)
    parser.add_argument("--allow-paid", action="store_true",
                        help="Explicit opt-in to potentially billable Hugging Face inference")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        spec, tasks = experiment_from(args.experiment)
        report = measure(spec, tasks, args.candidate, max_tasks=args.max_tasks,
                         allow_paid=args.allow_paid)
        result = json.dumps(report, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result, encoding="utf-8")
        print(result)
        return 0
    except (ValueError, TypeError, KeyError, ImportError, OSError, json.JSONDecodeError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
