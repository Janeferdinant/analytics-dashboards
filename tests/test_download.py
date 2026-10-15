from __future__ import annotations

import hashlib

import pytest

from analytics_dashboards import download


def test_sha256_of_matches_hashlib(tmp_path):
    path = tmp_path / "x.bin"
    path.write_bytes(b"abc")
    assert download.sha256_of(path) == hashlib.sha256(b"abc").hexdigest()


def test_verify_rejects_a_changed_file(tmp_path):
    path = tmp_path / "x.bin"
    path.write_bytes(b"abc")
    with pytest.raises(download.ChecksumError):
        download.verify(path, "0" * 64)


def test_every_source_has_a_pinned_checksum_and_license():
    for source in download.SOURCES.values():
        assert len(source.sha256) == 64
        assert source.license == "CC BY 4.0"
        assert source.url.startswith("https://")
