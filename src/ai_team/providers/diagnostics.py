"""Allowlisted diagnostics only: never serialize exception text, data or headers."""
import asyncio
from .base import ProviderError

CODES = {"SDK_ERROR", "CONNECTION_ERROR", "SDK_PROTOCOL_ERROR", "SDK_RPC_ERROR",
         "TIMEOUT", "CANCELLED", "PROVIDER_ERROR", "UNKNOWN_ERROR", "MODEL_MAX_TOKENS",
         "MODEL_TURN_FAILED", "SESSION_MISMATCH", "INVALID_MODEL_JSON",
         "INVALID_MODEL_CONTENT", "INVALID_MODEL_DECISION", "MISSING_FINAL_TEXT"}
SDK_TYPES = {"TransportClosedError": "CONNECTION_ERROR", "SdkProtocolError": "SDK_PROTOCOL_ERROR",
             "JsonRpcError": "SDK_RPC_ERROR"}
FINISH_REASONS = {"completed", "max-tokens", "error", "cancelled", "interrupted"}


def sanitize(value):
    code = value.get("code")
    result = {"code": code if isinstance(code, str) and code in CODES else "UNKNOWN_ERROR"}
    for key in ("input_chars", "input_bytes", "response_chars", "output_tokens"):
        number = value.get(key)
        if type(number) is int and 0 <= number <= 100_000_000:
            result[key] = number
    if isinstance(value.get("finish_reason"), str) and value["finish_reason"] in FINISH_REASONS:
        result["finish_reason"] = value["finish_reason"]
    for key, low, high in (("rpc_code", -32768, 32767), ("http_status", 100, 599)):
        number = value.get(key)
        if type(number) is int and low <= number <= high:
            result[key] = number
    known = set(SDK_TYPES) | {"TimeoutError", "CancelledError", "ConnectionError", "ProviderError", "OTHER"}
    if isinstance(value.get("source_type"), str) and value["source_type"] in known:
        result["source_type"] = value["source_type"]
    if isinstance(value.get("cause_types"), list):
        result["cause_types"] = [t if isinstance(t, str) and t in known else "OTHER" for t in value["cause_types"][:4]]
    return result


class ClassifiedProviderError(ProviderError):
    def __init__(self, message, code, **metadata):
        super().__init__(message)
        self.diagnostic = sanitize({**metadata, "code": code})


def error_diagnostic(exc):
    if isinstance(exc, ClassifiedProviderError):
        return sanitize(exc.diagnostic)
    if isinstance(exc, TimeoutError):
        code, source = "TIMEOUT", "TimeoutError"
    elif isinstance(exc, asyncio.CancelledError):
        code, source = "CANCELLED", "CancelledError"
    elif isinstance(exc, ConnectionError):
        code, source = "CONNECTION_ERROR", "ConnectionError"
    elif type(exc).__module__ == "deepseek_harness.errors" and type(exc).__name__ in SDK_TYPES:
        source = type(exc).__name__
        code = SDK_TYPES[source]
    elif isinstance(exc, ProviderError):
        code, source = "PROVIDER_ERROR", "ProviderError"
    else:
        code, source = "UNKNOWN_ERROR", "OTHER"
    data = {"code": code, "source_type": source}
    if source == "JsonRpcError":
        data["rpc_code"] = getattr(exc, "code", None)
    # Only explicitly typed numeric status; never inspect response bodies/headers.
    data["http_status"] = getattr(exc, "status_code", None)
    causes, seen = [], {id(exc)}
    parent = exc.__cause__ or exc.__context__
    while parent is not None and id(parent) not in seen and len(causes) < 4:
        seen.add(id(parent))
        name = type(parent).__name__
        causes.append(name if name in SDK_TYPES or isinstance(parent, (TimeoutError, ConnectionError)) else "OTHER")
        parent = parent.__cause__ or parent.__context__
    if causes:
        data["cause_types"] = causes
    return sanitize(data)
