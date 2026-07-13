#!/usr/bin/env python3
"""Download and validate OriginLab template archives with bounded retries."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


ALLOWED_HOST_SUFFIXES = ("originlab.com", "cloudfront.net")
USER_AGENT = "OriginPlot-template-retriever/1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_allowed_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and any(
        host == suffix or host.endswith("." + suffix) for suffix in ALLOWED_HOST_SUFFIXES
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_archive(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        signature = handle.read(4)
        sample = signature + handle.read(508)
    if signature[:2] != b"PK":
        raise ValueError("response does not have a ZIP signature")
    if b"<html" in sample.lower() or b"<!doctype html" in sample.lower():
        raise ValueError("response is HTML, not a template archive")

    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"ZIP integrity failure at {bad_member}")
        members = []
        project_members = []
        for info in archive.infolist():
            normalized = info.filename.replace("\\", "/")
            member = PurePosixPath(normalized)
            if member.is_absolute() or ".." in member.parts:
                raise ValueError(f"unsafe ZIP member path: {info.filename}")
            members.append(info.filename)
            if member.suffix.lower() in {".opj", ".opju", ".otp", ".otpu"}:
                project_members.append(info.filename)
        if not project_members:
            raise ValueError("archive contains no Origin project or template file")

    return {
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "member_count": len(members),
        "project_members": project_members,
    }


def safe_extract(path: Path, destination: Path) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    extracted = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            target = (destination / info.filename).resolve()
            if os.path.commonpath([str(root), str(target)]) != str(root):
                raise ValueError(f"unsafe extraction target: {info.filename}")
            archive.extract(info, destination)
            extracted.append(info.filename)
    return extracted


def fetch_once(url: str, temporary: Path, timeout: float) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = getattr(response, "status", None) or response.getcode()
        final_url = response.geturl()
        if status != 200:
            raise ValueError(f"unexpected HTTP status {status}")
        if not is_allowed_url(final_url):
            raise ValueError(f"redirected to a non-official host: {final_url}")
        content_type = response.headers.get("Content-Type", "")
        with temporary.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    if temporary.stat().st_size < 1024:
        raise ValueError("download is unexpectedly small")
    return {"status": status, "final_url": final_url, "content_type": content_type}


def retrieve(
    urls: list[str],
    output: Path,
    attempts: int,
    timeout: float,
    backoff: float,
    extract_dir: Path | None,
) -> dict[str, object]:
    if attempts < 3:
        raise ValueError("attempts must be at least 3")
    for url in urls:
        if not is_allowed_url(url):
            raise ValueError(f"URL is not an allowed official HTTPS host: {url}")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + f".part.{os.getpid()}")
    records: list[dict[str, object]] = []

    for url in urls:
        for attempt in range(1, attempts + 1):
            record: dict[str, object] = {
                "timestamp_utc": utc_now(),
                "url": url,
                "method": "python_urllib",
                "attempt": attempt,
            }
            try:
                if temporary.exists():
                    temporary.unlink()
                response = fetch_once(url, temporary, timeout)
                validation = validate_archive(temporary)
                temporary.replace(output)
                record.update(response)
                record.update(validation)
                record["result"] = "ok"
                records.append(record)
                extracted = safe_extract(output, extract_dir) if extract_dir else []
                return {
                    "schema": "originplot.official_template_retrieval.v1",
                    "status": "ok",
                    "selected_url": url,
                    "output": str(output),
                    "validation": validation,
                    "extracted_members": extracted,
                    "attempts": records,
                }
            except (OSError, ValueError, zipfile.BadZipFile, urllib.error.URLError) as exc:
                record["result"] = "failed"
                record["error_type"] = type(exc).__name__
                record["error"] = str(exc)
                if temporary.exists():
                    record["response_bytes"] = temporary.stat().st_size
                    temporary.unlink()
                records.append(record)
                if attempt < attempts:
                    time.sleep(min(backoff * (2 ** (attempt - 1)), 30.0))

    return {
        "schema": "originplot.official_template_retrieval.v1",
        "status": "failed",
        "error_code": "E131_TEMPLATE_RETRIEVAL_EXHAUSTED",
        "attempts": records,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", required=True, help="Official HTTPS ZIP URL; repeat for alternates")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--backoff", type=float, default=2.0)
    parser.add_argument("--extract-dir", type=Path)
    parser.add_argument("--log", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = retrieve(
        args.url,
        args.output.resolve(),
        args.attempts,
        args.timeout,
        args.backoff,
        args.extract_dir.resolve() if args.extract_dir else None,
    )
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "log": str(args.log)}, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
