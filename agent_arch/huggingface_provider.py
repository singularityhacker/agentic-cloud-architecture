"""Hugging Face hosted *chat* adapter for the existing tool-using agent.

Requires optional huggingface_hub package, HF_TOKEN, and a model/provider that
actually supports tools. Merely existing on Hub does not mean hosted inference.
No requests during construction. This does not provision endpoints.
"""
import json
import os
from .local_agent import TOOLS


def as_dict(value):
    """Handle SDK Pydantic output without depending on a specific SDK version."""
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(exclude_none=True)
    if hasattr(value, "dict"):
        return value.dict(exclude_none=True)
    raise TypeError("Unexpected Hugging Face response type")


def chat_messages(messages):
    """Translate Ollama's tool_name to OpenAI/HF tool_call_id format."""
    out = []
    for index, message in enumerate(messages):
        if message["role"] == "tool":
            if not message.get("tool_call_id"):
                raise ValueError("Tool result has no corresponding tool_call_id")
            out.append({"role": "tool", "tool_call_id": message["tool_call_id"],
                        "content": message["content"]})
        elif message["role"] == "assistant" and message.get("tool_calls"):
            calls = []
            for n, call in enumerate(message["tool_calls"]):
                f = call["function"]
                args = f.get("arguments", {})
                calls.append({"id": call.get("id", "call_%s_%s" % (index, n)),
                              "type": "function",
                              "function": {"name": f["name"], "arguments":
                                           args if isinstance(args, str) else json.dumps(args)}})
            out.append({"role": "assistant", "content": message.get("content") or None,
                        "tool_calls": calls})
        else:
            out.append({"role": message["role"], "content": message.get("content", "")})
    return out


class HuggingFaceChatModel:
    """Matches LocalAgent's model.chat(messages) contract."""

    def __init__(self, model, provider="auto", client=None, max_tokens=512):
        self.model = model
        self.provider = provider
        self.max_tokens = max_tokens
        if client is None:
            token = os.getenv("HF_TOKEN")
            if not token:
                raise ValueError("Set HF_TOKEN to use Hugging Face hosted inference")
            try:
                from huggingface_hub import InferenceClient
            except ImportError as exc:
                raise RuntimeError("Install optional HF support: pip install -e '.[hf]'") from exc
            client = InferenceClient(api_key=token, provider=provider)
        self.client = client

    def chat(self, messages):
        result = self.client.chat_completion(
            model=self.model, messages=chat_messages(messages), tools=TOOLS,
            max_tokens=self.max_tokens, stream=False, temperature=0
        )
        data = as_dict(result)
        if not data.get("choices"):
            raise ValueError("Hugging Face returned no chat choices")
        message = data["choices"][0]["message"]
        calls = []
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            calls.append({"id": call.get("id"), "function": {
                "name": function["name"], "arguments": function.get("arguments", "{}")}})
        usage = data.get("usage") or {}
        return {"message": {"role": "assistant", "content": message.get("content") or "",
                            "tool_calls": calls},
                "usage": {"input_tokens": usage.get("prompt_tokens") or 0,
                          "output_tokens": usage.get("completion_tokens") or 0}}
