# Enterprise knowledge retrieval

**Scenario:** Answer corporate policy questions from changing documents with source citations and access constraints.

**Options:** full-context prompts, self-hosted vector RAG, or Bedrock Knowledge Bases with a managed index.

**Trade-offs:** prompt-token repetition versus ingest/index cost; retrieval quality; indexing freshness and tenant isolation. Some serverless search/vector implementations still have material minimum cost.

**Benchmark:** fixed gold-answer corpus, reference-document recall@k, grounded correctness, citation quality, P95, cost per *correct grounded* answer.
