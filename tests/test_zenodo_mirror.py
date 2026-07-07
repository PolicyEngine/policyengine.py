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
    def __init__(
        self,
        status_code: int,
        payload: dict | None = None,
        *,
        raise_json: bool = False,
    ):
        self.status_code = status_code
        self._payload = payload or {}
        self._raise_json = raise_json
        # A non-JSON body (e.g. a Cloudflare challenge page served with a
        # 200) has text but no decodable JSON object.
        self.text = (
            "<html>challenge</html>" if raise_json else json.dumps(self._payload)
        )

    def json(self) -> dict:
        if self._raise_json:
            raise ValueError("No JSON object could be decoded")
        return self._payload


class _FakeSession:
    """Records every request; serves canned Zenodo + HF API responses."""

    def __init__(
        self,
        *,
        hf_public: bool = True,
        hf_gated: bool = False,
        hf_private: bool = False,
        hf_nonjson: bool = False,
        hf_status: int = 401,
        publish_doi: str = "10.5281/z.1",
    ):
        self.requests: list[tuple[str, str]] = []
        self.uploads: dict[str, bytes] = {}
        self.metadata: dict | None = None
        self.published = False
        self.hf_public = hf_public
        self.hf_gated = hf_gated
        self.hf_private = hf_private
        self.hf_nonjson = hf_nonjson
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
            if self.hf_nonjson:
                return _FakeResponse(200, raise_json=True)
            payload: dict = {}
            if self.hf_gated:
                payload["gated"] = "auto"
            if self.hf_private:
                payload["private"] = True
            return _FakeResponse(200, payload)
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
        uploaded_hashes = {
            hashlib.sha256(payload).hexdigest()
            for payload in fake_session.uploads.values()
        }
        assert {mirror.sha256 for mirror in deposit.mirrors} == uploaded_hashes

    def test__given_draft__then_mirror_urls_are_provisional_deposit_handle(
        self, fake_session
    ):
        # A draft has no published per-file URL, so every mirror points at
        # the draft deposit itself as a provisional handle rather than a
        # fabricated /files/ path that would 404.
        deposit = _mirror(fake_session, publish=False)
        assert all(
            mirror.url == "https://zenodo.example/deposit/4321"
            for mirror in deposit.mirrors
        )
        assert all("/files/" not in mirror.url for mirror in deposit.mirrors)

    def test__given_publish__then_mirror_urls_are_per_file_record_urls(
        self, fake_session
    ):
        # Publishing yields stable, dereferenceable per-file record URLs.
        deposit = _mirror(fake_session, publish=True)
        assert all(
            mirror.url.startswith("https://zenodo.example/records/4321/files/")
            for mirror in deposit.mirrors
        )
        names = {mirror.url.rsplit("/", 1)[-1] for mirror in deposit.mirrors}
        assert "us.trace.tro.jsonld" in names

    def test__given_post_creation_failure__then_error_names_the_orphaned_draft(self):
        # Once the deposition is created, a later failure (here a metadata
        # PUT 400) must re-raise with the deposit id and URL so the staged
        # draft can be found and deleted rather than silently orphaned.
        class _MetadataFailSession(_FakeSession):
            def put(self, url, *, data=None, json=None, headers=None, timeout=None):
                self.requests.append(("PUT", url))
                if url.startswith(BUCKET):
                    name = url.removeprefix(BUCKET + "/")
                    self.uploads[name] = data
                    return _FakeResponse(201, {"key": name})
                if "/deposit/depositions/" in url:
                    return _FakeResponse(400, {"message": "bad metadata"})
                return _FakeResponse(404)

        with pytest.raises(ZenodoDepositError) as exc_info:
            _mirror(_MetadataFailSession())
        message = str(exc_info.value)
        assert "4321" in message
        assert "https://zenodo.example/deposit/4321" in message
        assert "delete or resume" in message

    def test__given_zipimport_keyerror__then_raises_zenodo_error(self, monkeypatch):
        # A zipimport loader raises KeyError (not FileNotFoundError) when a
        # resource is absent from the archive; it must map to a
        # ZenodoDepositError, not escape as a raw KeyError.
        import importlib.resources as importlib_resources

        from policyengine.provenance import zenodo as zenodo_module

        class _MissingResource:
            def read_bytes(self):
                raise KeyError("resource not in zip archive")

        class _Traversable:
            def joinpath(self, *parts):
                return _MissingResource()

        monkeypatch.setattr(
            importlib_resources, "files", lambda package: _Traversable()
        )
        with pytest.raises(ZenodoDepositError, match="bundled TRACE TRO"):
            zenodo_module._bundled_tro_bytes("us")

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

    def test__given_non_json_200__then_refuses_as_unverifiable(self):
        # A 200 with a non-JSON body (e.g. a Cloudflare challenge page) is
        # not positive confirmation of a public repo; refuse rather than
        # fail open by defaulting gated to False.
        session = _FakeSession(hf_nonjson=True)
        with pytest.raises(ZenodoDepositError, match="verify"):
            _mirror(session, include_dataset=True)

    def test__given_private_flag_in_200_metadata__then_refuses(self):
        # An authenticated session reads a private repo's metadata as
        # 200 {"private": true, "gated": false}; the gate must check
        # private, not only gated.
        session = _FakeSession(hf_private=True)
        with pytest.raises(PrivateSourceRepoError, match="private"):
            _mirror(session, include_dataset=True)

    def test__given_public_source_repo__then_dataset_bytes_deposited(
        self, fake_session, monkeypatch
    ):
        from policyengine.provenance import zenodo as zenodo_module

        payload = b"dataset bytes"
        # The gate now verifies fetched bytes against the certified sha256,
        # so pin this payload's hash on the manifest for the happy path.
        base = get_release_manifest("us")
        certified = base.certified_data_artifact.model_copy(
            update={"sha256": hashlib.sha256(payload).hexdigest()}
        )
        manifest = base.model_copy(update={"certified_data_artifact": certified})
        monkeypatch.setattr(
            zenodo_module, "get_release_manifest", lambda country_id: manifest
        )
        deposit = _mirror(
            fake_session,
            include_dataset=True,
            dataset_fetcher=lambda url: payload,
        )
        assert fake_session.uploads["populace_us_2024.h5"] == payload
        assert hashlib.sha256(payload).hexdigest() in {
            mirror.sha256 for mirror in deposit.mirrors
        }

    def test__given_tampered_dataset_bytes__then_refuses_on_sha256_mismatch(
        self, fake_session
    ):
        # The public gate passes, but the fetched bytes do not match the
        # certified sha256, so the deposit is refused before any upload and
        # the error names both hashes.
        certified_sha256 = get_release_manifest("us").certified_data_artifact.sha256
        with pytest.raises(ZenodoDepositError) as exc_info:
            _mirror(
                fake_session,
                include_dataset=True,
                dataset_fetcher=lambda url: b"tampered",
            )
        message = str(exc_info.value)
        assert hashlib.sha256(b"tampered").hexdigest() in message
        assert certified_sha256 in message
        assert not fake_session.uploads


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

    def test__given_unknown_country__then_clean_error_exit(self, monkeypatch, capsys):
        # get_release_manifest raises ValueError for an unknown country id;
        # the CLI must catch it and exit 1 with a clean message, not a
        # traceback. Reaches the manifest lookup (no live network) with a
        # token present.
        monkeypatch.setenv("ZENODO_TOKEN", "t")
        exit_code = main(["zenodo-mirror", "usa"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "usa" in captured.err
