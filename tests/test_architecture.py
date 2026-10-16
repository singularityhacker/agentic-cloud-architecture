import unittest
from pathlib import Path
from agent_arch.__main__ import bench, cost_estimate, load_profile

ROOT = Path(__file__).resolve().parents[1]


class ProfileTests(unittest.TestCase):
    def test_profiles_validate(self):
        for path in (ROOT / "architectures").glob("*.json"):
            with self.subTest(path=path.name):
                self.assertIn("id", load_profile(path))

    def test_synthetic_retry_changes_outcome(self):
        direct = bench(load_profile(ROOT / "architectures/local-direct.json"))
        retries = bench(load_profile(ROOT / "architectures/local-retry.json"))
        self.assertEqual(direct["successful_tasks"], 4)
        self.assertEqual(retries["successful_tasks"], 7)
        self.assertIn("SYNTHETIC", retries["evidence_class"])

    def test_illustrative_cost_and_guard(self):
        value = cost_estimate(load_profile(ROOT / "architectures/aws-queue-worker.json"))
        self.assertGreater(value["monthly_partial_estimate_usd"], 270)
        self.assertTrue(value["under_local_threshold"])

    def test_http_uses_no_expected(self):
        from unittest.mock import patch
        from agent_arch.__main__ import invoke_endpoint
        import json
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, amount):
                return b'{"answer":"billing"}'
        def fake_open(request, timeout):
            body = json.loads(request.data)
            self.assertNotIn("expected", body)
            self.assertNotIn("transient_failures", body)
            return Response()
        task = {"id":"t","input":"question","expected":"billing","transient_failures":2}
        with patch("agent_arch.__main__.urlopen", side_effect=fake_open):
            self.assertEqual(invoke_endpoint("http://localhost:8080/a", task, "AGENT_API_TOKEN", 5)["answer"], "billing")


if __name__ == "__main__":
    unittest.main()
