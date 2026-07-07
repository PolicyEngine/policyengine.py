"""Zenodo mirroring of certified releases.

Hugging Face hosts the primary artifacts but publishes no preservation
commitment — its DOIs are deletable short URLs. These tests pin the
mirroring flow that deposits the certification record (bundle manifest,
bundle TRO, data release manifest, and optionally the dataset itself)
on Zenodo, which does publish one, and returns ``PreservationMirror``
entries with real DOIs.

License safety is load-bearing: a dataset file is only ever deposited
when its source Hugging Face repo is publicly readable. Private repos
(the UK microdata, under UK Data Service licence) are refused even when
the caller asks.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from policyengine.cli import main
from policyengine.provenance.manifest import (
    get_data_release_manifest,
    get_release_manifest,
)
from policyengine.provenance.zenodo import (
    ZENODO_SANDBOX_API,
    PrivateSourceRepoError,
    ZenodoDepositError,
    deposition_metadata,
    mirror_release_to_zenodo,
)

from .test_trace_tro import _us_data_release_manifest

BUCKET = "https://zenodo.example/api/files/bucket-1"


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = json.dumps(self._payload)

    def json(self) -> dict:
        return self._payload


class _FakeSession:
    """Records every request; serves canned Zenodo + HF API responses."""

    def __init__(
        self,
        *,
        hf_public: bool = True,
        hf_gated: bool = False,
        hf_status: int = 401,
        publish_doi: str = "10.5281/z.1",
    ):
        self.requests: list[tuple[str, str]] = []
        self.uploads: dict[str, bytes] = {}
        self.metadata: dict | None = None
        self.published = False
        self.hf_public = hf_public
        self.hf_gated = hf_gated
        self.hf_status = hf_status
        self.publish_doi = publish_doi

    def post(self, url, *, json=None, data=None, headers=None, timeout=None):
        self.requests.append(("POST", url))
        if url.endswith("/deposit/depositions"):
            return _FakeResponse(
                201,
                {
                    "id": 4321,
                    "links": {
                        "bucket": BUCKET,
                        "html": "https://zenodo.example/deposit/4321",
                    },
                },
            )
        if url.endswith("/actions/publish"):
            self.published = True
            return _FakeResponse(
                202,
                {
                    "doi": self.publish_doi,
                    "conceptdoi": "10.5281/z.concept",
                    "links": {"record_html": "https://zenodo.example/records/4321"},
                },
            )
        return _FakeResponse(404)

    def put(self, url, *, data=None, json=None, headers=None, timeout=None):
        self.requests.append(("PUT", url))
        if url.startswith(BUCKET):
            name = url.removeprefix(BUCKET + "/")
            self.uploads[name] = data
            return _FakeResponse(201, {"key": name})
        if "/deposit/depositions/" in url:
            self.metadata = json["metadata"]
            return _FakeResponse(200, {})
        return _FakeResponse(404)

    def get(self, url, *, headers=None, timeout=None):
        self.requests.append(("GET", url))
        if "huggingface.co/api/" in url:
            if not self.hf_public:
                return _FakeResponse(self.hf_status)
            return _FakeResponse(200, {"gated": "auto"} if self.hf_gated else {})
        if url.startswith("https://huggingface.co/datasets/"):
            return _FakeResponse(200)
        return _FakeResponse(404)


@pytest.fixture(autouse=True)
def _clear_manifest_caches():
    yield
    get_release_manifest.cache_clear()
    get_data_release_manifest.cache_clear()


@pytest.fixture
def fake_session():
    return _FakeSession()


def _mirror(session, **overrides):
    kwargs = dict(
        token="test-token",
        session=session,
        data_release_manifest=_us_data_release_manifest(),
    )
    kwargs.update(overrides)
    return mirror_release_to_zenodo("us", **kwargs)


class TestDeposit:
    def test__given_release__then_certification_record_is_deposited(self, fake_session):
        deposit = _mirror(fake_session)
        assert set(fake_session.uploads) == {
            "us.bundle_manifest.json",
            "us.trace.tro.jsonld",
            "us.data_release_manifest.json",
        }
        assert deposit.deposit_id == "4321"
        # The TRO uploaded is the shipped artifact, byte-for-byte.
        from importlib.resources import files

        shipped = (
            files("policyengine")
            .joinpath("data", "bundle", "us.trace.tro.jsonld")
            .read_bytes()
        )
        assert fake_session.uploads["us.trace.tro.jsonld"] == shipped

    def test__given_default__then_dataset_bytes_are_not_deposited(self, fake_session):
        _mirror(fake_session)
        assert not any(name.endswith(".h5") for name in fake_session.uploads)

    def test__given_draft__then_mirrors_have_no_doi_and_not_published(
        self, fake_session
    ):
        deposit = _mirror(fake_session, publish=False)
        assert not fake_session.published
        assert deposit.doi is None
        assert all(mirror.doi is None for mirror in deposit.mirrors)
        assert all(mirror.kind == "zenodo" for mirror in deposit.mirrors)

    def test__given_publish__then_doi_recorded_on_every_mirror(self, fake_session):
        deposit = _mirror(fake_session, publish=True)
        assert fake_session.published
        assert deposit.doi == "10.5281/z.1"
        assert deposit.concept_doi == "10.5281/z.concept"
        assert all(mirror.doi == "10.5281/z.1" for mirror in deposit.mirrors)

    def test__given_uploads__then_mirror_sha256_matches_uploaded_bytes(
        self, fake_session
    ):
        deposit = _mirror(fake_session)
        by_name = {mirror.url.rsplit("/", 1)[-1]: mirror for mirror in deposit.mirrors}
        for name, payload in fake_session.uploads.items():
            assert by_name[name].sha256 == hashlib.sha256(payload).hexdigest()

    def test__given_metadata__then_describes_certified_release(self, fake_session):
        _mirror(fake_session)
        metadata = fake_session.metadata
        assert metadata["upload_type"] == "dataset"
        assert "us" in metadata["title"]
        assert metadata["creators"] == [{"name": "PolicyEngine"}]
        assert any(
            "huggingface.co" in related["identifier"]
            for related in metadata["related_identifiers"]
        )

    def test__given_sandbox__then_requests_hit_sandbox_api(self):
        session = _FakeSession()
        _mirror(session, base_url=ZENODO_SANDBOX_API)
        deposition_posts = [url for method, url in session.requests if method == "POST"]
        assert all(url.startswith(ZENODO_SANDBOX_API) for url in deposition_posts)

    def test__given_no_token__then_raises(self, fake_session, monkeypatch):
        monkeypatch.delenv("ZENODO_TOKEN", raising=False)
        with pytest.raises(ZenodoDepositError, match="token"):
            mirror_release_to_zenodo(
                "us",
                session=fake_session,
                data_release_manifest=_us_data_release_manifest(),
            )

    def test__given_deposit_api_failure__then_raises_with_status(self):
        class _FailingSession(_FakeSession):
            def post(self, url, **kwargs):
                return _FakeResponse(500, {"message": "boom"})

        with pytest.raises(ZenodoDepositError, match="500"):
            _mirror(_FailingSession())


class TestDatasetInclusion:
    def test__given_private_source_repo__then_refuses_even_when_asked(self):
        session = _FakeSession(hf_public=False)
        with pytest.raises(PrivateSourceRepoError, match="private"):
            _mirror(session, include_dataset=True)

    def test__given_gated_source_repo__then_refuses_even_when_metadata_is_200(self):
        # HF returns 200 for gated-repo metadata but access-walls the bytes;
        # a 200 alone must not be treated as public.
        session = _FakeSession(hf_gated=True)
        with pytest.raises(PrivateSourceRepoError, match="gated"):
            _mirror(session, include_dataset=True)

    def test__given_transient_hf_error__then_refuses_as_unverifiable_not_private(self):
        # A 429/5xx means visibility is unknown; refuse with a retryable
        # ZenodoDepositError rather than silently treating it as public.
        session = _FakeSession(hf_public=False, hf_status=429)
        with pytest.raises(ZenodoDepositError, match="verify"):
            _mirror(session, include_dataset=True)

    def test__given_public_source_repo__then_dataset_bytes_deposited(
        self, fake_session
    ):
        payload = b"dataset bytes"
        deposit = _mirror(
            fake_session,
            include_dataset=True,
            dataset_fetcher=lambda url: payload,
        )
        assert fake_session.uploads["populace_us_2024.h5"] == payload
        names = {mirror.url.rsplit("/", 1)[-1] for mirror in deposit.mirrors}
        assert "populace_us_2024.h5" in names


class TestDepositionMetadata:
    def test__given_manifests__then_version_and_description_pinned(self):
        metadata = deposition_metadata(
            get_release_manifest("us"), _us_data_release_manifest()
        )
        assert metadata["version"] == get_release_manifest("us").policyengine_version
        description = metadata["description"]
        assert "populace-us-2024" in description


class TestCLI:
    def test__given_cli__then_prints_mirrors_json(self, monkeypatch, capsys):
        from policyengine.provenance import zenodo as zenodo_module
        from policyengine.provenance.manifest import PreservationMirror

        def fake_mirror(country_id, **kwargs):
            assert country_id == "us"
            return zenodo_module.ZenodoDeposit(
                deposit_id="1",
                deposit_url="https://zenodo.example/deposit/1",
                doi=None,
                concept_doi=None,
                published=False,
                mirrors=[
                    PreservationMirror(
                        kind="zenodo",
                        url="https://zenodo.example/deposit/1/files/us.trace.tro.jsonld",
                    )
                ],
            )

        monkeypatch.setattr(zenodo_module, "mirror_release_to_zenodo", fake_mirror)
        monkeypatch.setenv("ZENODO_TOKEN", "t")
        exit_code = main(["zenodo-mirror", "us"])
        captured = capsys.readouterr()
        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["mirrors"][0]["kind"] == "zenodo"
