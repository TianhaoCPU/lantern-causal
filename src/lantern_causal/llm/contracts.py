"""Validate cited latent-mechanism proposals without treating them as verified."""


def validate_proposals(payload: dict, evidence: str, limit: int = 3) -> dict:
    """Check candidate limits, graph syntax and literal evidence quotations."""
    if payload.get("status") not in ("candidates", "insufficient_information"):
        raise ValueError("Proposal status must describe candidates or insufficient information.")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or len(candidates) > limit:
        raise ValueError("Expected a candidate list within the declared budget.")
    if payload["status"] == "candidates" and not candidates:
        raise ValueError("A candidates response needs at least one candidate.")
    seen = set()
    for candidate in candidates:
        identifier = candidate.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValueError("Candidate IDs must be nonempty and unique.")
        seen.add(identifier)
        if not isinstance(candidate.get("role"), str) or not candidate["role"].strip():
            raise ValueError("Each candidate must state its proposed role.")
        nodes = candidate.get("nodes")
        if (not isinstance(nodes, list) or not nodes or
            any(not isinstance(n, str) or not n for n in nodes) or len(set(nodes)) != len(nodes)):
            raise ValueError("Candidate nodes must be unique nonempty strings.")
        edges = candidate.get("edges")
        if not isinstance(edges, list):
            raise ValueError("Candidate edges must be a list.")
        parents = {n: set() for n in nodes}
        for edge in edges:
            if (not isinstance(edge, list) or len(edge) != 2 or
                any(n not in parents for n in edge)):
                raise ValueError("Each edge must reference two declared nodes.")
            parents[edge[1]].add(edge[0])
        remaining = set(nodes)
        while remaining:
            ready = {n for n in remaining if not (parents[n] & remaining)}
            if not ready:
                raise ValueError("Candidate graph must be acyclic.")
            remaining -= ready
        quotes = candidate.get("evidence_quotes")
        if (not isinstance(quotes, list) or not quotes or
            any(not isinstance(q, str) or not q or q not in evidence for q in quotes)):
            raise ValueError("Every evidence quote must occur literally in the allowed input.")
    return payload
