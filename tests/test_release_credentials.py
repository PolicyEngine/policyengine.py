"""Credential verification fails closed without exposing account or token data."""

import importlib.util
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "release_credentials", ROOT / "scripts/check_release_credentials.py"
)
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)


@pytest.mark.parametrize("role", ["read", "write", "fineGrained", "admin", "", None])
def test_requires_authenticated_read_role(monkeypatch, capsys, role):
    token = "fixture-secret-must-not-appear"
    monkeypatch.setenv("HUGGING_FACE_TOKEN", token)
    response = requests.Response()
    response.status_code = 200
    payload = {
        "name": "fixture-private-account",
        "auth": {"type": "access_token", "accessToken": {"role": role}},
    }

    def whoami(url, **kwargs):
        assert url == "https://huggingface.co/api/whoami-v2"
        assert kwargs["headers"] == {"Authorization": f"Bearer {token}"}
        assert kwargs["allow_redirects"] is False
        assert kwargs["timeout"] == 30
        response.json = lambda: payload
        return response

    monkeypatch.setattr(credentials.requests, "get", whoami)
    assert credentials.main() == (0 if role == "read" else 1)
    output = capsys.readouterr()
    assert token not in output.out + output.err
    assert payload["name"] not in output.out + output.err


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"auth": None},
        {"auth": {"type": "oauth", "accessToken": {"role": "read"}}},
        {"auth": {"type": "access_token"}},
        [],
    ],
)
def test_missing_or_unknown_auth_metadata_is_rejected(monkeypatch, payload):
    response = requests.Response()
    response.status_code = 200
    response.json = lambda: payload
    monkeypatch.setattr(credentials.requests, "get", lambda *a, **kw: response)
    with pytest.raises(ValueError, match="role read"):
        credentials.check_read_only_token("fixture-token")


@pytest.mark.parametrize("failure", ["timeout", "invalid-json", 301, 401, 403, 503])
def test_fetch_failures_never_log_sensitive_response(monkeypatch, capsys, failure):
    secret = "fixture-sensitive-detail"
    monkeypatch.setenv("HUGGING_FACE_TOKEN", secret)

    def fetch(*args, **kwargs):
        if failure == "timeout":
            raise requests.Timeout(secret)
        response = requests.Response()
        response.status_code = failure if isinstance(failure, int) else 200
        response._content = secret.encode()
        return response

    monkeypatch.setattr(credentials.requests, "get", fetch)
    assert credentials.main() == 1
    output = capsys.readouterr()
    assert secret not in output.out + output.err


@pytest.mark.parametrize("token", [None, "", "  "])
def test_absent_credentials_fail_before_network(monkeypatch, token):
    def unexpected(*args, **kwargs):
        pytest.fail("No request may be sent without a credential")

    monkeypatch.setattr(credentials.requests, "get", unexpected)
    with pytest.raises(ValueError, match="requires HUGGING_FACE_TOKEN"):
        credentials.check_read_only_token(token)
