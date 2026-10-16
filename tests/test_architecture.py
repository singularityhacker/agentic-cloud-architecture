import unittest
from pathlib import Path
from agent_arch.__main__ import bench, cost_estimate, load_profile

ROOT = Path(__file__).resolve().parents[1]


class ProfileTests(unittest.TestCase):
    def test_profiles_validate(self):
        for path in (ROOT / "architectures").glob("*.json"):
            with self.subTest(path=path.name):
                if path.name == "portable-research.json":
                    from agent_arch.workbench import validated_spec
                    self.assertEqual(validated_spec(path)["schema_version"], 1)
                else:
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

    def test_real_agent_research_contains_scoring(self):
        from unittest.mock import patch
        from tempfile import TemporaryDirectory
        from agent_arch.local_agent import LocalAgent
        from agent_arch.workbench import validated_spec, DEFAULT_SPEC
        with TemporaryDirectory() as temp:
            agent = LocalAgent(validated_spec(DEFAULT_SPEC),
                               memory_path=Path(temp) / "m.db", provider="rules")
            profile = {
                "id": "research-smoke", "fixture": "fixtures/enterprise_research.json",
                "retry_attempts": 1, "driver": "http",
                "model": {"input_usd_per_million": 0, "output_usd_per_million": 0}
            }
            def local_endpoint(url, task, timeout, token_env):
                return agent.run(task["input"], task.get("context", {}).get("session_id", "test"))
            with patch("agent_arch.__main__.invoke_endpoint", side_effect=local_endpoint):
                result = bench(profile, driver="http", endpoint="http://127.0.0.1:8000/agent")
            self.assertEqual(result["successful_tasks"], result["total_tasks"])
            self.assertEqual(result["total_tasks"], 4)
            self.assertEqual(result["driver"], "http")

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
