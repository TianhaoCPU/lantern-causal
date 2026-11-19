# LANTERN-Causal candidate proposal contract

Read only the supplied field definitions, time ordering and extraction process.
Propose up to three latent-mechanism candidates that could change the stated
target's recoverability. Cite literal input passages. Keep alternative mechanisms
when the evidence cannot distinguish them. Do not infer truth from a graph passing
a finite compatibility test or name a hidden clinical field without evidence.

Return JSON with status "candidates" or "insufficient_information" and a
"candidates" list. Each candidate contains "id", "role", "nodes", "edges"
(two-element source/target lists) and "evidence_quotes". All graph statements
remain proposals until independently checked. This contract is implemented;
provider execution and clinical evaluation are pending.
