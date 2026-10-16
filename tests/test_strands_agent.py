"""Actual SDK integration with offline providers; no credentials or model downloads."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from agent_arch.frameworks import create_agent, selected_framework
from agent_arch.local_agent import LocalAgent, ROOT, SYSTEM_PROMPT
from agent_arch.workbench import DEFAULT_SPEC, evaluated, plan, validated_spec

HAS_STRANDS = importlib.util.find_spec("strands") is not None


def response(text="", calls=None):
    return {"message": {"content": text, "tool_calls": calls or []},
            "usage": {"input_tokens": 10, "output_tokens": 5}}


def call(name, **args):
    return {"function": {"name": name, "arguments": args}}


class FrameworkTests(unittest.TestCase):
    def test_default_and_explicit_selection(self):
        spec = validated_spec(DEFAULT_SPEC)
        with patch.dict("os.environ", {"AGENT_FRAMEWORK": ""}):
            self.assertEqual(selected_framework(spec), "custom-python")
            spec["framework"] = "strands"
            self.assertEqual(plan(spec, "local")["framework"], "strands")
            self.assertIn("PLANNED", plan(spec, "aws")["deployment_status"])
        with patch.dict("os.environ", {"AGENT_FRAMEWORK": "invalid"}):
            with self.assertRaises(ValueError):
                selected_framework(spec)

    def test_missing_dependency_has_install_hint(self):
        import sys
        with patch.dict(sys.modules, {"agent_arch.strands_agent": None}), \
                patch.dict("os.environ", {"AGENT_FRAMEWORK": "strands"}):
            with self.assertRaisesRegex(RuntimeError, r"\[strands\]"):
                create_agent({}, "unused")


@unittest.skipUnless(HAS_STRANDS, "Install .[strands] to run actual SDK integration")
class StrandsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.spec = validated_spec(ROOT / "architectures/portable-research-strands.json")
        from agent_arch.strands_agent import StrandsAgent
        self.agent = StrandsAgent(self.spec, Path(self.tmp.name) / "m.db", provider="rules")
        # Even an accidental default cloud provider or SDK network call must fail.
        network = patch("socket.socket.connect", side_effect=AssertionError("Network forbidden"))
        network.start()
        self.addCleanup(network.stop)

    def scripted(self, replies):
        self.agent.model = Mock(model="offline-script", chat=Mock(side_effect=replies))

    def test_rules_match_custom_and_preserve_metadata(self):
        baseline = LocalAgent(self.spec, Path(self.tmp.name) / "custom.db", provider="rules")
        for question in ("What is the refund approval threshold?", "What tier is customer cust-100?"):
            actual, expected = self.agent.run(question), baseline.run(question)
            for key in ("answer", "usage", "tool_calls", "trace", "model_turns"):
                self.assertEqual(actual[key], expected[key])
            self.assertEqual(actual["framework"], "strands")
            self.assertEqual(actual["framework_version"], "1.61.1")

    def test_ollama_provider_through_real_sdk_with_mock_http(self):
        from agent_arch.local_agent import OllamaModel
        self.agent.model = OllamaModel("local-test")
        self.agent.provider = "ollama"
        first = {"message": {"role": "assistant", "tool_calls": [
            call("lookup_customer", customer_id="cust-100")]},
                 "prompt_eval_count": 2, "eval_count": 3}
        second = {"message": {"role": "assistant", "content": "enterprise"},
                  "prompt_eval_count": 4, "eval_count": 5}
        handles = []
        for payload in (first, second):
            handle = Mock()
            handle.__enter__ = Mock(return_value=handle)
            handle.__exit__ = Mock(return_value=False)
            handle.read.return_value = json.dumps(payload).encode()
            handles.append(handle)
        with patch("agent_arch.local_agent.urlopen", side_effect=handles) as request:
            result = self.agent.run("customer tier")
        self.assertEqual(result["answer"], "enterprise")
        self.assertEqual(result["usage"], {"input_tokens": 6, "output_tokens": 8})
        payload = json.loads(request.call_args.args[0].data)
        self.assertEqual(payload["model"], "local-test")
        self.assertEqual(payload["messages"][-1]["tool_name"], "lookup_customer")

    def test_multiple_tools_usage_and_correlation(self):
        self.scripted([response(calls=[call("search_docs", query="refund"),
                                      call("lookup_customer", customer_id="cust-100")]), response("done")])
        result = self.agent.run("research")
        self.assertEqual(result["usage"], {"input_tokens": 20, "output_tokens": 10})
        self.assertEqual(result["tool_calls"], 2)
        messages = self.agent.model.chat.call_args.args[0]
        self.assertEqual(messages[0]["content"], SYSTEM_PROMPT)
        self.assertEqual(messages[-2]["tool_call_id"], messages[-3]["tool_calls"][0]["id"])
        self.assertEqual(messages[-1]["tool_call_id"], messages[-3]["tool_calls"][1]["id"])
        self.assertEqual(json.loads(messages[-1]["content"])["customer"]["tier"], "enterprise")

    def test_policy_denial_does_not_write(self):
        self.agent.tools.allowed = frozenset()
        self.scripted([response(calls=[call("remember", key="secret", value="x")]), response("denied")])
        result = self.agent.run("store")
        self.assertEqual(result["trace"][0]["status"], "denied_or_invalid")
        self.assertIsNone(self.agent.memory.recall("default", "secret")["value"])

    def test_persistent_session_isolation_and_fresh_conversation(self):
        self.scripted([response(calls=[call("remember", key="k", value="v")]), response("saved"),
                       response(calls=[call("recall", key="k")]), response("read")])
        self.agent.run("store", "a")
        self.agent.run("read", "b")
        self.assertEqual(len(self.agent.model.chat.call_args_list[2].args[0]), 2)
        last = self.agent.model.chat.call_args.args[0][-1]
        self.assertIsNone(json.loads(last["content"])["value"])
        self.assertEqual(self.agent.memory.recall("a", "k")["value"], "v")

    def test_tool_limit_checked_before_any_batch_side_effect(self):
        self.spec["limits"]["max_tool_calls"] = 1
        self.scripted([response(calls=[call("remember", key="k", value="v"),
                                      call("unknown")])])
        with self.assertRaisesRegex(Exception, "Maximum tool call budget"):
            self.agent.run("store")
        self.assertIsNone(self.agent.memory.recall("default", "k")["value"])
        self.assertEqual(self.agent.model.chat.call_count, 1)

    def test_model_limit_no_extra_inference(self):
        self.spec["limits"]["max_model_turns"] = 1
        self.scripted([response(calls=[call("search_docs", query="refund")])])
        with self.assertRaisesRegex(Exception, "Maximum model turn budget"):
            self.agent.run("search")
        self.assertEqual(self.agent.model.chat.call_count, 1)

    def test_unknown_and_invalid_tools_cannot_bypass_budget(self):
        self.scripted([response(calls=[call("unknown"), call("remember", key="k")]), response("failed")])
        result = self.agent.run("invalid")
        self.assertEqual(result["tool_calls"], 2)
        self.assertIsNone(self.agent.memory.recall("default", "k")["value"])
        self.assertIn("error", self.agent.model.chat.call_args.args[0][-1]["content"].lower())

    def test_invalid_prompt_and_provider_failure(self):
        self.scripted([])
        for prompt in ("", None, "x" * 5001):
            with self.assertRaises(ValueError):
                self.agent.run(prompt)
        self.agent.model.chat.assert_not_called()
        self.agent.model.chat.side_effect = OSError("provider unavailable")
        with self.assertRaisesRegex(Exception, "provider unavailable"):
            self.agent.run("hello")
        self.assertEqual(self.agent.model.chat.call_count, 1)

    def test_benchmark_same_contract_and_synthetic_label(self):
        def invoke(endpoint, task, token_env, timeout):
            self.assertNotIn("expected", task.get("input", ""))
            return self.agent.run(task["input"])
        with patch("agent_arch.__main__.invoke_endpoint", side_effect=invoke):
            result = evaluated(self.spec, "local", "http://127.0.0.1:8000/agent", 10)
        self.assertEqual(result["success_rate"], 1.0)
        self.assertIn("RULE-BASED", result["evidence_class"])
        self.assertTrue(all(r["framework"] == "strands" for r in result["results"]))
