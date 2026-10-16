"""Unit tests require no Hugging Face SDK and make no network calls."""
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from agent_arch.huggingface_provider import HuggingFaceChatModel, chat_messages
from agent_arch.local_agent import LocalAgent
from agent_arch.workbench import ROOT, validated_spec


class FakeChatClient:
    def __init__(self):
        self.messages_seen = []

    def chat_completion(self, **kwargs):
        self.messages_seen.append(kwargs["messages"])
        if len(self.messages_seen) == 1:
            return {"choices": [{"message": {"content": "", "tool_calls": [
                {"id": "call_doc_1", "function": {
                    "name": "search_docs",
                    "arguments": json.dumps({"query": "Northstar refund threshold"})}}
            ]}}], "usage": {"prompt_tokens": 52, "completion_tokens": 10}}
        tool_result = kwargs["messages"][-1]
        assert tool_result["role"] == "tool"
        assert tool_result["tool_call_id"] == "call_doc_1"
        assert "$2,500" in tool_result["content"]
        return {"choices": [{"message": {"content": "The threshold is $2,500."}}],
                "usage": {"prompt_tokens": 150, "completion_tokens": 9}}


class HFAdapterTests(unittest.TestCase):
    def test_mocked_hf_tool_loop(self):
        path = ROOT / "architectures" / "portable-research-hf.json"
        spec = validated_spec(path)
        fake = FakeChatClient()
        with tempfile.TemporaryDirectory() as temp, patch(
            "agent_arch.huggingface_provider.HuggingFaceChatModel",
            side_effect=lambda model, provider: HuggingFaceChatModel(model, provider, client=fake)
        ):
            agent = LocalAgent(spec, Path(temp) / "mem.db")
            result = agent.run("What is Northstar's refund threshold?")
        self.assertIn("$2,500", result["answer"])
        self.assertEqual(result["provider"], "huggingface")
        self.assertEqual(result["usage"]["input_tokens"], 202)
        self.assertEqual(result["tool_calls"], 1)
        self.assertEqual(fake.messages_seen[1][-1]["tool_call_id"], "call_doc_1")

    def test_hf_requires_token_when_real(self):
        with patch.dict("os.environ", {"HF_TOKEN": ""}):
            with self.assertRaisesRegex(ValueError, "HF_TOKEN"):
                HuggingFaceChatModel("org/model")


if __name__ == "__main__":
    unittest.main()
