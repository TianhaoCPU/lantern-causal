"""Run only the frozen synthetic tasks, then export offline-scoring responses."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

from .blind import export_tasks
from .llm.missingness import inspect_missingness_proposals
from .llm.provider import ProviderConfig, ProviderError, chat_completion, strict_json


_STATUSES = {"in_flight", "valid_proposal", "invalid_proposal", "invalid_json",
             "refusal", "non_stop_completion", "invalid_provider_response", "provider_error"}


def _sha256(value) -> str:
    content = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _request(config: ProviderConfig, bundle: dict, task: dict) -> dict:
    # Copy an explicit allowlist, never the evaluator, pilot output or answer key.
    visible = {"field_definitions": bundle["field_definitions"], "target": bundle["target"],
               "task_id": task["task_id"], "extraction_process": task["extraction_process"]}
    body = {"model": config.model, "messages": [
        {"role": "system", "content": bundle["instructions"]},
        {"role": "user", "content": json.dumps(visible, ensure_ascii=False, allow_nan=False)},
    ], "max_completion_tokens": config.max_completion_tokens, "stream": False, "store": False}
    if config.json_mode:
        body["response_format"] = {"type": "json_object"}
    if config.temperature is not None:
        body["temperature"] = config.temperature
    return body


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name + ".", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _submission(report: dict) -> dict:
    return {"schema_version": 1, "task_bundle_sha256": report["task_bundle_sha256"],
            "responses": [{"task_id": r["task_id"], "proposal": r["proposal"]}
                          for r in report["records"]]}


def _checkpoint(report: dict, output: Path, responses: Path | None) -> None:
    counts = {status: sum(r["status"] == status for r in report["records"])
              for status in sorted(_STATUSES)}
    report["summary"] = {"tasks": len(report["requests"]), "started": len(report["records"]),
                         "not_started": len(report["requests"]) - len(report["records"]),
                         "statuses": counts}
    report["updated_at"] = datetime.now(timezone.utc).isoformat()
    # The report is authoritative; --resume regenerates the derived envelope.
    _atomic_json(output, report)
    if responses is not None:
        _atomic_json(responses, _submission(report))


def _resume_records(previous: dict, plan: dict) -> list[dict]:
    if not isinstance(previous, dict) or any(previous.get(k) != v for k, v in plan.items()):
        raise ValueError("Resume requires the same task bundle, provider config and exact requests.")
    records = previous.get("records")
    if not isinstance(records, list) or len(records) > len(plan["requests"]):
        raise ValueError("Invalid checkpoint records.")
    for record, request in zip(records, plan["requests"]):
        if (not isinstance(record, dict) or record.get("task_id") != request["task_id"] or
            record.get("request_sha256") != request["request_sha256"] or
            not isinstance(record.get("status"), str) or record["status"] not in _STATUSES or
            "proposal" not in record):
            raise ValueError("Checkpoint records must be an ordered prefix of the frozen requests.")
        if record["status"] == "valid_proposal":
            visible = json.loads(request["request"]["messages"][1]["content"])
            inspect_missingness_proposals(record["proposal"], visible["extraction_process"])
    return records


def _safe_text(value, secret: str):
    return value.replace(secret, "[REDACTED]") if isinstance(value, str) else None


def _decode_reply(reply: dict, evidence: str, secret: str) -> dict:
    body = reply.get("body") if isinstance(reply, dict) else None
    if not isinstance(body, dict):
        return {"status": "invalid_provider_response", "proposal": None}
    record = {"status": "invalid_provider_response", "proposal": None,
              "request_id": _safe_text(reply.get("request_id"), secret),
              "response_id": _safe_text(body.get("id"), secret),
              "returned_model": _safe_text(body.get("model"), secret),
              "system_fingerprint": _safe_text(body.get("system_fingerprint"), secret)}
    usage = body.get("usage")
    if isinstance(usage, dict):
        record["usage"] = {k: usage[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")
                           if type(usage.get(k)) is int and usage[k] >= 0}
    choices = body.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        return record
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        return record
    content = _safe_text(message.get("content"), secret)
    record.update({"raw_content": content, "finish_reason": _safe_text(choice.get("finish_reason"), secret),
                   "refusal": _safe_text(message.get("refusal"), secret)})
    if record["refusal"]:
        return {**record, "status": "refusal"}
    if choice.get("finish_reason") != "stop":
        return {**record, "status": "non_stop_completion"}
    if content is None:
        return record
    try:
        proposal = strict_json(content)
    except (ValueError, RecursionError):
        return {**record, "status": "invalid_json"}
    try:
        inspect_missingness_proposals(proposal, evidence)
    except ValueError:
        return {**record, "status": "invalid_proposal", "proposal": proposal}
    return {**record, "status": "valid_proposal", "proposal": proposal}


def run_inference(payload: dict, *, output: Path, responses: Path | None = None,
                  dry_run: bool = False, resume: bool = False) -> dict:
    """Save requests before calls and each attempt before moving to the next task.

    A resumed run skips every started task, including failures and in-flight
    calls whose delivery is unknown. Repeating them requires a new run path.
    """
    config = ProviderConfig.from_dict(payload)
    output = Path(output).resolve()
    responses = Path(responses).resolve() if responses is not None else None
    if responses == output:
        raise ValueError("Run report and response envelope must use different files.")
    if dry_run and (resume or responses is not None):
        raise ValueError("--dry-run uses only --output; omit --resume and --responses.")
    if not dry_run and responses is None:
        raise ValueError("A live run requires --responses for the offline-scoring envelope.")
    if not resume and (output.exists() or (responses is not None and responses.exists())):
        raise ValueError("Output already exists; choose new paths or use --resume for a live checkpoint.")
    bundle = export_tasks()
    requests = [{"task_id": task["task_id"], "request": _request(config, bundle, task)}
                for task in bundle["tasks"]]
    for request in requests:
        request["request_sha256"] = _sha256(request["request"])
    plan = {"schema_version": 1, "experiment": "synthetic_process_inference", "dry_run": dry_run,
            "patient_data_used": False, "protocol": "openai_chat_completions",
            "task_bundle_sha256": bundle["task_bundle_sha256"], "provider_config": config.public_dict(),
            "requests": requests,
            "run_sha256": _sha256({"provider": config.public_dict(), "requests": requests})}
    previous = strict_json(output.read_text(encoding="utf-8")) if resume else None
    records = _resume_records(previous, plan) if resume else []
    report = {**plan, "created_at": previous["created_at"] if resume else datetime.now(timezone.utc).isoformat(),
              "records": records}
    api_key = None
    if not dry_run and len(records) < len(requests):
        if config.model == "replace-with-a-pinned-model-id":
            raise ValueError("Set model to your chosen model ID before a live run.")
        api_key = os.environ.get(config.api_key_env)
        if (not api_key or not api_key.strip() or
            any(c.isspace() or ord(c) < 32 or ord(c) > 126 for c in api_key)):
            raise ValueError(f"Set a nonempty API token in environment variable {config.api_key_env}.")
    _checkpoint(report, output, responses)
    if dry_run:
        return report
    for task, request in zip(bundle["tasks"][len(records):], requests[len(records):]):
        record = {"task_id": task["task_id"], "request_sha256": request["request_sha256"],
                  "status": "in_flight", "proposal": None}
        records.append(record)
        _checkpoint(report, output, responses)
        try:
            reply = chat_completion(config, request["request"], api_key)
            record.update(_decode_reply(reply, task["extraction_process"], api_key))
        except ProviderError as exc:
            record.update({"status": "provider_error", "error_code": exc.code, "http_status": exc.http_status})
        _checkpoint(report, output, responses)
    return report
