# Make It Falsifiable: LLM-Guided Witness Acquisition for Latent Causal Graph Auditing

**Research plan: data collection, dataset construction, and experiments**

---

## 0. One-paragraph summary

In medical real-world evidence (RWE), the causal graph behind an effect estimate usually contains latent confounders (frailty, disease severity, health-seeking behaviour). Such graphs often have **no testable implications** on the variables at hand, so they are accepted on faith. Falsifiability, however, depends on *what we measure*. We propose a framework in which LLMs propose rival bias mechanisms and candidate **witnesses**: extra variables (negative controls, proxies, instruments, mediators, temporal anchors) that, once acquired, create testable constraints able to reject graphs that would **change the clinical conclusion**. A symbolic checker verifies that each witness really has testing power. A sequential e-value auditor tests the witnesses with error control, and a blame-assignment step attributes rejections either to graph edges or to the witnesses' own assumptions.

---

## 1. Research questions and hypotheses

| ID | Research question | Hypothesis |
|---|---|---|
| RQ1 | Can we decide algorithmically when adding a witness W makes a latent graph falsifiable against a rival? | A graphical criterion over V ∪ {W} (m-separation, Verma, tetrad/rank, IV inequality) is sound and efficient. |
| RQ2 | Do LLMs propose useful witnesses? | LLM proposals that pass the symbolic filter beat random and generic choices on falsification power per unit cost. |
| RQ3 | Does targeting the decision (ψ) beat targeting the whole structure? | For a fixed budget, acquisition aimed at ψ reduces ambiguity about the effect faster than structure-learning objectives. |
| RQ4 | Is the audit valid under adaptive acquisition and LLM hallucination? | E-value testing keeps type-I error ≤ α. Hallucinated witnesses cost budget but never cause false conclusions. |
| RQ5 | Can blame assignment separate "graph is wrong" from "witness is invalid"? | Triangulating witnesses with disjoint assumptions identifies the culprit better than single-witness tests. |
| RQ6 | Does audit status predict real-world validity? | RWE emulations that survive the audit agree with their RCTs more often than those that fail or are untestable. |

---

## 2. Data sources

### 2.1 Overview

| Tier | Source | Purpose | Access | Cost |
|---|---|---|---|---|
| T1 | Synthetic latent ADMGs (self-generated) | Ground truth for theory and algorithms | None | Free |
| T2 | MIMIC-IV v3.x + MIMIC-IV-Note | Semi-synthetic benchmarks and real ICU case studies | PhysioNet credentialing + CITI training + DUA | Free |
| T2 | eICU-CRD | External replication of the ICU case studies | PhysioNet credentialing | Free |
| T2 | Synthea / CMS DE-SynPUF | Pipeline development, OMOP ETL testing | Public | Free |
| T3 | OMOP CDM network data (OHDSI collaborators) or claims (Optum, MarketScan, Medicare) | RCT-DUPLICATE-style calibration | Collaboration or licence | High; stretch goal |
| Ref | Published RCT results and RCT-DUPLICATE protocols (ClinicalTrials.gov, papers) | Reference effects for the real case studies | Public | Free |
| Ref | PubMed / PMC Open Access, clinical guidelines | Retrieval corpus for grounding the LLM | Public | Free |

### 2.2 Access steps (start in week 1, since approval takes weeks)

1. **PhysioNet credentialing**: create an account, complete the CITI course "Data or Specimens Only Research", submit the credentialing application, and sign the DUAs for MIMIC-IV, MIMIC-IV-Note and eICU-CRD.
2. **LLM use with credentialed data.** Read PhysioNet's current guidance on responsible LLM use. In general, **do not send MIMIC rows or notes to public third-party chat APIs.** Allowed options:
   - **Metadata-only prompts** (variable names, schema, aggregated statistics, no patient rows) for rival generation and witness proposal.
   - **Local open-weight models** (on your own GPU) for note extraction.
   - Cloud LLM services only if PhysioNet's current policy explicitly allows the specific configuration.
3. **Retrieval corpus**: download the PMC Open Access subset (or use the PubMed E-utilities API) for epidemiology and pharmacology papers on the chosen case studies.
4. **Stretch (T3)**: contact an OHDSI node or a pharmacoepidemiology group that has RCT-DUPLICATE-style claims access. Propose that they run our code on their data (a federated setup), so we never receive the data ourselves.

### 2.3 Real case studies (observational result contradicted or not confirmed by RCTs)

Choose cases where the "true" answer is anchored by trials, and that can be run in ICU data:

| Case | Exposure → Outcome | Suspected bias | RCT anchor | Candidate witnesses to (re)discover |
|---|---|---|---|---|
| C1 | Pre-admission statin use → sepsis mortality | Healthy-user / adherer bias | SAILS (2014): no mortality benefit | Negative control outcomes (e.g., accidental injury), other preventive-care markers, frailty proxies |
| C2 | Vitamin C (± hydrocortisone, thiamine) → sepsis mortality | Confounding by indication, temporal and secular trends | VICTAS (2020), LOVIT (2022): no benefit / possible harm | Time-window negative controls, prescriber/time-period instrument, severity proxies from notes |
| C3 | Stress-ulcer prophylaxis (PPI) → GI bleeding / mortality | Confounding by severity | SUP-ICU (2018): no mortality effect | Severity proxies (≥3 for tetrad constraints), negative control outcomes |
| C4 (optional) | Early vs delayed renal replacement therapy → mortality | Immortal time, indication | AKIKI, STARRT-AKI: no benefit of early RRT | Temporal anchors, landmark-time witnesses |

> Before locking the cases, check each RCT citation and confirm the exposure is measurable in MIMIC-IV with enough patients (target ≥ 500 exposed).

---

## 3. Dataset construction: **WitnessBench**

WitnessBench has four components. Every item records the hypothesized graph, the rival graphs, the candidate witnesses, and the ground truth where it is known.

### 3.1 Common schemas

**Graph (`graph.json`)**
```json
{
  "graph_id": "C1_G0",
  "observed": ["A", "Y", "age", "sofa", "..."],
  "latent": ["U_frailty", "U_health_seeking"],
  "directed": [["age", "A"], ["A", "Y"], ["U_frailty", "Y"]],
  "bidirected": [["A", "Y"]],
  "estimand": {"type": "ATE", "treatment": "A", "outcome": "Y"},
  "identified_by": "backdoor",
  "provenance": {"source": "llm_agent:skeptic", "citations": ["PMID:..."]}
}
```

**Witness candidate (`witness.json`)**
```json
{
  "witness_id": "C1_W07",
  "name": "accidental injury admission within 1y",
  "type": "negative_control_outcome",
  "acquisition": {"channel": "structured | note_extraction | linkage | prospective",
                  "cost": 2, "source_table": "hosp.diagnoses_icd", "codes": ["..."]},
  "validity_assumptions": ["A has no causal effect on W", "W shares U_health_seeking with Y"],
  "targets_rivals": ["C1_G0 vs C1_G2"],
  "proposed_by": "llm:model_x:prompt_v3",
  "symbolic_check": {"creates_constraint": true, "constraint_type": "CI", "separates": ["G0", "G2"]}
}
```

**Audit result (`audit.json`)**: status (falsified / survived-k / untestable), e-values, blame scores per hypothesis component, load-bearing edges, recommended next witness.

### 3.2 Component A: synthetic latent graphs (T1)

Purpose: exact ground truth for RQ1–RQ5.

1. **Graph generator**
   - Sample latent ADMGs with |V| ∈ {10, 20, 50} and |U| ∈ {1, 2, 3, 5}, at varying densities.
   - Each instance has a treatment A, an outcome Y, a true graph G\*, and K = 3–10 rival graphs.
   - Rivals come from realistic bias "mutations" of G\*: add a latent confounder of A and Y, reverse a time-ordering error, add a collider (selection), or remove a mediator.
2. **Witness pool**
   - For each instance, plant a pool of 20–100 potential witnesses with known roles: valid negative controls, invalid ones (with a hidden effect of A), proxies of U, valid and invalid instruments, mediators, and irrelevant variables.
   - Assign costs to mimic the channels: structured = 1, note = 3, linkage = 10, prospective = 50.
3. **Data generation**
   - Use linear-Gaussian, nonlinear additive-noise, and binary/logistic SEMs.
   - Vary n ∈ {1k, 5k, 20k, 100k} to match EHR scale.
4. **Simulated LLM proposer** (for controlled hallucination)
   - It returns witnesses from the pool, labelled with roles, using parameters for precision, recall, a hallucination rate h ∈ {0, 0.1, 0.3, 0.5} (wrong role claimed), and a "confident-but-useless" rate.
   - This lets RQ4 be studied independently of any particular real LLM.
5. **Size**: about 2,000 instances, split train/dev/test 60/20/20 (training only for tuning hyperparameters, e.g., of the acquisition policy).

### 3.3 Component B: semi-synthetic on real covariates (T2, MIMIC-IV)

Purpose: realistic covariate distributions, missingness and note text, while keeping ground truth.

**Masking design** (key idea):
1. Build a real cohort (e.g., adult sepsis patients, first ICU stay).
2. Choose real measured variables to **hide as "latent" confounders**, e.g., the full SOFA score, lactate, or a frailty index built from many fields.
3. Simulate the treatment A and outcome Y from the real covariates **including the hidden variables**, with known effect ψ\*.
4. The other real variables (labs, diagnoses, procedures, note-derived features) become the **witness pool**. Their roles relative to the hidden variable are partly known by construction, because their correlation with the masked variable is real.
5. Ground truth: ψ\* is known, and so is which hidden variable confounds A and Y. The audit should detect that a graph omitting it is wrong, using real proxies.

Size: 3 cohorts × 5 masking choices × 4 outcome mechanisms × 5 seeds = 300 instances.

### 3.4 Component C: real case studies (T2, MIMIC-IV + eICU)

For each case C1–C4:

1. **Cohort extraction**
   - Write the target trial protocol first: eligibility, treatment strategies, time zero, outcome, follow-up, causal contrast.
   - Use SQL on MIMIC-IV (BigQuery or a local PostgreSQL build from `mimic-code`).
   - Save the code as `cohorts/C{k}/cohort.sql` along with a cohort flow diagram.
2. **Variables**
   - Covariates from structured tables (`hosp.admissions`, `hosp.diagnoses_icd`, `hosp.prescriptions`, `icu.chartevents`, `hosp.labevents`, etc.).
   - Use a pre-admission window for baseline confounders.
3. **Hypothesized graph G0**: the "naïve analyst" graph, i.e. the adjustment set a typical published observational study used.
4. **Rival graphs**
   - Generate them with the LLM rival generator (metadata-only prompts plus a retrieval corpus).
   - **Plus** an independent set from 2 clinicians and 1 epidemiologist. This is the human reference.
5. **Witness candidates**
   - Proposals from the LLM, from humans, and from a generic library (standard OHDSI-style negative controls), all merged and de-duplicated.
6. **Witness acquisition channels**
   - Structured: SQL query.
   - Note: extraction with a local LLM from `note.discharge` / `note.radiology`, **only from notes dated before time zero** for baseline witnesses.
   - Linkage: in MIMIC, out-of-hospital date of death serves as the "linkage" channel; other linkage is simulated with a cost.
7. **Reference answer**: the RCT effect estimate with its CI, plus the published observational estimate.
8. **External replication**: re-run C1–C3 in eICU-CRD, where variables allow.

### 3.5 Component D: annotation sets (human ground truth for the LLM parts)

| Set | Content | Annotators | Size | Agreement metric |
|---|---|---|---|---|
| D1: witness validity | For each LLM-proposed witness, is its claimed role (e.g., "A has no effect on W") clinically plausible? | 2 clinicians + adjudicator | ~300 witnesses | Cohen's κ (target ≥ 0.6) |
| D2: rival plausibility | Is each rival bias mechanism plausible? Rate 1–5 | 2 clinicians + 1 epidemiologist | ~100 rivals | Krippendorff's α |
| D3: note extraction | Chart-review labels for note-extracted witnesses (e.g., frailty indicators, home functional status) | 2 annotators | 200–400 notes per variable | κ; used to calibrate LLM extraction error |

Annotation workflow:
- Write a guideline document with examples.
- Run a pilot of 30 items, revise the guideline, then annotate the full set.
- Store the labels in `annotations/` (identifiers only, no PHI outside the secure environment).

### 3.6 Repository layout

```
new_paper_research/
├── RESEARCH_PLAN.md
├── data/                      # NOT committed (gitignored); credentialed data stays here
│   ├── raw/                   # MIMIC-IV, eICU, Synthea
│   ├── interim/
│   └── processed/
├── witnessbench/
│   ├── synthetic/             # Component A generator + released instances
│   ├── semisynthetic/         # Component B masking pipeline
│   ├── cases/C1..C4/          # Component C: protocol.md, cohort.sql, graphs/, witnesses/
│   └── annotations/           # Component D (de-identified IDs only)
├── src/
│   ├── graphs/                # ADMG utilities, m-separation, Verma, tetrad/rank, IV checks
│   ├── llm/                   # rival generator, witness proposer, note extractor, prompts/
│   ├── acquisition/           # decision-relevant acquisition policy
│   ├── audit/                 # e-value tests, sequential auditor, blame assignment
│   └── estimation/            # target-trial emulation, AIPW/TMLE estimators
├── experiments/               # one config + script per experiment (E1..E9)
├── results/
└── paper/
```

Rules:
- `data/` goes in `.gitignore`.
- Never commit PHI or patient rows.
- Log every prompt and LLM response, with the model ID, temperature and date, under `results/llm_logs/` for reproducibility.

---

## 4. Method components to implement (dependency order)

1. **ADMG toolkit**: m-separation, latent projection, and constraint enumeration. Constraint types:
   - conditional independences
   - Verma (nested Markov) constraints, e.g. via the `ananke` library
   - vanishing tetrads and rank constraints for proxy sets
   - Pearl/Bonet instrumental inequalities
2. **Falsifiability checker**: `separates(G, G', V, W) → {constraint, direction} | None`.
3. **Estimand-relevance scorer**: for rivals G′, compute ψ under each (identified, or bounded if not identified), then group rivals by how different their effect conclusions are.
4. **Acquisition policy**: greedy or lookahead maximization of expected ambiguity reduction about ψ per unit cost. Baselines plug into the same interface.
5. **Sequential e-value auditor**:
   - e-value tests for CI (e.g., split-likelihood-ratio or betting-based CI tests), tetrad and IV constraints.
   - e-BH / e-closure for multiplicity.
   - Planning uses only fold 1 (no outcome data); tests run on fold 2.
6. **Blame assignment**: the hypothesis is the pair (G, witness assumptions). Combine e-values across witnesses with disjoint assumption sets. Compute a posterior or minimal-hitting-set attribution of each rejection to graph edges vs witness assumptions.
7. **LLM modules**: role-played rival generator, witness proposer (structured JSON output), and local note extractor. Prompts are versioned in `src/llm/prompts/`.
8. **Estimation**: target-trial emulation with AIPW/TMLE, so the case-study effect estimates can be compared to RCTs.

---

## 5. Experiments

Report everything with 95% CIs over seeds or bootstrap. Pre-register the main hypotheses (e.g., on OSF) before running E7–E8.

### E1: Falsifiability checker correctness (RQ1). Data: A
- Compare checker output with a brute-force reference: simulate a large n and test all implied constraints.
- **Metrics**: soundness (no false "creates constraint"), completeness for each constraint type, runtime vs |V|.

### E2: Acquisition efficiency (RQ2, RQ3). Data: A, B
- **Methods**:
  - (i) ours: LLM proposals + checker + ψ-targeted acquisition
  - (ii) random witnesses
  - (iii) generic negative-control library
  - (iv) LLM proposals with no checker
  - (v) LLM proposals + checker with a structure-learning objective (information gain over the whole graph)
  - (vi) an oracle with full knowledge of witness roles (upper bound)
- **Metrics**:
  - falsification rate of wrong graphs vs cumulative cost (budget curves, area under the curve)
  - cost to reach the correct ψ conclusion
  - final ambiguity about ψ (width of the set of effects consistent with the surviving graphs)

### E3: Robustness to hallucination (RQ4). Data: A
- Vary the simulated LLM's hallucination rate h ∈ {0, 0.1, 0.3, 0.5}.
- **Metrics**: false-falsification rate (rejecting the true G\*), wasted budget, power.
- **Expected**: the false-falsification rate stays ≤ α for all h; only cost increases.

### E4: Type-I error under adaptive acquisition (RQ4). Data: A
- The true graph is fed in as the hypothesis, under many adaptive acquisition sequences.
- Compare the e-value auditor with naive p-values + Bonferroni, and with naive p-values without splitting.
- **Metrics**: empirical type-I error, power.

### E5: Blame assignment (RQ5). Data: A, B
- Plant either a wrong edge in G or an invalid witness, or both.
- **Metrics**: accuracy in attributing the rejection to the correct component, with triangulation vs single-witness.

### E6: Measurement error in LLM-extracted witnesses. Data: C + D3
- Measure extraction accuracy against chart review.
- Inject the measured differential error into semi-synthetic data (B) and test whether the corrected tests still control false falsification.
- **Metrics**: extraction F1/κ, false-falsification rate with and without error correction.

### E7: Rediscovery on real case studies (RQ2, RQ6). Data: C
- For C1–C4, run the full loop from G0.
- **Questions**:
  - (a) Does the system propose witnesses that experts consider valid (judged against D1)?
  - (b) Does the audit **falsify the naïve graph G0** in the cases where the RCT contradicted the observational result?
  - (c) After adjusting for the surviving graph(s), does the estimate or bound move toward the RCT estimate?
- Compare against witnesses chosen by human experts and against standard E-value sensitivity analysis.
- Replicate on eICU.

### E8: Calibration against RCTs (RQ6). Data: C (+ T3 if obtained)
- Over all case studies and their analytic variants (several plausible adjustment sets per case → many emulations), check whether audit status predicts RWE–RCT agreement. Use RCT-DUPLICATE agreement definitions: regulatory, estimate and standardized-difference agreement.
- **Metrics**: AUC of the audit-status / severity score in predicting agreement; compare with the E-value and with covariate-balance diagnostics.
- With T3 access, scale up to the RCT-DUPLICATE trial set.

### E9: Ablations and LLM comparison. Data: A, B, C
- Remove one module at a time: retrieval grounding, multi-role agents, symbolic checker, ψ-targeting, triangulation.
- Swap LLMs: one or two closed models through metadata-only prompts, plus 2–3 open-weight models run locally.
- **Metrics**: same as E2/E7, plus LLM cost (tokens, $).

### Summary table

| Exp | RQ | Data | Main metric | Success criterion |
|---|---|---|---|---|
| E1 | RQ1 | A | Soundness / completeness | Soundness = 100%; completeness ≥ 95% for supported types |
| E2 | RQ2–3 | A, B | AUC of falsification-vs-cost | Ours > all non-oracle baselines; ψ-targeting > structure objective |
| E3 | RQ4 | A | False-falsification rate | ≤ α at all hallucination rates |
| E4 | RQ4 | A | Type-I error | ≤ α; naive baselines inflate |
| E5 | RQ5 | A, B | Blame accuracy | Triangulation significantly > single-witness |
| E6 | — | B, C, D3 | False falsification under extraction error | Controlled after correction |
| E7 | RQ2, RQ6 | C | G0 falsified when RCT disagrees | ≥ 3/4 cases; witnesses judged valid by experts |
| E8 | RQ6 | C (+T3) | AUC predicting RWE–RCT agreement | > E-value baseline |
| E9 | all | A–C | Ablation deltas | Each module contributes |

---

## 6. Timeline (about 9 months)

| Month | Work |
|---|---|
| 1 | PhysioNet credentialing; literature review and novelty check; ADMG toolkit; synthetic generator (A) |
| 2 | Falsifiability checker; E1; simulated LLM proposer; e-value auditor; E4 |
| 3 | Acquisition policy + baselines; E2, E3 on synthetic data |
| 4 | MIMIC-IV setup; cohorts C1–C4; target-trial protocols; masking pipeline (B) |
| 5 | LLM modules (rivals, witnesses, local note extractor); annotation guidelines; pilot D1–D3 |
| 6 | Full annotation; E5, E6; E2 on semi-synthetic data |
| 7 | E7 real case studies + eICU replication; E8 |
| 8 | E9 ablations and LLM comparison; contact OHDSI/claims partners for the T3 extension |
| 9 | Writing; release of WitnessBench (synthetic + semi-synthetic generator code; MIMIC-derived parts as code only, per DUA) |

---

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| PhysioNet approval delayed | Start week 1; build everything on synthetic data and Synthea first |
| LLM use conflicts with the DUA | Metadata-only prompts for closed models; local models for anything touching notes or rows |
| Too few exposed patients in a case study | Pre-check counts; keep C4 and eICU as backups |
| Witness constraint tests have low power at EHR sample sizes | Report power curves; prefer witness types with strong constraints (time-window negative controls, multiple proxies) |
| An RCT "anchor" is not the same estimand as the emulation | Align the target trial protocol to the RCT; report estimand differences explicitly |
| Related work appears during the project | Monthly arXiv alerts for "falsification", "negative control", "testability", "LLM causal" |
| The Duhem–Quine problem makes rejections ambiguous | Built into the design: triangulation + blame assignment (E5) |

---

## 8. Deliverables

1. **WitnessBench**: synthetic generator and instances; semi-synthetic masking pipeline; case-study protocols and SQL (data obtained through PhysioNet by each user).
2. **Open-source library** (`src/`): ADMG falsifiability checker, ψ-targeted acquisition, e-value auditor, blame assignment.
3. **Paper**: method + theory (falsifiability-gain criterion, validity guarantee) + experiments E1–E9.
4. **Audit-certificate template** that RWE studies could report alongside their effect estimates.

---

## 9. Immediate next steps (this week)

- [ ] Apply for PhysioNet credentialing (CITI course + application)
- [ ] Run a full novelty literature search and record it in `paper/related_work.md`
- [ ] Set up the repo skeleton and `.gitignore` for `data/`
- [ ] Implement the ADMG utilities and the synthetic graph generator (Component A)
- [ ] Write the first falsifiability-checker prototype for CI and IV-inequality constraints
