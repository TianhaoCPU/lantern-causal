"""Exercise synthetic-only requests, failure accounting and interrupted calls."""

from contextlib import contextmanager
from copy import deepcopy
from http.client import IncompleteRead
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.error import URLError

from lantern_causal.blind import export_tasks, run_blind_evaluation
from lantern_causal.inference import run_inference
from lantern_causal.llm.missingness import rule_proposal
from lantern_causal.llm.provider import ProviderConfig, ProviderError, chat_completion, strict_json


_TOKEN = "synthetic-test-token-not-a-real-key"
_CONFIG = {"schema_version": 1, "base_url": "https://example.test/v1", "model": "fixture-model",
           "api_key_env": "LANTERN_TEST_KEY"}


def _reply(content, *, finish="stop", refusal=None):
    return {"request_id": "fixture-request", "body": {
        "id": "fixture-response", "model": "fixture-model-revision", "system_fingerprint": "fixture-fp",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        "choices": [{"finish_reason": finish, "message": {"content": content, "refusal": refusal}}],
    }}


def _rule_reply(config, body, token):
    visible = json.loads(body["messages"][1]["content"])
    return _reply(json.dumps(rule_proposal(visible["extraction_process"])))


@contextmanager
def _server():
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.append({"path": self.path, "authorization": self.headers.get("Authorization"), "body": body})
            if self.path.startswith("/redirect/"):
                self.send_response(302)
                self.send_header("Location", "/redirect-target")
                self.end_headers()
                return
            if self.path.startswith("/error/"):
                self.send_response(429)
                self.end_headers()
                self.wfile.write(_TOKEN.encode())
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("x-request-id", "local-request")
            self.end_headers()
            if self.path.startswith("/malformed/"):
                self.wfile.write(b'{"duplicate": 1, "duplicate": 2}')
            else:
                self.wfile.write(json.dumps(_rule_reply(None, body, None)["body"]).encode())

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}", received
        finally:
            server.shutdown()
            worker.join(timeout=5)


class ProviderTests(unittest.TestCase):
    def test_config_rejects_unknown_fields_credentials_and_invalid_values(self):
        self.assertEqual(ProviderConfig.from_dict(_CONFIG).endpoint, "https://example.test/v1/chat/completions")
        for field, value in (
            ("schema_version", True), ("api_key", _TOKEN), ("model", ""),
            ("base_url", "http://example.test/v1"), ("base_url", "https://user:pass@example.test/v1"),
            ("base_url", "https://example.test/v1?token=secret"), ("base_url", "https://example.test/#fragment"),
            ("base_url", "https://example.test:invalid/v1"), ("base_url", "https://example.test/\n"),
            ("api_key_env", "TOKEN=secret"), ("timeout_seconds", 0), ("timeout_seconds", float("inf")),
            ("timeout_seconds", True), ("max_completion_tokens", False), ("json_mode", "true"),
            ("temperature", float("nan")), ("temperature", -1), ("temperature", True),
        ):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                ProviderConfig.from_dict({**_CONFIG, field: value})
        for bad in (None, [], {}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ProviderConfig.from_dict(bad)

    def test_json_parser_does_not_repair_duplicates_or_nonfinite_numbers(self):
        for text in ('{"status": "candidates", "status": "insufficient_information"}',
                     '{"score": NaN}', '{"score": Infinity}', '{"score": 1e999}', '```json\n{}\n```'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                strict_json(text)

    def test_transport_blocks_redirects_and_sanitizes_errors(self):
        body = {"messages": [{"content": "unused"}, {"content": "{}"}]}
        with _server() as (url, received):
            for route, code, status in (("redirect", "http_error", 302), ("error", "http_error", 429),
                                         ("malformed", "invalid_provider_json", None)):
                config = ProviderConfig.from_dict({**_CONFIG, "base_url": url + "/" + route})
                with self.subTest(route=route), self.assertRaises(ProviderError) as caught:
                    chat_completion(config, body, _TOKEN)
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(caught.exception.http_status, status)
                self.assertNotIn(_TOKEN, str(caught.exception))
            self.assertEqual(len(received), 3)
            self.assertFalse(any(r["path"] == "/redirect-target" for r in received))
        for failure in (URLError(_TOKEN), TimeoutError(_TOKEN), IncompleteRead(b"truncated response")):
            with patch("lantern_causal.llm.provider.build_opener") as opener:
                opener.return_value.open.side_effect = failure
                with self.assertRaises(ProviderError) as caught:
                    chat_completion(ProviderConfig.from_dict(_CONFIG), body, _TOKEN)
                self.assertEqual(str(caught.exception), "connection_error")

    def test_transport_bounds_response_size(self):
        body = {"messages": [{"content": "unused"}, {"content": "{}"}]}
        with _server() as (url, _), patch("lantern_causal.llm.provider.MAX_RESPONSE_BYTES", 5):
            config = ProviderConfig.from_dict({**_CONFIG, "base_url": url + "/malformed"})
            with self.assertRaises(ProviderError) as caught:
                chat_completion(config, body, _TOKEN)
            self.assertEqual(caught.exception.code, "response_too_large")


class InferenceTests(unittest.TestCase):
    def test_dry_run_allowlist_never_reads_key_or_calls_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "requests.json"
            with patch("lantern_causal.inference.os.environ") as environment, \
                 patch("lantern_causal.inference.chat_completion") as call:
                report = run_inference(_CONFIG, output=output, dry_run=True)
                environment.get.assert_not_called()
                call.assert_not_called()
            self.assertEqual(report, json.loads(output.read_text()))
            self.assertEqual(report["summary"]["not_started"], 9)
            self.assertTrue(report["dry_run"])
            self.assertFalse(report["patient_data_used"])
            bundle = export_tasks()
            self.assertEqual(report["task_bundle_sha256"], bundle["task_bundle_sha256"])
            for request, task in zip(report["requests"], bundle["tasks"]):
                body = request["request"]
                visible = json.loads(body["messages"][1]["content"])
                self.assertEqual(set(visible), {"field_definitions", "target", "task_id", "extraction_process"})
                self.assertEqual(visible["extraction_process"], task["extraction_process"])
                self.assertEqual(body["messages"][0]["content"], bundle["instructions"])
                self.assertEqual(body["response_format"], {"type": "json_object"})
                self.assertNotIn("temperature", body)
                self.assertFalse(body["store"])
                self.assertFalse(body["stream"])
            text = output.read_text()
            for forbidden in ("reference_rd", "expected_families", "39/400", "0.0975", "seed", _TOKEN):
                self.assertNotIn(forbidden, text)

    def test_attempts_are_not_repaired_and_all_failures_remain_in_denominators(self):
        attempts = []

        def transport(config, body, token):
            self.assertEqual(token, _TOKEN)
            index = len(attempts)
            attempts.append(body)
            if index in (0, 7):
                return _rule_reply(config, body, token)
            if index == 1:
                return _reply("```json\n{}\n```")
            if index == 2:
                return _reply("{}")
            if index == 3:
                return _reply(_rule_reply(config, body, token)["body"]["choices"][0]["message"]["content"], finish="length")
            if index == 4:
                return _reply(None, refusal="fixture refusal")
            if index == 5:
                return {"body": {"choices": []}}
            if index == 6:
                raise ProviderError("http_error", 429)
            reply = _reply(json.dumps({"echo": token}))
            reply["request_id"] = token
            reply["body"]["model"] = token
            return reply

        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"LANTERN_TEST_KEY": _TOKEN}), \
             patch("lantern_causal.inference.chat_completion", side_effect=transport):
            output, responses = Path(temp) / "run.json", Path(temp) / "responses.json"
            report = run_inference(_CONFIG, output=output, responses=responses)
            self.assertEqual(len(attempts), 9)
            self.assertEqual([r["request"] for r in report["requests"]], attempts)
            self.assertEqual(report["summary"]["not_started"], 0)
            self.assertEqual(report["summary"]["statuses"]["valid_proposal"], 2)
            self.assertEqual(report["summary"]["statuses"]["invalid_proposal"], 2)
            for name in ("invalid_json", "non_stop_completion", "refusal", "invalid_provider_response", "provider_error"):
                self.assertEqual(report["summary"]["statuses"][name], 1)
            self.assertIsNone(report["records"][3]["proposal"])
            self.assertEqual(report["records"][6]["http_status"], 429)
            for path in (output, responses):
                self.assertNotIn(_TOKEN, path.read_text())
            submitted = json.loads(responses.read_text())
            self.assertEqual(set(submitted), {"schema_version", "task_bundle_sha256", "responses"})
            scores = run_blind_evaluation({"schema_version": 1, "seeds": [1]}, submitted)
            text = scores["summary"]["submitted"]["text"]
            self.assertEqual((text["tasks"], text["valid"], text["invalid"], text["missing"]), (9, 2, 7, 0))

    def test_resume_skips_started_calls_including_unknown_delivery(self):
        attempts = []

        def interrupt(config, body, token):
            attempts.append(body)
            if len(attempts) == 2:
                raise KeyboardInterrupt
            return _rule_reply(config, body, token)

        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"LANTERN_TEST_KEY": _TOKEN}):
            output, responses = Path(temp) / "run.json", Path(temp) / "responses.json"
            with patch("lantern_causal.inference.chat_completion", side_effect=interrupt), self.assertRaises(KeyboardInterrupt):
                run_inference(_CONFIG, output=output, responses=responses)
            partial = json.loads(output.read_text())
            self.assertEqual([r["status"] for r in partial["records"]], ["valid_proposal", "in_flight"])
            responses.unlink()  # Recover even if only the authoritative report survived.
            with patch("lantern_causal.inference.chat_completion", side_effect=_rule_reply) as call:
                report = run_inference(_CONFIG, output=output, responses=responses, resume=True)
                self.assertEqual(call.call_count, 7)
                self.assertEqual([c.args[1] for c in call.call_args_list],
                                 [r["request"] for r in partial["requests"][2:]])
            self.assertEqual(report["summary"]["statuses"]["valid_proposal"], 8)
            self.assertEqual(report["summary"]["statuses"]["in_flight"], 1)
            self.assertEqual(len(json.loads(responses.read_text())["responses"]), 9)
            with patch.dict(os.environ, {}, clear=True), patch("lantern_causal.inference.chat_completion") as call:
                run_inference(_CONFIG, output=output, responses=responses, resume=True)
                call.assert_not_called()

    def test_resume_rejects_configuration_or_request_changes_before_calls(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"LANTERN_TEST_KEY": _TOKEN}), \
             patch("lantern_causal.inference.chat_completion", side_effect=_rule_reply) as call:
            output, responses = Path(temp) / "run.json", Path(temp) / "responses.json"
            report = run_inference(_CONFIG, output=output, responses=responses)
            call.reset_mock()
            with self.assertRaises(ValueError):
                run_inference({**_CONFIG, "model": "changed"}, output=output, responses=responses, resume=True)
            for mutate in (
                lambda r: r["requests"][0]["request"].update({"model": "changed"}),
                lambda r: r["records"][0].update({"task_id": "unknown"}),
                lambda r: r["records"][0].update({"status": []}),
            ):
                changed = deepcopy(report)
                mutate(changed)
                output.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    run_inference(_CONFIG, output=output, responses=responses, resume=True)
            call.assert_not_called()

    def test_preflight_missing_key_path_collisions_and_overwrites_make_no_calls(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {}, clear=True), \
             patch("lantern_causal.inference.chat_completion") as call:
            output, responses = Path(temp) / "run.json", Path(temp) / "responses.json"
            for kwargs in ({"output": output}, {"output": output, "responses": output},
                           {"output": output, "responses": responses},
                           {"output": output, "responses": responses, "dry_run": True},
                           {"output": output, "dry_run": True, "resume": True}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    run_inference(_CONFIG, **kwargs)
            self.assertFalse(output.exists())
            output.write_text("preserve this file")
            with self.assertRaises(ValueError):
                run_inference(_CONFIG, output=output, dry_run=True)
            self.assertEqual(output.read_text(), "preserve this file")
            call.assert_not_called()

    def test_optional_json_mode_and_temperature_are_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            report = run_inference({**_CONFIG, "json_mode": False, "temperature": 0},
                                   output=Path(temp) / "run.json", dry_run=True)
            self.assertNotIn("response_format", report["requests"][0]["request"])
            self.assertEqual(report["requests"][0]["request"]["temperature"], 0)

    def test_cli_live_calls_and_resume_use_local_server_outside_repository(self):
        with tempfile.TemporaryDirectory() as temp, _server() as (url, received):
            root = Path(temp)
            config, output, responses = [root / n for n in ("config.json", "run.json", "responses.json")]
            config.write_text(json.dumps({**_CONFIG, "base_url": url + "/v1"}))
            command = [sys.executable, "-m", "lantern_causal", "blind-infer", "--provider-config", str(config),
                       "--output", str(output), "--responses", str(responses)]
            environment = {**os.environ, "LANTERN_TEST_KEY": _TOKEN}
            process = subprocess.run(command, cwd=temp, env=environment, text=True, capture_output=True, timeout=30)
            self.assertEqual(process.returncode, 0, process.stderr)
            report = json.loads(process.stdout)
            self.assertEqual(report, json.loads(output.read_text()))
            self.assertEqual(report["summary"]["statuses"]["valid_proposal"], 9)
            self.assertEqual(report["records"][0]["request_id"], "local-request")
            self.assertEqual(report["records"][0]["usage"]["total_tokens"], 30)
            self.assertEqual(len(received), 9)
            self.assertTrue(all(r["path"] == "/v1/chat/completions" for r in received))
            self.assertTrue(all(r["authorization"] == "Bearer " + _TOKEN for r in received))
            self.assertNotIn(_TOKEN, process.stdout + process.stderr)
            score = run_blind_evaluation({"schema_version": 1, "seeds": [1]}, json.loads(responses.read_text()))
            self.assertEqual(score["summary"]["submitted"]["text"]["exact_candidate_sets"], 9)
            process = subprocess.run(command + ["--resume"], cwd=temp, env=environment,
                                     text=True, capture_output=True, timeout=30)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(len(received), 9)
            process = subprocess.run(command[:-2] + ["--responses", str(config)], cwd=temp, env=environment,
                                     text=True, capture_output=True, timeout=30)
            self.assertEqual(process.returncode, 2)
            self.assertNotIn("Traceback", process.stderr)


if __name__ == "__main__":
    unittest.main()
