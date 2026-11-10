import io
import json
import socket
import ssl

import httpcore
import httpx
import openai
import pytest

from launchpilot.diagnostics import exception_chain, failure_report, log_failure, source_free_check


def test_chained_socket_error_retains_codes_without_secrets_or_source(monkeypatch):
    secret = "private-credential-do-not-log"
    source = "private-source-do-not-log"
    monkeypatch.setenv("HTTPS_PROXY", f"http://user:{secret}@proxy.example:8080")
    monkeypatch.setenv("SSL_CERT_FILE", f"C:/{secret}/certificate.pem")
    root = PermissionError(13, f"[WinError 10013] denied {secret} {source}")
    root.winerror = 10013
    core = httpcore.ConnectError(root)
    transport = httpx.ConnectError(f"[WinError 10013] {secret}")
    transport.__cause__ = core
    request = httpx.Request("POST", "https://api.tokenfactory.nebius.com/v1/chat/completions",
                           headers={"Authorization": f"Bearer {secret}"}, content=source)
    wrapper = openai.APIConnectionError(request=request)
    wrapper.__cause__ = transport
    report = failure_report(wrapper, credential_loaded=True)
    rendered = json.dumps(report)
    assert secret not in rendered and source not in rendered and "Authorization" not in rendered
    assert any(row.get("winerror") == 10013 for row in report["exception_chain"])
    assert any("socket_permission_denied" in row.get("categories", []) for row in report["exception_chain"])
    assert report["runtime"]["proxy_configured"]["HTTPS_PROXY"] is True
    assert report["runtime"]["credential_loaded"] is True


@pytest.mark.parametrize("exc,category", [
    (socket.gaierror(11001, "private DNS details"), "dns"),
    (ssl.SSLCertVerificationError(1, "CERTIFICATE_VERIFY_FAILED private certificate"), "tls_certificate"),
    (httpx.ProxyError("http://user:private@proxy.example"), "proxy"),
    (httpx.ReadTimeout("private request body"), "timeout"),
])
def test_dns_tls_proxy_timeout_are_classified_without_raw_messages(exc, category):
    result = exception_chain(exc)
    assert category in result[0]["categories"]
    assert "private" not in json.dumps(result)


def test_worker_serializes_safe_exception_chain_without_request(monkeypatch, capsys):
    from launchpilot import worker
    private = "source-and-api-key-must-not-appear"
    payload = {"api_key": private, "messages": [], "tools": [], "json_mode": False, "max_tokens": 1, "timeout": 1}
    root = httpx.ConnectError(f"[WinError 10013] {private}")
    error = openai.APIConnectionError(request=httpx.Request("POST", "https://example.org", content=private))
    error.__cause__ = root
    class Model:
        def invoke(self, *args, **kwargs):
            raise error
    monkeypatch.setattr(worker, "make_model", lambda request: Model())
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    worker.main()
    result_text = capsys.readouterr().out
    assert private not in result_text
    result = json.loads(result_text)
    assert result["ok"] is False and result["transient"] is True
    assert result["diagnostics"]["exception_chain"][1]["os_codes_in_message"] == [{"family": "WinError", "code": 10013}]


def test_diagnostic_log_is_local_jsonl_not_a_campaign_mutation(tmp_path):
    class ExistingStore:
        def path(self, cid):
            assert cid == "existing-campaign"
            return tmp_path
    report = failure_report(socket.gaierror(11001, "do not log this message"))
    log_failure(ExistingStore(), "existing-campaign", 4, "research", report)
    text = (tmp_path / "provider_diagnostics.jsonl").read_text(encoding="utf-8")
    assert "do not log this message" not in text
    result = json.loads(text)
    assert result["call_id"] == 4 and result["stage"] == "research"
    assert result["exception_chain"][0]["errno"] == 11001
    assert len(list(tmp_path.iterdir())) == 1


def test_connectivity_probe_only_sends_unauthenticated_head(monkeypatch):
    requests = []
    def handler(request):
        requests.append(request)
        assert request.method == "HEAD" and not request.content
        assert "Authorization" not in request.headers
        return httpx.Response(405)
    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", ("127.0.0.1", 443))])
    result = source_free_check()
    assert result["http_reached"] and result["http_status"] == 405
    assert result["authenticated"] is False and result["model_request"] is False
    assert len(requests) == 1 and str(requests[0].url) == "https://api.tokenfactory.nebius.com/v1/models"
