import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import unittest

from agent_arch.domain_bench import (
    HostedClassifier, _label_from_text, experiment_from, measure
)
from agent_arch.__main__ import ROOT


class DomainBenchTests(unittest.TestCase):
    def setUp(self):
        self.spec, self.tasks = experiment_from(ROOT / "experiments/finance-sentiment.json")

    def test_majority_offline_and_metrics(self):
        r = measure(self.spec, self.tasks, "majority")
        self.assertEqual(r["attempts"], 15)
        self.assertEqual(r["correct"], 5)
        self.assertAlmostEqual(r["accuracy"], 5 / 15, places=4)
        self.assertAlmostEqual(r["macro_f1"], 1 / 6, places=4)
        self.assertIsNone(r["estimated_inference_usd"])
        self.assertIn("DETERMINISTIC", r["evidence_class"])

    def test_paid_requires_explicit_opt_in(self):
        with self.assertRaisesRegex(ValueError, "allow-paid"):
            measure(self.spec, self.tasks, "finbert")
        with self.assertRaisesRegex(ValueError, "allow-paid"):
            measure(self.spec, self.tasks, "generalist")

    def test_hf_text_classifier_with_mock_sdk(self):
        cfg = self.spec["candidates"]["finbert"]
        fake = MagicMock()
        fake.text_classification.return_value = [
            {"label": "neutral", "score": 0.12},
            {"label": "positive", "score": 0.88}]
        model = HostedClassifier(cfg, client=fake)
        outcome = model.predict("profits rose", self.spec["labels"])
        self.assertEqual(outcome["label"], "positive")
        r = measure(self.spec, self.tasks[:2], "finbert",
                    predictor=model, allow_paid=True)
        self.assertEqual(r["attempts"], 2)
        self.assertIsNone(r["estimated_inference_usd"])

    def test_hf_chat_classifier_and_exact_label_parse(self):
        cfg = self.spec["candidates"]["generalist"]
        fake = MagicMock()
        fake.chat_completion.return_value = {
            "choices": [{"message": {"content": "positive"}}],
            "usage": {"prompt_tokens": 80, "completion_tokens": 2}}
        model = HostedClassifier(cfg, client=fake)
        self.assertEqual(model.predict("profits rose", self.spec["labels"])["label"], "positive")
        self.assertIsNone(_label_from_text("not positive", self.spec["labels"]))
        self.assertEqual(_label_from_text(' "negative." ', self.spec["labels"]), "negative")

    def test_max_tasks_limits_requests(self):
        with self.assertRaisesRegex(ValueError, "max_tasks"):
            measure(self.spec, self.tasks, "majority", max_tasks=0)


if __name__ == "__main__":
    unittest.main()
