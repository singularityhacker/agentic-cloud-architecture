import json
import tempfile
import unittest
from pathlib import Path

from agent_arch.local_agent import Knowledge, LocalAgent, SQLiteMemory, Tools
from agent_arch.workbench import DEFAULT_SPEC, plan, validated_spec


class LocalCapabilitiesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.spec = validated_spec(DEFAULT_SPEC)
        self.agent = LocalAgent(self.spec,
                                memory_path=Path(self.tmp.name) / "memory.sqlite",
                                provider="rules")

    def tearDown(self):
        self.tmp.cleanup()

    def test_plan_does_not_claim_aws_implementation(self):
        aws = plan(self.spec, "aws")
        self.assertIn("PLANNED", aws["deployment_status"])
        self.assertIn("AgentCore", aws["capability_bindings"]["runtime"]["implementation"])

    def test_model_free_agent_uses_real_tools_and_docs(self):
        result = self.agent.run("What is Northstar's refund approval threshold?", "test")
        self.assertIn("$2,500", result["answer"])
        self.assertEqual(result["provider"], "rules")
        self.assertEqual(result["tool_calls"], 1)
        self.assertEqual(result["trace"][0]["tool"], "search_docs")

    def test_lexical_retrieval_and_customer(self):
        self.assertEqual(self.agent.knowledge.search("support tickets retention")[0]["id"], "retention")
        result = self.agent.run("What tier is customer cust-100?", "test")
        self.assertIn("enterprise", result["answer"])

    def test_session_memory_persists(self):
        self.agent.tools.call("session-a", "remember", {"key": "priority", "value": "high"})
        self.assertEqual(self.agent.tools.call("session-a", "recall", {"key": "priority"})["value"], "high")
        self.assertIsNone(self.agent.tools.call("session-b", "recall", {"key": "priority"})["value"])
        other = SQLiteMemory(Path(self.tmp.name) / "memory.sqlite")
        self.assertEqual(other.recall("session-a", "priority")["value"], "high")

    def test_unauthorized_action_denied(self):
        with self.assertRaises(PermissionError):
            self.agent.tools.call("any", "issue_refund", {"amount": 1000})
        with self.assertRaises(PermissionError):
            self.agent.tools.call("any", "exec_shell", {"command": "rm -rf /"})

    def test_tool_budget_is_bounded(self):
        spec = json.loads(json.dumps(self.spec))
        spec["limits"]["max_tool_calls"] = 1
        agent = LocalAgent(spec, Path(self.tmp.name) / "bounded.sqlite", provider="rules")
        self.assertEqual(agent.run("What is the retention policy?")["tool_calls"], 1)


if __name__ == "__main__":
    unittest.main()
