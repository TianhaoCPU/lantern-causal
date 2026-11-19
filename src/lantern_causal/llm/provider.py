"""Small standard-library transport for explicit Chat Completions requests."""

from dataclasses import asdict, dataclass
from http.client import HTTPException
import ipaddress
import json
import math
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


MAX_RESPONSE_BYTES = 2_000_000


def strict_json(text: str):
    """Reject duplicate keys and non-finite values rather than repairing JSON."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("JSON object keys must be unique.")
            result[key] = value
        return result

    def constant(_):
        raise ValueError("JSON numbers must be finite.")

    result = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    # A numeric literal such as 1e999 also becomes non-finite in json.loads.
    json.dumps(result, allow_nan=False)
    return result


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str
    model: str
    api_key_env: str = "OPENAI_API_KEY"
    timeout_seconds: float = 60
    max_completion_tokens: int = 2048
    json_mode: bool = True
    temperature: float | None = None

    @classmethod
    def from_dict(cls, payload: dict):
        allowed = {"schema_version", *cls.__dataclass_fields__}
        if (not isinstance(payload, dict) or set(payload) - allowed or
            type(payload.get("schema_version")) is not int or payload["schema_version"] != 1):
            raise ValueError("Provider config needs schema_version=1 and only documented fields.")
        for name in ("base_url", "model"):
            if not isinstance(payload.get(name), str) or not payload[name].strip():
                raise ValueError(f"Provider config needs a nonempty {name}.")
        config = cls(**{k: v for k, v in payload.items() if k != "schema_version"})
        url = urlsplit(config.base_url)
        if (url.scheme not in ("https", "http") or not url.hostname or url.username is not None or
            url.password is not None or url.query or url.fragment or
            any(c.isspace() or ord(c) < 32 for c in config.base_url)):
            raise ValueError("base_url must be an HTTP(S) URL without credentials, queries or fragments.")
        url.port  # Validate the port even when the hostname is not an IP address.
        try:
            loopback = url.hostname == "localhost" or ipaddress.ip_address(url.hostname).is_loopback
        except ValueError:
            loopback = url.hostname == "localhost"
        if url.scheme == "http" and not loopback:
            raise ValueError("Use HTTPS for hosted endpoints; HTTP is allowed only for loopback servers.")
        if (not isinstance(config.api_key_env, str) or
            not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", config.api_key_env)):
            raise ValueError("api_key_env must name an environment variable.")
        if (type(config.timeout_seconds) not in (int, float) or
            not math.isfinite(config.timeout_seconds) or not 0 < config.timeout_seconds <= 300):
            raise ValueError("timeout_seconds must be finite and in (0, 300].")
        if type(config.max_completion_tokens) is not int or config.max_completion_tokens < 1:
            raise ValueError("max_completion_tokens must be a positive integer.")
        if type(config.json_mode) is not bool:
            raise ValueError("json_mode must be a boolean.")
        if config.temperature is not None and (
            type(config.temperature) not in (int, float) or not math.isfinite(config.temperature) or
            not 0 <= config.temperature <= 2
        ):
            raise ValueError("temperature must be null or a finite number in [0, 2].")
        return config

    @property
    def endpoint(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"

    def public_dict(self) -> dict:
        return {"schema_version": 1, **asdict(self)}


class ProviderError(Exception):
    """A fixed error code; provider bodies and exception text may echo secrets."""

    def __init__(self, code: str, http_status: int | None = None):
        super().__init__(code)
        self.code = code
        self.http_status = http_status


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def chat_completion(config: ProviderConfig, body: dict, api_key: str) -> dict:
    """Make one bounded, non-streaming call without redirects or retries."""
    request = Request(
        config.endpoint, data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with build_opener(_NoRedirect()).open(request, timeout=config.timeout_seconds) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ProviderError("response_too_large")
            try:
                body = strict_json(raw.decode("utf-8"))
            except (UnicodeError, ValueError, RecursionError):
                raise ProviderError("invalid_provider_json") from None
            if not isinstance(body, dict):
                raise ProviderError("invalid_provider_json")
            return {"body": body, "request_id": response.headers.get("x-request-id")}
    except HTTPError as exc:
        status = exc.code
        exc.close()
        raise ProviderError("http_error", status) from None
    except (URLError, OSError, HTTPException):
        raise ProviderError("connection_error") from None
