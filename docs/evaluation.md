# Advanced evaluation and benchmarking

The Command Center now has a deterministic evaluation layer for agent regression testing.

## Metrics
- Groundedness: approved facts represented in the answer.
- Completeness: expected case facts covered by the answer.
- Tool accuracy: expected tools observed during execution.
- Latency: supplied end-to-end execution time.
- Cost: supplied execution cost.
- Overall: mean of groundedness, completeness, and tool accuracy.

## Default quality gate
- Overall >= 0.80
- Latency <= 5 seconds
- Cost <= 0.25 per case

The runner is provider-agnostic so production agents can be connected without coupling scoring to an LLM provider.

## CI safety
No changes are made to .github/workflows/ci.yml.
The deterministic tests run in the existing pytest step and require no API keys, Azure resources, GitHub tokens, network calls, or model calls.
Heavy model-based benchmark suites should remain separate from PR CI to avoid flaky and expensive validation.
