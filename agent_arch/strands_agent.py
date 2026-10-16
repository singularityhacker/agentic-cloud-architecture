"""Real Strands orchestration over the workbench's portable chat/tool contracts."""
import json
from importlib.metadata import version

from strands import Agent, tool
from strands.models import Model
from strands.tools.executors import SequentialToolExecutor

from .local_agent import LocalAgent, SYSTEM_PROMPT, TOOLS, validate_prompt


def chat_messages(messages, system_prompt):
    """Translate Strands text/tool blocks into the existing provider contract."""
    result = [{"role": "system", "content": system_prompt or ""}]
    names = {}
    for message in messages:
        text, calls, responses = [], [], []
        for block in message["content"]:
            if "text" in block:
                text.append(block["text"])
            elif "toolUse" in block:
                use = block["toolUse"]
                names[use["toolUseId"]] = use["name"]
                calls.append({"id": use["toolUseId"], "function": {
                    "name": use["name"], "arguments": use["input"]}})
            elif "toolResult" in block:
                value = block["toolResult"]
                content = value["content"]
                body = "\n".join(b["text"] if "text" in b else json.dumps(b["json"])
                                 for b in content)
                responses.append({"role": "tool", "tool_call_id": value["toolUseId"],
                                  "tool_name": names[value["toolUseId"]], "content": body})
            else:
                raise ValueError("Only text and tool blocks are supported")
        if text or calls:
            item = {"role": message["role"], "content": "\n".join(text)}
            if calls:
                item["tool_calls"] = calls
            result.append(item)
        result.extend(responses)
    return result


class ChatModelAdapter(Model):
    """One invocation's bounded bridge; never constructs a default cloud model."""

    def __init__(self, backend, limits):
        self.backend, self.limits = backend, limits
        self.turns = self.calls = 0
        self.usage = {"input_tokens": 0, "output_tokens": 0}
        self.config = {"model_id": getattr(backend, "model", "unknown")}

    def get_config(self):
        return dict(self.config)

    def update_config(self, **model_config):
        raise ValueError("Configure the underlying workbench model provider instead")

    async def structured_output(self, *args, **kwargs):
        raise NotImplementedError("Structured output is not part of the chat contract")
        yield  # pragma: no cover

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        if self.turns >= self.limits["max_model_turns"]:
            raise RuntimeError("Maximum model turn budget exceeded")
        self.turns += 1
        result = self.backend.chat(chat_messages(messages, system_prompt))
        for key in self.usage:
            self.usage[key] += int(result.get("usage", {}).get(key, 0))
        message = result["message"]
        calls = message.get("tool_calls") or []
        if self.calls + len(calls) > self.limits["max_tool_calls"]:
            raise RuntimeError("Maximum tool call budget exceeded")
        self.calls += len(calls)
        yield {"messageStart": {"role": "assistant"}}
        if message.get("content"):
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": message["content"]}}}
            yield {"contentBlockStop": {}}
        for index, call in enumerate(calls):
            fn = call["function"]
            args = fn.get("arguments", {})
            yield {"contentBlockStart": {"start": {"toolUse": {
                "toolUseId": call.get("id") or f"call_{self.turns}_{index}", "name": fn["name"]}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {
                "input": args if isinstance(args, str) else json.dumps(args)}}}}
            yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "tool_use" if calls else "end_turn"}}


class StrandsAgent(LocalAgent):
    framework = "strands"

    def run(self, text, session_id="default"):
        validate_prompt(text)
        session_id = str(session_id)[:100]
        trace = []
        model = ChatModelAdapter(self.model, self.spec["limits"])

        def invoke(name, arguments):
            try:
                data = self.tools.call(session_id, name, arguments)
                trace.append({"tool": name, "status": "ok"})
            except (PermissionError, KeyError, ValueError, TypeError) as exc:
                data = {"error": str(exc)}
                trace.append({"tool": name, "status": "denied_or_invalid"})
            return json.dumps(data)

        def search_docs(query: str):
            return invoke("search_docs", {"query": query})

        def lookup_customer(customer_id: str):
            return invoke("lookup_customer", {"customer_id": customer_id})

        def remember(key: str, value: str):
            return invoke("remember", {"key": key, "value": value})

        def recall(key: str):
            return invoke("recall", {"key": key})

        functions = [search_docs, lookup_customer, remember, recall]
        registered = [tool(name=s["function"]["name"],
                           description=s["function"]["description"],
                           inputSchema={"json": s["function"]["parameters"]})(f)
                      for s, f in zip(TOOLS, functions)]
        agent = Agent(model=model, system_prompt=SYSTEM_PROMPT,
                      tools=registered, callback_handler=None,
                      tool_executor=SequentialToolExecutor(), retry_strategy=None,
                      context_manager=False)
        result = agent(text)
        answer = "\n".join(b["text"] for b in result.message["content"] if "text" in b).strip()
        return {"answer": answer, "completed": bool(answer), "provider": self.provider,
                "model": getattr(self.model, "model", "unknown"), "framework": self.framework,
                "framework_version": version("strands-agents"), "usage": model.usage,
                "tool_calls": model.calls, "model_turns": model.turns, "trace": trace}
