from __future__ import annotations

import io
import tarfile

from mimi.events import EventLog
from mimi.schemas import Claim, EvidenceKind, ReportSubmission
from mimi.stages import ground


TARBALL_URL = "https://registry.npmjs.org/test-package/-/test-package-1.0.0.tgz"


class FakeJsonResponse:
    def json(self) -> dict:
        return {"dist": {"tarball": TARBALL_URL}}


class FakeTarballResponse:
    def __init__(self, chunks: list[bytes], content_length: str | None = None):
        self.headers = {"Content-Length": content_length} if content_length is not None else {}
        self.chunks = chunks
        self.read_chunks: list[bytes] = []

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self, chunk_size: int):
        assert chunk_size == 64 * 1024
        for chunk in self.chunks:
            self.read_chunks.append(chunk)
            yield chunk


class FakeClient:
    def __init__(self, tarball_response: FakeTarballResponse):
        self.tarball_response = tarball_response
        self.get_urls: list[str] = []
        self.stream_calls: list[tuple[str, str]] = []

    def get(self, url: str) -> FakeJsonResponse:
        self.get_urls.append(url)
        return FakeJsonResponse()

    def stream(self, method: str, url: str) -> FakeTarballResponse:
        self.stream_calls.append((method, url))
        return self.tarball_response


def _tarball(files: dict[str, bytes]) -> bytes:
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as tf:
        for name, contents in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(contents)
            tf.addfile(info, io.BytesIO(contents))
    return archive.getvalue()


def _inputs() -> tuple[ReportSubmission, Claim, EventLog]:
    submission = ReportSubmission(report_text="A test report", package_spec="test-package@1.0.0")
    claim = Claim(
        package="test-package",
        cited_files=["index.js"],
        cited_symbols=["vulnerableFunction"],
        expected_effect="the function is called",
    )
    return submission, claim, EventLog("test-report")


def test_tarball_check_streams_and_searches_within_cap(monkeypatch):
    blob = _tarball({"package/index.js": b"function vulnerableFunction() {}"})
    monkeypatch.setattr(ground, "_TARBALL_CAP", len(blob) + 1)
    response = FakeTarballResponse([blob], content_length=str(len(blob)))
    client = FakeClient(response)
    submission, claim, events = _inputs()

    evidence = ground._tarball_check(submission, claim, client, events)

    assert client.stream_calls == [("GET", TARBALL_URL)]
    assert len(response.read_chunks) == 1
    assert {item.kind for item in evidence} == {EvidenceKind.FILE_FOUND, EvidenceKind.SYMBOL_FOUND}


def test_tarball_check_rejects_oversize_content_length_without_reading(monkeypatch):
    monkeypatch.setattr(ground, "_TARBALL_CAP", 8)
    response = FakeTarballResponse([b"must not read"], content_length="9")
    client = FakeClient(response)
    submission, claim, events = _inputs()

    evidence = ground._tarball_check(submission, claim, client, events)

    assert response.read_chunks == []
    assert len(evidence) == 1
    assert evidence[0].kind == EvidenceKind.NOTE
    assert "8 MiB limit" in evidence[0].detail


def test_tarball_check_enforces_cap_when_content_length_is_untrusted(monkeypatch):
    monkeypatch.setattr(ground, "_TARBALL_CAP", 8)
    response = FakeTarballResponse([b"12345678", b"9", b"must not read"], content_length="1")
    client = FakeClient(response)
    submission, claim, events = _inputs()

    evidence = ground._tarball_check(submission, claim, client, events)

    assert response.read_chunks == [b"12345678", b"9"]
    assert len(evidence) == 1
    assert evidence[0].kind == EvidenceKind.NOTE
    assert "8 MiB limit" in evidence[0].detail


def test_compressed_archive_cannot_exceed_the_expanded_search_budget(monkeypatch):
    blob = _tarball({"package/index.js": b"a" * 20_000})
    monkeypatch.setattr(ground, "_UNPACKED_CAP", 1024)
    submission, claim, events = _inputs()
    evidence = ground._tarball_check(submission, claim, FakeClient(FakeTarballResponse([blob])), events)
    assert len(evidence) == 1
    assert evidence[0].kind == EvidenceKind.NOTE
    assert "expanded tarball" in evidence[0].detail


def test_too_many_entries_make_absence_inconclusive(monkeypatch):
    blob = _tarball({"package/a.js": b"", "package/b.js": b"", "package/index.js": b""})
    monkeypatch.setattr(ground, "_MAX_MEMBERS", 2)
    submission, claim, events = _inputs()
    evidence = ground._tarball_check(submission, claim, FakeClient(FakeTarballResponse([blob])), events)
    assert len(evidence) == 1
    assert evidence[0].kind == EvidenceKind.NOTE
    assert "2-entry" in evidence[0].detail


def test_large_file_is_present_but_unsearched_symbols_are_not_absent(monkeypatch):
    blob = _tarball({"package/index.js": b"function vulnerableFunction() {}"})
    monkeypatch.setattr(ground, "_SOURCE_FILE_CAP", 16)
    submission, claim, events = _inputs()
    evidence = ground._tarball_check(submission, claim, FakeClient(FakeTarballResponse([blob])), events)
    assert any(item.kind == EvidenceKind.FILE_FOUND and item.target == "index.js" for item in evidence)
    assert any(item.kind == EvidenceKind.NOTE and item.target == "vulnerableFunction" for item in evidence)
    assert not any(item.kind in {EvidenceKind.FILE_ABSENT, EvidenceKind.SYMBOL_ABSENT} for item in evidence)


def test_cited_file_must_match_a_complete_path_component():
    blob = _tarball({"package/not-index.js": b"function vulnerableFunction() {}", "package/.index.js": b""})
    submission, claim, events = _inputs()
    claim.cited_files.append("./.index.js")
    evidence = ground._tarball_check(submission, claim, FakeClient(FakeTarballResponse([blob])), events)
    assert any(item.kind == EvidenceKind.FILE_ABSENT and item.target == "index.js" for item in evidence)
    assert not any(item.kind == EvidenceKind.FILE_FOUND and item.target == "index.js" for item in evidence)
    assert any(item.kind == EvidenceKind.FILE_FOUND and item.target == "./.index.js" for item in evidence)
