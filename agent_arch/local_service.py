"""Local-only HTTP entry point; exposed on host loopback by Docker Compose."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from agent_arch.local_agent import ROOT
from agent_arch.frameworks import create_agent
from agent_arch.workbench import validated_spec


def configured_agent():
    spec_path = (ROOT / os.getenv("AGENT_SPEC", "architectures/portable-research.json")).resolve()
    if not spec_path.is_relative_to(ROOT):
        raise ValueError("AGENT_SPEC must stay within repository")
    spec = validated_spec(spec_path)
    db = os.getenv("AGENT_MEMORY_DB", "/tmp/agentic-cloud-memory.db")
    return create_agent(spec, memory_path=db)


AGENT = None


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self.respond(200, {"ok": True, "model_provider": AGENT.provider,
                               "framework": AGENT.framework,
                               "note": "Process alive; model availability not guaranteed"})
        else:
            self.respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/agent":
            self.respond(404, {"error": "not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 64 * 1024:
                raise ValueError("Request body must be 1..65536 bytes")
            request = json.loads(self.rfile.read(size))
            context = request.get("context", {})
            if not isinstance(context, dict):
                raise ValueError("context must be object")
            result = AGENT.run(request.get("input", ""),
                               session_id=context.get("session_id", "default"))
            self.respond(200, result)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.respond(400, {"error": str(exc)})
        except Exception as exc:
            # Model may not yet be downloaded, server unavailable, or tool budget exceeded.
            self.respond(502, {"error": type(exc).__name__ + ": " + str(exc)[:150]})

    def log_message(self, fmt, *args):
        # Avoid logging user prompts into terminal output by default.
        if os.getenv("AGENT_HTTP_ACCESS_LOG") == "1":
            super().log_message(fmt, *args)


def main():
    global AGENT
    AGENT = configured_agent()
    host = os.getenv("AGENT_BIND", "127.0.0.1")
    port = int(os.getenv("AGENT_PORT", "8000"))
    print("Local agent listening on %s:%s provider=%s" % (host, port, AGENT.provider),
          flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
