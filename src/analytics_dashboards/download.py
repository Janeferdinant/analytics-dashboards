"""Runtime dataset download with SHA-256 verification. Raw data is never committed."""

from __future__ import annotations

import hashlib
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .paths import RAW


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    url: str
    filename: str
    sha256: str
    license: str
    page: str
    extract: tuple[str, ...] = ()  # members to pull out of a zip, as relative paths


SOURCES: dict[str, Source] = {
    "retail": Source(
        key="retail",
        title="Online Retail II (UCI)",
        url="https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip",
        filename="online_retail_ii.zip",
        sha256="572e36277c2390fbfde10664750731e0a86f55e33470d91919085f0408e67bfb",
        license="CC BY 4.0",
        page="https://archive.ics.uci.edu/dataset/502/online+retail+ii",
        extract=("online_retail_II.xlsx",),
    ),
    "marketing": Source(
        key="marketing",
        title="Bank Marketing (UCI)",
        url="https://archive.ics.uci.edu/static/public/222/bank+marketing.zip",
        filename="bank_marketing.zip",
        sha256="e0bf5f5de5b846e2f18e9d90606637267d46dfa260e0f17bb12e605db5efbeb4",
        license="CC BY 4.0",
        page="https://archive.ics.uci.edu/dataset/222/bank+marketing",
        extract=("bank-additional.zip",),
    ),
    "hr": Source(
        key="hr",
        title="Saudi Employee Attrition Dataset (Mendeley Data)",
        url=(
            "https://data.mendeley.com/public-files/datasets/6z2hty8php/files/"
            "b422d0af-74b6-47b8-94ff-614e09c2382f/file_downloaded"
        ),
        filename="employee_attrition_original.xlsx",
        sha256="9a44efec36c467062d1a19230a31eb0c101b3407f0da0ed8c3e1812bbef79650",
        license="CC BY 4.0",
        page="https://data.mendeley.com/datasets/6z2hty8php/1",
    ),
}


class ChecksumError(RuntimeError):
    """Raised when a downloaded file does not match its pinned SHA-256."""


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(path: Path, expected: str) -> None:
    actual = sha256_of(path)
    if actual != expected:
        raise ChecksumError(f"{path.name}: expected sha256 {expected}, got {actual}")


def fetch(key: str, dest: Path = RAW) -> Path:
    """Download one dataset (skipped if already present and valid); return its folder."""
    src = SOURCES[key]
    folder = dest / key
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / src.filename
    if not (target.exists() and sha256_of(target) == src.sha256):
        request = urllib.request.Request(src.url, headers={"User-Agent": "analytics-dashboards/0.1"})
        tmp = target.with_suffix(target.suffix + ".part")
        with urllib.request.urlopen(request, timeout=300) as response, tmp.open("wb") as out:
            while block := response.read(1 << 20):
                out.write(block)
        verify(tmp, src.sha256)
        tmp.replace(target)
    if target.suffix == ".zip":
        with zipfile.ZipFile(target) as archive:
            for member in src.extract:
                if not (folder / member).exists():
                    archive.extract(member, folder)
        if key == "marketing":
            inner = folder / "bank-additional.zip"
            with zipfile.ZipFile(inner) as archive:
                member = "bank-additional/bank-additional-full.csv"
                if not (folder / member).exists():
                    archive.extract(member, folder)
    return folder


def fetch_all(dest: Path = RAW) -> dict[str, Path]:
    return {key: fetch(key, dest) for key in SOURCES}
