"""Framework selection is independent of model bindings and deployment targets."""
import os

FRAMEWORKS = ("custom-python", "strands")


def selected_framework(spec):
    name = os.getenv("AGENT_FRAMEWORK") or spec.get("framework", "custom-python")
    if name not in FRAMEWORKS:
        raise ValueError("Unsupported agent framework: " + str(name))
    return name


def create_agent(spec, memory_path, **kwargs):
    if selected_framework(spec) == "strands":
        try:
            from .strands_agent import StrandsAgent
        except ImportError as exc:
            raise RuntimeError("Install Strands support: pip install -e '.[strands]'") from exc
        return StrandsAgent(spec, memory_path, **kwargs)
    from .local_agent import LocalAgent
    return LocalAgent(spec, memory_path, **kwargs)
