#!/usr/bin/env python3
"""Discover and optionally download OriginLab Graph Gallery projects."""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from retrieve_official_template import USER_AGENT, is_allowed_url, retrieve, validate_archive


GALLERY_URL = "https://www.originlab.com/www/products/GraphGallery.aspx"
MAX_ITEMS_LIMIT = 20


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self._in_title = False
        self._heading_tag = ""
        self._heading_complete = False
        self._title_parts: list[str] = []
        self._heading_parts: list[str] = []
        self.meta_title = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = {str(key).lower(): value for key, value in attrs}
        if tag == "a":
            href = attributes.get("href")
            if href:
                self.links.append(href)
        elif tag == "title":
            self._in_title = True
        elif tag in {"h1", "h2"} and not self._heading_complete:
            self._heading_tag = tag
        elif tag == "meta" and attributes.get("property", "").lower() == "og:title":
            self.meta_title = " ".join(str(attributes.get("content") or "").split())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        elif tag == self._heading_tag:
            self._heading_tag = ""
            self._heading_complete = True

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        elif self._heading_tag:
            self._heading_parts.append(data)

    @property
    def title(self) -> str:
        document_title = " ".join(" ".join(self._title_parts).split())
        heading = " ".join(" ".join(self._heading_parts).split())
        return self.meta_title or heading or document_title


def parse_html(html: str) -> LinkParser:
    parser = LinkParser()
    parser.feed(html)
    parser.close()
    return parser


def build_gallery_url(search_terms: str = "", gallery_url: str = "") -> str:
    if bool(search_terms.strip()) == bool(gallery_url.strip()):
        raise ValueError("provide exactly one of search_terms or gallery_url")
    if gallery_url:
        parsed = urllib.parse.urlparse(gallery_url)
        if not is_allowed_url(gallery_url) or parsed.path.lower() != "/www/products/graphgallery.aspx":
            raise ValueError("gallery_url must be the official HTTPS GraphGallery.aspx page")
        return gallery_url
    query = urllib.parse.urlencode({"s": "1", "k": search_terms.strip(), "sort": "Newest"})
    return f"{GALLERY_URL}?{query}"


def extract_gids(html: str, base_url: str = GALLERY_URL) -> list[str]:
    seen: set[str] = set()
    gids: list[str] = []
    for href in parse_html(html).links:
        parsed = urllib.parse.urlparse(urllib.parse.urljoin(base_url, href))
        query = urllib.parse.parse_qs(parsed.query)
        for key, values in query.items():
            if key.lower() != "gid":
                continue
            for value in values:
                if value.isdigit() and value not in seen:
                    seen.add(value)
                    gids.append(value)
    return gids


def extract_zip_urls(html: str, detail_url: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for href in parse_html(html).links:
        url = urllib.parse.urljoin(detail_url, href)
        parsed = urllib.parse.urlparse(url)
        if (
            is_allowed_url(url)
            and parsed.path.lower().endswith(".zip")
            and "/ftp/graph_gallery/" in parsed.path.lower()
            and url not in seen
        ):
            seen.add(url)
            urls.append(url)
    return urls


def safe_archive_name(url: str, gid: str, index: int) -> str:
    raw = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._")
    if not stem.lower().endswith(".zip"):
        stem = f"originlab_gid_{gid}_{index}.zip"
    return stem or f"originlab_gid_{gid}_{index}.zip"


def candidate_title(document_title: str, zip_urls: list[str], gid: str) -> str:
    generic = document_title.strip().lower().replace(" ", "") in {"originlabgraphgallery", "graphgallery"}
    if document_title.strip() and not generic:
        return document_title.strip()
    if zip_urls:
        archive = safe_archive_name(zip_urls[0], gid, 1)
        return Path(archive).stem.replace("_", " ").strip()
    return f"OriginLab Graph Gallery GID {gid}"


def fetch_html_once(url: str, timeout: float, referer: str = "") -> tuple[str, dict[str, Any]]:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    if referer:
        headers["Referer"] = referer
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = getattr(response, "status", None) or response.getcode()
        final_url = response.geturl()
        if status != 200:
            raise ValueError(f"unexpected HTTP status {status}")
        if not is_allowed_url(final_url):
            raise ValueError(f"redirected to a non-official host: {final_url}")
        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type.lower():
            raise ValueError(f"expected HTML response, got {content_type or 'unknown content type'}")
        payload = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace"), {
        "status": status,
        "final_url": final_url,
        "content_type": content_type,
        "response_bytes": len(payload),
    }


def fetch_html(url: str, attempts: int, timeout: float, backoff: float, referer: str = "") -> tuple[str, list[dict[str, Any]]]:
    if attempts < 3:
        raise ValueError("attempts must be at least 3")
    if not is_allowed_url(url) or (referer and not is_allowed_url(referer)):
        raise ValueError("HTML retrieval requires official HTTPS URLs")
    records: list[dict[str, Any]] = []
    for attempt in range(1, attempts + 1):
        record: dict[str, Any] = {"timestamp_utc": utc_now(), "url": url, "attempt": attempt, "method": "python_urllib"}
        try:
            html, response = fetch_html_once(url, timeout, referer)
            record.update(response)
            record["result"] = "ok"
            records.append(record)
            return html, records
        except (OSError, ValueError, urllib.error.URLError) as exc:
            record.update({"result": "failed", "error_type": type(exc).__name__, "error": str(exc)})
            records.append(record)
            if attempt < attempts:
                time.sleep(min(backoff * (2 ** (attempt - 1)), 30.0))
    raise RuntimeError(json.dumps({"error_code": "E132_TEMPLATE_SEARCH_FAILED", "attempts": records}))


def discover(
    gallery_url: str,
    max_items: int,
    attempts: int,
    timeout: float,
    backoff: float,
    download_dir: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    if not 1 <= max_items <= MAX_ITEMS_LIMIT:
        raise ValueError(f"max_items must be between 1 and {MAX_ITEMS_LIMIT}")
    gallery_html, gallery_attempts = fetch_html(gallery_url, attempts, timeout, backoff)
    gids = extract_gids(gallery_html, gallery_url)[:max_items]
    candidates: list[dict[str, Any]] = []
    if download_dir:
        download_dir.mkdir(parents=True, exist_ok=True)

    for gid in gids:
        detail_url = f"{GALLERY_URL}?GID={gid}"
        candidate: dict[str, Any] = {"gid": gid, "detail_url": detail_url, "status": "detail_failed"}
        try:
            detail_html, detail_attempts = fetch_html(detail_url, attempts, timeout, backoff, gallery_url)
            parsed = parse_html(detail_html)
            zip_urls = extract_zip_urls(detail_html, detail_url)
            candidate.update({
                "title": candidate_title(parsed.title, zip_urls, gid),
                "document_title": parsed.title,
                "zip_urls": zip_urls,
                "detail_attempts": detail_attempts,
            })
            candidate["status"] = "discovered" if zip_urls else "no_zip_link"
            if download_dir:
                downloads = []
                for index, zip_url in enumerate(zip_urls, start=1):
                    output = download_dir / safe_archive_name(zip_url, gid, index)
                    if output.exists() and not force:
                        try:
                            validation = validate_archive(output)
                            downloads.append({"status": "existing_valid", "output": str(output), "validation": validation})
                        except (OSError, ValueError) as exc:
                            downloads.append({"status": "existing_invalid", "output": str(output), "error": str(exc)})
                        continue
                    downloads.append(retrieve([zip_url], output, attempts, timeout, backoff, None, detail_url))
                candidate["downloads"] = downloads
        except RuntimeError as exc:
            candidate["error"] = str(exc)
        candidates.append(candidate)

    discovered = sum(candidate["status"] == "discovered" for candidate in candidates)
    return {
        "schema": "originplot.graph_gallery_search.v1",
        "status": "ok" if discovered else "failed",
        "error_code": None if discovered else "E132_TEMPLATE_SEARCH_FAILED",
        "gallery_url": gallery_url,
        "gallery_attempts": gallery_attempts,
        "candidate_count": len(candidates),
        "discovered_count": discovered,
        "candidates": candidates,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--search-terms")
    source.add_argument("--gallery-url")
    parser.add_argument("--max-items", type=int, default=5)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--backoff", type=float, default=2.0)
    parser.add_argument("--download-dir", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--manifest", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    gallery_url = build_gallery_url(args.search_terms or "", args.gallery_url or "")
    result = discover(
        gallery_url,
        args.max_items,
        args.attempts,
        args.timeout,
        args.backoff,
        args.download_dir.resolve() if args.download_dir else None,
        args.force,
    )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "manifest": str(args.manifest)}, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
