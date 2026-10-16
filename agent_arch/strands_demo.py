"""Runnable Strands example: rules by default, opt-in local Ollama inference."""
import argparse
import json
import tempfile
from pathlib import Path

from .local_agent import ROOT
from .workbench import validated_spec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("rules", "ollama"), default="rules")
    parser.add_argument("--prompt", default="What is Northstar's refund approval threshold?")
    args = parser.parse_args()
    spec = validated_spec(ROOT / "architectures/portable-research-strands.json")
    # Explicit example choice, unaffected by framework environment overrides.
    from .strands_agent import StrandsAgent
    with tempfile.TemporaryDirectory() as directory:
        agent = StrandsAgent(spec, Path(directory) / "memory.db", provider=args.provider)
        print(json.dumps(agent.run(args.prompt), indent=2))


if __name__ == "__main__":
    main()
