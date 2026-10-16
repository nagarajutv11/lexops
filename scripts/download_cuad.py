"""Download CUAD v1 (CC BY 4.0) from Zenodo into data/cuad/."""

from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

ROOT = Path(__file__).resolve().parents[1]
CUAD_DIR = ROOT / "data" / "cuad"
ZIP_PATH = CUAD_DIR / "CUAD_v1.zip"
ZENODO_URL = "https://zenodo.org/records/4595826/files/CUAD_v1.zip?download=1"
EXPECTED_MD5 = "c38f490a984420b8a62600db401fafd5"


def _progress(block_count: int, block_size: int, total: int) -> None:
    if total <= 0:
        return
    done = min(block_count * block_size, total)
    if done == total or block_count % 200 == 0:
        print(f"\r{done / 1_000_000:.1f} / {total / 1_000_000:.1f} MB", end="", flush=True)


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    CUAD_DIR.mkdir(parents=True, exist_ok=True)
    if not ZIP_PATH.exists() or ZIP_PATH.stat().st_size < 50_000_000:
        print(f"Downloading {ZENODO_URL}")
        urlretrieve(ZENODO_URL, ZIP_PATH, _progress)
        print()
    digest = _md5(ZIP_PATH)
    if digest != EXPECTED_MD5:
        print(f"MD5 mismatch: {digest} (expected {EXPECTED_MD5})", file=sys.stderr)
        return 1
    print(f"MD5 ok ({digest})")
    with zipfile.ZipFile(ZIP_PATH) as archive:
        archive.extractall(CUAD_DIR)
    csvs = list(CUAD_DIR.rglob("master_clauses.csv"))
    pdfs = list(CUAD_DIR.rglob("*.pdf"))
    txts = list(CUAD_DIR.rglob("*.txt"))
    jsons = [path for path in CUAD_DIR.rglob("*.json") if "cuad" in path.name.lower()]
    print(f"csv={len(csvs)} pdf={len(pdfs)} txt={len(txts)} json={len(jsons)}")
    if not csvs or not pdfs or not txts or not jsons:
        print("Extracted archive is missing CUAD artifacts", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
