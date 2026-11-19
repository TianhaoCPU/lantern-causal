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
| Target-endpoint ordering helper | Implemented as a transparent deterministic ordering utility. Optimality and statistical guarantees are not claimed. |
| General inflation/LP solver | Not implemented. |
| LLM provider integration and blinded evaluation | Not implemented. |
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
├── llm/            # Candidate proposal contract and prompt; no provider call
├── recovery/       # Risk-difference and proxy-based recovery utilities
├── experiments.py  # Reproducible JSON experiment runner
├── planning.py     # Target-endpoint candidate ordering
└── synthetic.py    # Exact synthetic data-generating mechanisms
configs/experiments # Versioned reference-case settings
datasets/literature # Local corpus; article text and abstracts ignored by Git
docs/                # Paper framework, protocols, decisions and asset inventory
tools/               # Corpus rebuild, PubMed search and optional OCR utilities
tests/               # Numerical and interface regression checks
~~~

The paper framework is in [docs/paper_framework.md](docs/paper_framework.md). Detailed inherited protocols are preserved in [docs/protocols](docs/protocols/); older planning material is in [docs/archive](docs/archive/).

## Method boundary

The implemented cut-inflation test evaluates a necessary condition for **one binary causal structure**: three observed variables with pairwise independent latent sources, under the stated ancestry assumptions and without direct arrows. It can return an incompatibility certificate for that candidate. It does not search arbitrary clinical DAGs, prove compatibility when the constraint passes, or uniquely label a clinical cause.

Recoverability is evaluated for a specified outcome and target. The calibrated-proxy routine additionally requires a known nonsingular proxy measurement matrix, proxy-error independence, recording independence conditional on the hidden state and outcome, and cell support. Without those assumptions, the code does not return its recovered point estimate. The risk-difference endpoint-ordering helper is a starting point for experiments; it is not an optimal active-testing policy or an inferential guarantee.

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
