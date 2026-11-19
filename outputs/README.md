# Generated outputs

Local experiment results, logs and temporary data are written here and are ignored by Git. The reference CLI examples create proxy.json, bridge.json, bridge_unchanged.json and missingness_pilot.json. `blind-tasks` creates the answer-separated synthetic task bundle and response template; `blind-eval` creates a scoring report after optional external JSON responses are supplied. Pilot and evaluator reports contain synthetic scoring answers and are not model prompts or clinical results.

`blind-infer --dry-run` saves a request preview. A live `blind-infer` run saves a per-task checkpoint and a separate response envelope consumed by `blind-eval`; completed and failed attempts remain in the run record. See [the model-run guide](../docs/protocols/synthetic_llm_inference.md). Mock-service outputs test the interface and are not model results.
