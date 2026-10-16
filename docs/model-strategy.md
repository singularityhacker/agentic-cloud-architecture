# Domain-specific model strategy

**Thesis:** General-purpose frontier chat models are not optimal for every operation. A small specialized classifier, encoder, NER model, ASR model or reranker may deliver higher accuracy, faster inference and lower cost on a well-defined subtask. This is a hypothesis to test, not an assumed conclusion.

## Separate three independent choices

1. **Inference task:** chat/tool calling, classification, tagging, embedding, reranking, speech recognition, document processing. Each needs its own request/response and scoring contract.
2. **Model weights:** generalist versus domain-adapted models, including revision, tokenizer, license, training/eval leakage risk and hardware constraints.
3. **Hosting:** Ollama locally, Hugging Face Inference Providers or dedicated endpoint, Bedrock or SageMaker. Availability and performance differ by provider, even for identical weights.

### What is implemented now

- Portable tool-using agent can invoke a hosted Hugging Face **chat** model. Requires HF_TOKEN, optional huggingface_hub SDK, availability and tool-call support.
- `agent-arch model-benchmark` compares a deterministic majority-class baseline, a Hugging Face text classifier, and a Hugging Face chat model on exactly the same synthetic finance-sentiment fixture.
- `agent-arch model-search` discovers Hub models by task and can ask for models currently served by at least one provider. Hub listing ≠ a guarantee a particular API route or model revision will work.

### Initial experiment: FinBERT vs generalist text sentiment

[Finance sentiment experiment](../experiments/finance-sentiment.json) uses:
- Baseline: predict neutral for every message, **no inference / no charges**.
- Candidate: `ProsusAI/finbert`, a domain-specific text classifier (*candidate ID only; live hosting not guaranteed*).
- Generalist: `openai/gpt-oss-120b`, prompted for exactly one class (*candidate ID only; verify hosting*).
- Dataset: 15 synthetic, balanced news statements (positive/negative/neutral), not an authoritative or held-out industry benchmark.

~~~bash
python -m pip install -e '.[hf]'
agent-arch model-search --task text-classification --search finbert --limit 10
agent-arch model-benchmark --candidate majority
export HF_TOKEN=your_token_here
agent-arch model-benchmark --candidate finbert --allow-paid --max-tasks 15
agent-arch model-benchmark --candidate generalist --allow-paid --max-tasks 15
~~~

For real paid runs, record model ID and accessible revision (when provided), inference provider, library version, date/region if known, complete fixture, task success, macro-F1, confusion matrix, p50/p95 latency, model-specific price basis, and errors. Model accuracy cannot be inferred from a few synthetic samples.

**Cost handling:** HF classifier responses may not expose usage or per-request billing. The runner returns `null` for unknown inference cost—never silently $0. It does not reconcile provider invoices. The `--max-tasks` flag restricts how many calls it will attempt and `--allow-paid` is mandatory for any hosted inference.

## Opportunity matrix

| Business subtask | Candidate specialist type | Objective metric |
|---|---|---|
| Financial news/event sentiment | FinBERT / finance-classification family | Macro-F1 and confusion matrix by market event |
| Biomedical entity extraction | Biomedical token classifier | Entity span/type F1 and false positives |
| Enterprise RAG reranking | Cross-encoder / embedding reranker | Recall@k, nDCG, downstream grounded answers |
| Invoice parsing | Document understanding / layout model | Field-level extraction and verification |
| Security classification | Threat/content classifier | False-negative rate and false-positive cost |
| Transcription | Domain-adapted ASR | Word error rate on representative audio |
| Code-change triage | Small code classifier/embedding | Ticket routing accuracy and resolution cost |

Those additional task adapters are **planned**, not yet executable. Do not equate a model repository with a hosted endpoint; see [Inference Providers docs](https://huggingface.co/docs/inference-providers/en/index), [model discovery API](https://huggingface.co/docs/huggingface_hub/en/package_reference/hf_api), [text classification API](https://huggingface.co/docs/inference-providers/tasks/text-classification), and [dedicated endpoints](https://huggingface.co/docs/inference-endpoints/index).

## A good comparison changes one thing at a time

A **model specialization** experiment holds task labels and test data constant. An **infrastructure** comparison keeps model ID/version and, where possible, inference provider fixed. An **agent topology** comparison fixes models and tools, then changes orchestration or memory. If changing all three, label it a *system comparison*, not proof that specialized weights alone caused the difference.

Respect licensing, gated terms, sensitive input restrictions, security of downloaded artifacts, and domain-specific evaluation standards before treating a model as deployable in an enterprise.


## Curated candidate registry

[models/candidates.json](../models/candidates.json) lists verified Hub repository identities and their *possible* uses. It is **not** a database of proven best-performing models, licensing approvals, hosted availability or current prices. Discovery and benchmarking remain separate phases. A model candidate gets promoted to a production architecture only after measurable held-out business outcomes, model card/licensing review, and deployment economics have been evaluated.
