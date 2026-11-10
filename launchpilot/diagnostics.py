"""Source-free connection diagnostics. Never record exception messages or requests."""
import ctypes
import json
import logging
import os
import re
import socket
import ssl
import sys
import time
from datetime import datetime, timezone

from .config import ENDPOINT, MODEL

LOGGER = logging.getLogger(__name__)


def restricted_token():
    if os.name != "nt":
        return None
    from ctypes import wintypes
    try:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        advapi = ctypes.WinDLL("advapi32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        advapi.IsTokenRestricted.argtypes = [wintypes.HANDLE]
        advapi.IsTokenRestricted.restype = wintypes.BOOL
        token = wintypes.HANDLE()
        if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
            return None
        try:
            return bool(advapi.IsTokenRestricted(token))
        finally:
            kernel.CloseHandle(token)
    except (OSError, AttributeError):
        return None


def runtime_context(*, credential_loaded=None):
    def present(name):
        return bool(os.environ.get(name) or os.environ.get(name.lower()))
    return {
        "pid": os.getpid(), "interpreter": sys.executable, "endpoint": ENDPOINT, "model": MODEL,
        "credential_loaded": credential_loaded, "restricted_windows_token": restricted_token(),
        "proxy_configured": {name: present(name) for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")},
        "certificate_override_configured": {name: present(name) for name in (
            "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE")},
    }


def exception_chain(exc):
    """Keep types, OS codes and fixed classifications, not potentially sensitive free text.

    httpcore sometimes retains a socket exception only in args, or converts its
    message to a string. Inspect those too, but emit only numeric OS codes.
    """
    queue, seen, output = [(exc, "raised")], set(), []
    while queue and len(output) < 12:
        error, relation = queue.pop(0)
        if id(error) in seen:
            continue
        seen.add(id(error))
        name = type(error).__module__ + "." + type(error).__name__
        row = {"type": re.sub(r"[^A-Za-z0-9_.]", "_", name)[:160], "via": relation}
        for attr in ("errno", "winerror", "verify_code", "status_code"):
            value = getattr(error, attr, None)
            if type(value) is int:
                row[attr] = value
        categories = set()
        if isinstance(error, socket.gaierror):
            categories.add("dns")
        if isinstance(error, ssl.SSLCertVerificationError):
            categories.add("tls_certificate")
        elif isinstance(error, ssl.SSLError):
            categories.add("tls")
        if isinstance(error, (TimeoutError, socket.timeout)) or "Timeout" in type(error).__name__:
            categories.add("timeout")
        if "ProxyError" in type(error).__name__:
            categories.add("proxy")
        if type(error).__name__ in {"ConnectError", "ConnectionError", "APIConnectionError", "OpenAIConnectionError"}:
            categories.add("connection")
        # Never write these strings to the result. Extract only fixed numeric/enum information.
        codes = set()
        for argument in getattr(error, "args", ()):
            if isinstance(argument, BaseException):
                queue.append((argument, "argument"))
            elif isinstance(argument, str):
                for family, number in re.findall(r"\[(WinError|Errno)\s+(-?\d{1,6})\]", argument[:8192]):
                    codes.add((family, int(number)))
                if "CERTIFICATE_VERIFY_FAILED" in argument[:8192] or "certificate verify failed" in argument[:8192].lower():
                    categories.add("tls_certificate")
        if codes:
            row["os_codes_in_message"] = [{"family": family, "code": code} for family, code in sorted(codes)]
        os_codes = {row.get("winerror"), row.get("errno")} | {code for _, code in codes}
        if os_codes & {13, 10013}:
            categories.add("socket_permission_denied")
        if os_codes & {10060, 110}:
            categories.add("timeout")
        if os_codes & {11001, 11002, 11003, 11004}:
            categories.add("dns")
        if categories:
            row["categories"] = sorted(categories)
        output.append(row)
        if error.__cause__ is not None:
            queue.append((error.__cause__, "cause"))
        elif error.__context__ is not None:
            queue.append((error.__context__, "context"))
    return output


def failure_report(exc, *, credential_loaded=None):
    return {"exception_chain": exception_chain(exc), "runtime": runtime_context(credential_loaded=credential_loaded)}


def log_failure(store, cid, call_id, stage, report):
    """Retained with this campaign for seven days; does not alter its checkpoints or counters."""
    entry = {"at": datetime.now(timezone.utc).isoformat(), "call_id": call_id, "stage": stage, **report}
    rendered = json.dumps(entry, ensure_ascii=True)
    LOGGER.warning("Provider connection diagnostic: %s", rendered)
    try:
        with (store.path(cid) / "provider_diagnostics.jsonl").open("a", encoding="utf-8") as destination:
            destination.write(rendered + "\n")
    except OSError as exc:
        LOGGER.warning("Could not save diagnostic file: %s", json.dumps(exception_chain(exc)))


def source_free_check():
    """Unauthenticated HEAD only. No source text, API key, model call or application-state writes."""
    import httpx
    from urllib.parse import urlsplit
    result = {"runtime": runtime_context(), "method": "HEAD", "authenticated": False, "model_request": False}
    started = time.monotonic()
    host = urlsplit(ENDPOINT).hostname
    try:
        result["dns_address_count"] = len({address[4][0] for address in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
    except OSError as exc:
        result["dns_error"] = exception_chain(exc)
    try:
        with httpx.Client(timeout=8, follow_redirects=False, trust_env=True) as client:
            response = client.head(ENDPOINT + "models")
            result.update(http_reached=True, http_status=response.status_code)
    except Exception as exc:
        result.update(http_reached=False, error=failure_report(exc))
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


if __name__ == "__main__":
    print(json.dumps(source_free_check(), indent=2))
