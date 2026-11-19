# Synthetic missingness process task

Use the supplied field definitions, target and extraction process. Propose the
recording graphs supported by the process text. The study's fixed graph family
has nodes C, X, Y, R and required edges C->X, C->Y, X->Y, C->R. The only optional
edges are X->R and Y->R; at least one must be present. C,X,Y form a saturated
factorization scaffold, not a claim that changing the lab group causes death.
R describes retrospective extraction after outcome adjudication. A missing
optional edge asserts absence of that dependency, not merely lack of mention.
In this synthetic family C always affects retention, every supplied X/Y input
affects retention, and the sampler's random noise is independent of C,X,Y.

Return a JSON object with status "candidates" or "insufficient_information" and
a "candidates" list of at most three graphs. Each graph has a unique "id", a
nonempty "role", "nodes", "edges" as source/target string pairs, and nonempty
"evidence_quotes" copied literally from this task's extraction_process only.
Keep all supported alternatives if the text leaves a dependency unresolved;
use "insufficient_information" in that case. Do not invent nodes or return a
point estimate. The statistical program chooses formulas after checking graphs.
