# LANTERN-Causal

**Latent-Mechanism Audit and Recoverability Testing with Evidence-Nominated Graphs and Inflation**

LANTERN-Causal is a research project for testing whether an unmeasured clinical mechanism changes the set of associations recoverable from partially masked data. It combines a constrained LLM proposal interface, machine-checked candidate graph constraints, causal-inflation certificates, and target-risk bounds. Its central research question is whether choosing graph tests by their effect on a target range yields useful evidence under a fixed compute budget.

The name describes the research goal, not a claim that an LLM or finite-order inflation can identify the true hidden mechanism. Each result is conditional on the supplied candidate graph family and evidence. A graph that is not rejected by a finite test is reported as **not excluded**, never as verified.

## Current state

| Component | Status |
|---|---|
| PMID-indexed literature corpus | Locally assembled: 154 records, 138 OCR full texts, 16 abstract-only records. Full-text records and abstracts are excluded from Git by default. |
| Binary triangle cut-inflation certificate | Implemented for the explicitly documented independent-pair-source triangle, using exact probabilities. |
| Candidate-contract validation | Implemented. Checks candidate count, literal evidence quotes, directed acyclicity, and node references. |
| Calibrated-proxy recovery example | Implemented and covered by exact synthetic tests. |
| Same-observation target-range bridge example | Implemented and tested. The bridge assumes an explicit common-upstream candidate graph and compares it with an independent-pair-source triangle. |
| Target-range unchanged control | Implemented with the bridge observation and certificate, adding a shared recording assumption to both candidates. |
| Stratified A/B/C missingness pilot | Implemented for a fixed synthetic cohort. It computes exact finite-cohort bounds, the MAR and exposure-conditional estimators, support failures, and witness allocations. |
| Fixed-family missingness graph dispatch | Implemented for the C/X/Y/R scaffold. It validates cited candidate graphs, maps supported A/B graphs to named estimators, and keeps ambiguous, unsupported, and joint graphs conservative. |
| Answer-separated synthetic task export and offline evaluator | Implemented as a development fixture: nine process tasks, a rule baseline, optional external JSON responses, paired synthetic masks, and denominator-preserving error summaries. It makes no provider call. |
| Target-endpoint ordering helper | Implemented as a transparent deterministic ordering utility. Optimality and statistical guarantees are not claimed. |
| General inflation/LP solver | Not implemented. |
| LLM provider integration and clinical blinded evaluation | Not implemented. The offline evaluator is a fixed synthetic harness, not a model result or the planned MIMIC study. |
| MIMIC cohort SQL, mortality follow-up adjudication and patient-level analysis | Not implemented. |
| Full paper replication across the literature corpus | Not implemented. |

This repository separates tested reference calculations from proposed experiments. Reproducing the synthetic examples does **not** establish the clinical validity of a proposed hidden cause or complete the planned MIMIC evaluation.

## Install and run

Python 3.10 or newer is required. The tested core and reference calculations use only the Python standard library.

From the repository root:

~~~bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
~~~

Run the exact calibrated-proxy reference:

~~~bash
lantern demo --config configs/experiments/proxy.json --output outputs/proxy.json
~~~

Run the same-observation target-range example:

~~~bash
lantern demo --config configs/experiments/bridge.json --output outputs/bridge.json
~~~

The proxy run reports a risk difference of **0.54 probability units**, or **54 percentage points**, and separately marks that calibrated proxy assumptions were supplied. The bridge run uses exact synthetic probabilities and reports the original observation-gate envelope and the candidate-graph conclusion after its inflation certificate. Both runs use no patient data and make no LLM API calls.

Run the control in which excluding the triangle does not change the target range:

~~~bash
lantern demo --config configs/experiments/bridge_unchanged.json --output outputs/bridge_unchanged.json
~~~

This control uses the identical observations and exclusion certificate as the bridge, but prespecifies $R\perp Y\mid X$ and visible support for **both** candidate families. Both therefore share the same point outer bound before the test; the additional assumption is part of the control and is not inferred from the observations.

Run the synthetic A/B/C missingness pilot:

~~~bash
lantern pilot --config configs/experiments/missingness_pilot.json --output outputs/missingness_pilot.json
~~~

The pilot starts from a versioned artificial cohort of 1,000 complete rows and generates 20 paired masks for each of three mechanisms. Scenario A assumes $R\perp X\mid Y,C$ and uses the MAR reconstruction; scenario B assumes $R\perp Y\mid X,C$ and uses the visible-case risk; scenario C reports the observation-gate identification interval and two allocation witnesses instead of claiming a point estimate. The report contains an exact synthetic reference risk difference of **0.0975**, or **9.75 percentage points**, actual masking rates, support failures, and paired absolute-error summaries. Its scores are kept in the output for regression checking and must not be supplied to a blinded model prompt.

Export the answer-separated synthetic process tasks and an empty response envelope:

~~~bash
lantern blind-tasks \
  --output outputs/blind_tasks.json \
  --response-template outputs/blind_responses.json
~~~

The task bundle contains only the fixed-family instructions, field definitions, target expression, nine artificial extraction-process texts, and a SHA-256 fingerprint. Six tasks specify one supported recording graph and three preserve multiple alternatives. It contains no complete rows, masking seeds, reference risk, expected graph labels, or scoring fields. After an external system returns JSON in the response envelope, score it with the same synthetic masks:

~~~bash
lantern blind-eval \
  --config configs/experiments/missingness_pilot.json \
  --responses outputs/blind_responses.json \
  --output outputs/blind_eval.json
~~~

`blind-eval` also reports the frozen rule baseline and known-graph reference. It does not call an LLM, access patient data, or verify the provenance of an externally supplied response. Its task-mask pairs reuse the 60 masks from the default pilot and are not independent clinical studies; missing, invalid, unsupported, and overconfident responses remain in their denominators.

Use the corpus locally:

~~~bash
lantern corpus --dataset datasets/literature
lantern validate-corpus --dataset datasets/literature
~~~

## Project layout

~~~text
src/lantern_causal/
├── datasets/       # PMID corpus reader, builder, and validator
├── inflation/      # Special-case observable triangle certificate
├── llm/            # Proposal contract, fixed-family dispatch and prompts; no provider call
├── recovery/       # Risk-difference, proxy and stratified recovery utilities
├── experiments.py  # Exact proxy and bridge JSON experiment runner
├── pilot.py        # Synthetic A/B/C missingness generator and scorer
├── blind.py        # Answer-separated synthetic task export and offline evaluator
├── planning.py     # Target-endpoint candidate ordering
└── synthetic.py    # Exact synthetic data-generating mechanisms
configs/experiments # Versioned reference-case settings
datasets/literature # Local corpus; article text and abstracts ignored by Git
docs/                # Paper framework, protocols, decisions and asset inventory
tools/               # Corpus rebuild, PubMed search and optional OCR utilities
tests/               # Numerical and interface regression checks
~~~

The paper framework is in [docs/paper_framework.md](docs/paper_framework.md). The executable pilot is specified in [docs/protocols/synthetic_missingness_pilot.md](docs/protocols/synthetic_missingness_pilot.md), while the planned MIMIC study is specified in [docs/protocols/missingness_recoverability.md](docs/protocols/missingness_recoverability.md). Older planning material is in [docs/archive](docs/archive/).

## Method boundary

The implemented cut-inflation test evaluates a necessary condition for **one binary causal structure**: three observed variables with pairwise independent latent sources, under the stated ancestry assumptions and without direct arrows. It can return an incompatibility certificate for that candidate. It does not search arbitrary clinical DAGs, prove compatibility when the constraint passes, or uniquely label a clinical cause.

Recoverability is evaluated for a specified outcome and target. The calibrated-proxy routine additionally requires a known nonsingular proxy measurement matrix, proxy-error independence, recording independence conditional on the hidden state and outcome, and cell support. Without those assumptions, the code does not return its recovered point estimate. The risk-difference endpoint-ordering helper is a starting point for experiments; it is not an optimal active-testing policy or an inferential guarantee.

The A/B/C pilot is a finite-cohort identification check. Its bounds use the extremal allowed missing-$X$ allocations within each $Y,C$ cell; they are not confidence intervals. The known-graph baseline applies a named conditional-independence formula supplied by the experiment design. The fixed-family adapter only recognizes the exact C/X/Y/R scaffold and leaves other graphs unsupported. The offline task evaluator checks candidate syntax and literal substrings, not semantic entailment; it is a development harness and does not infer a missingness graph, call an LLM, access MIMIC, or establish that a clinical association is causal.

## Literature corpus and GitHub publication

The corpus can be reconstructed with the corpus build tool from a local asset workspace containing the source manifest, PDFs, OCR JSON, and literature indices. See [datasets/literature/README.md](datasets/literature/README.md). To audit the existing local workspace:

~~~bash
python tools/build_corpus.py --workspace /path/to/local-assets --replace-generated
lantern validate-corpus --dataset datasets/literature --workspace /path/to/local-assets
~~~

Corpus text, abstracts, PDFs, OCR checkpoints, MIMIC patient records, model weights, credentials and experiment outputs are excluded from Git. Source PDFs have different reuse terms. Database access and derivatives retain their original conditions. Review the individual source licenses and applicable data-use agreements before sharing derived content. The root [MIT LICENSE](LICENSE) covers code contributed to this repository only; third-party materials remain under their original terms. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

**Check the Git ignore rules before the first commit.** For example:

~~~bash
git check-ignore datasets/literature/papers.jsonl
git status --short
~~~

The local path file configs/local.paths.json is ignored. Copy configs/local.paths.example.json and set external asset paths there for optional local corpus rebuilding or OCR. Do not commit credentials, patient-level data, PDFs or model files.

## Citation and terminology

Inflation certificates use the technique introduced by Wolfe, Spekkens and Fritz, *The Inflation Technique for Causal Inference with Latent Variables* ([paper](https://arxiv.org/abs/1609.00672)). This project uses their established triangle inequality as a comparison target, not as a new theorem. Any future novelty claim should be supported by a fixed-budget, held-out comparison against a fixed test order, an existing inflation implementation, and a suitable estimand-bounding baseline.

The label *risk difference* refers to a probability difference. For example, 0.54 equals 54 percentage points. The association in the current synthetic examples is not a causal effect of changing RDW.
