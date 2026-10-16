"""Local tool-using agent, intentionally not an AWS/AgentCore emulator.

Capabilities: Ollama chat and tool calls, SQLite session memory, lexical document
search, synthetic customer lookup, deterministic default-deny tool policy.
The 'rules' model is a transparent smoke-test model, not machine intelligence.
"""
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
STOPWORDS = {"a", "an", "and", "are", "at", "by", "for", "from", "how", "in",
             "is", "it", "many", "of", "on", "our", "the", "to", "what",
             "which", "with", "after", "does", "do", "we", "please", "reply", "briefly"}


def terms(text):
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOPWORDS


class Knowledge:
    def __init__(self, documents=None, customers=None):
        self.documents = documents if documents is not None else json.loads(
            (ROOT / "knowledge" / "documents.json").read_text(encoding="utf-8"))
        self.customers = customers if customers is not None else json.loads(
            (ROOT / "knowledge" / "customers.json").read_text(encoding="utf-8"))

    def search(self, query, top_k=3):
        query_terms = terms(query)
        ranked = []
        for doc in self.documents:
            title_terms = terms(doc["title"])
            body_terms = terms(doc["text"])
            score = 3 * len(query_terms & title_terms) + len(query_terms & body_terms)
            if score:
                ranked.append((score, doc))
        ranked.sort(key=lambda row: (-row[0], row[1]["id"]))
        return [{"id": doc["id"], "title": doc["title"], "text": doc["text"],
                 "lexical_score": score} for score, doc in ranked[:top_k]]

    def customer(self, customer_id):
        return next((c for c in self.customers if c["id"] == customer_id), None)


class SQLiteMemory:
    def __init__(self, database):
        self.database = str(database)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database, timeout=5) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS memories (
                         session TEXT NOT NULL, key TEXT NOT NULL,
                         value TEXT NOT NULL, PRIMARY KEY(session, key))""")

    def remember(self, session, key, value):
        with sqlite3.connect(self.database, timeout=5) as conn:
            conn.execute("INSERT OR REPLACE INTO memories(session,key,value) VALUES(?,?,?)",
                         (session, key, value))
        return {"stored": True, "key": key}

    def recall(self, session, key):
        with sqlite3.connect(self.database, timeout=5) as conn:
            found = conn.execute("SELECT value FROM memories WHERE session=? AND key=?",
                                 (session, key)).fetchone()
        return {"key": key, "value": found[0] if found else None}


TOOLS = [
    {"type": "function", "function": {
        "name": "search_docs", "description": "Search trusted internal policy documents",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Search query"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "lookup_customer", "description": "Look up synthetic customer by customer ID",
        "parameters": {"type": "object", "properties": {
            "customer_id": {"type": "string"}},
            "required": ["customer_id"]}}},
    {"type": "function", "function": {
        "name": "remember", "description": "Remember a session-scoped detail",
        "parameters": {"type": "object", "properties": {
            "key": {"type": "string"}, "value": {"type": "string"}},
            "required": ["key", "value"]}}},
    {"type": "function", "function": {
        "name": "recall", "description": "Recall a session-scoped detail by key",
        "parameters": {"type": "object", "properties": {
            "key": {"type": "string"}}, "required": ["key"]}}}
]


class Tools:
    """Local implementation; not MCP-compatible yet."""

    def __init__(self, knowledge, memory, allowed):
        self.knowledge = knowledge
        self.memory = memory
        self.allowed = frozenset(allowed)

    def call(self, session, name, arguments):
        # Never delegate authorization to a model.
        if name not in self.allowed:
            raise PermissionError("Tool denied by default-deny policy: " + name)
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be object")
        if name == "search_docs":
            return {"documents": self.knowledge.search(str(arguments["query"])[:500])}
        if name == "lookup_customer":
            return {"customer": self.knowledge.customer(str(arguments["customer_id"])[:100])}
        if name == "remember":
            key = str(arguments["key"])[:100]
            value = str(arguments["value"])[:2000]
            return self.memory.remember(session, key, value)
        if name == "recall":
            return self.memory.recall(session, str(arguments["key"])[:100])
        raise PermissionError("Unknown tool: " + name)


class OllamaModel:
    def __init__(self, model, base_url=None):
        self.model = model
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")

    def chat(self, messages):
        payload = {"model": self.model, "messages": messages, "tools": TOOLS,
                   "stream": False, "options": {"num_predict": 512}}
        request = Request(self.base_url + "/api/chat", data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read(2 * 1024 * 1024))
        message = result.get("message", {})
        usage = {"input_tokens": result.get("prompt_eval_count", 0),
                 "output_tokens": result.get("eval_count", 0)}
        return {"message": message, "usage": usage}


class RulesModel:
    """Deterministic fixture plumbing only; NOT an LLM or a model-quality test."""

    model = "rules-fixture-only"

    def chat(self, messages):
        last = messages[-1]
        if last["role"] == "user":
            question = last["content"]
            if "cust-" in question.lower() and ("tier" in question.lower() or "customer" in question.lower()):
                match = re.search(r"cust-[0-9]+", question.lower())
                args = {"customer_id": match.group(0)} if match else {"customer_id": "cust-100"}
                name = "lookup_customer"
            else:
                name = "search_docs"
                args = {"query": question}
            return {"message": {"role": "assistant", "content": "", "tool_calls": [{
                "function": {"name": name, "arguments": args}}]}, "usage": {}}
        if last["role"] == "tool":
            obj = json.loads(last["content"])
            if obj.get("customer"):
                answer = str(obj["customer"].get("tier", "not found"))
            else:
                docs = obj.get("documents", [])
                answer = docs[0]["text"] if docs else "No relevant documents found."
            return {"message": {"role": "assistant", "content": answer}, "usage": {}}
        return {"message": {"role": "assistant", "content": "No available result."}, "usage": {}}


class LocalAgent:
    def __init__(self, spec, memory_path, provider=None, knowledge=None):
        self.spec = spec
        self.knowledge = knowledge or Knowledge()
        self.memory = SQLiteMemory(memory_path)
        allowed = spec["capabilities"]["policy"]["allowed_tools"]
        self.tools = Tools(self.knowledge, self.memory, allowed)
        self.provider = provider or os.getenv("AGENT_MODEL_PROVIDER") or spec["capabilities"]["model"]["bindings"]["local"]["provider"]
        model_name = os.getenv("AGENT_MODEL") or spec["capabilities"]["model"]["bindings"]["local"]["model"]
        if self.provider == "rules":
            self.model = RulesModel()
        elif self.provider == "ollama":
            self.model = OllamaModel(model_name)
        else:
            raise ValueError("Unsupported local model provider: " + self.provider)

    def run(self, text, session_id="default"):
        if not isinstance(text, str) or not text.strip() or len(text) > 5000:
            raise ValueError("Prompt must have 1..5000 characters")
        session_id = str(session_id)[:100]
        messages = [
            {"role": "system", "content": (
                "You are an enterprise research agent operating on synthetic corporate data. "
                "Use tools to look up records and policies before answering. Prefer cited source names. "
                "Never invent policy facts. Do not claim an action occurred unless a tool completed it. "
                "You may only use the available tools. Answer briefly and accurately.")},
            {"role": "user", "content": text},
        ]
        calls, trace = 0, []
        total_usage = {"input_tokens": 0, "output_tokens": 0}
        max_turns = self.spec["limits"]["max_model_turns"]
        max_tools = self.spec["limits"]["max_tool_calls"]
        for turn in range(max_turns):
            result = self.model.chat(messages)
            usage = result.get("usage", {})
            for key in total_usage:
                total_usage[key] += int(usage.get(key, 0))
            message = result["message"]
            tool_calls = message.get("tool_calls", []) or []
            if not tool_calls:
                answer = message.get("content", "").strip()
                return {"answer": answer, "completed": bool(answer), "provider": self.provider,
                        "model": getattr(self.model, "model", "unknown"), "usage": total_usage,
                        "tool_calls": calls, "trace": trace, "model_turns": turn + 1}
            # Preserve the assistant tool-call message for Ollama protocol continuity.
            messages.append({"role": "assistant", "content": message.get("content", ""),
                             "tool_calls": tool_calls})
            for tool in tool_calls:
                calls += 1
                if calls > max_tools:
                    raise RuntimeError("Maximum tool call budget exceeded")
                function = tool["function"]
                name = function["name"]
                args = function.get("arguments", {})
                if isinstance(args, str):
                    args = json.loads(args)
                try:
                    data = self.tools.call(session_id, name, args)
                    trace.append({"tool": name, "status": "ok"})
                except (PermissionError, KeyError, ValueError, TypeError) as exc:
                    data = {"error": str(exc)}
                    trace.append({"tool": name, "status": "denied_or_invalid"})
                messages.append({"role": "tool", "tool_name": name,
                                 "content": json.dumps(data)})
        raise RuntimeError("Maximum model turn budget exceeded")
