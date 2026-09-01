from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from originplot.core.errors import OriginPlotError

from .models import FIGURE_SPEC_SCHEMA, FigureSpec

SUPPORTED_TABLE_SUFFIXES = {".csv", ".tsv", ".txt", ".xls", ".xlsx"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_headers(values: tuple[Any, ...] | list[Any]) -> list[str]:
    headers: list[str] = []
    seen: dict[str, int] = {}
    for index, value in enumerate(values, start=1):
        base = str(value).strip() if value is not None and str(value).strip() else f"Unnamed_{index}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        headers.append(base if count == 0 else f"{base}_{count + 1}")
    return headers


def _read_delimited(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".tsv":
        delimiter = "\t"
    elif path.suffix.lower() == ".txt":
        sample = path.read_text(encoding="utf-8-sig", errors="replace")[:8192]
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;").delimiter
        except csv.Error:
            delimiter = "\t" if "\t" in sample else ","
    else:
        delimiter = ","
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        headers = _normalize_headers(next(reader, []))
        return [dict(zip(headers, row)) for row in reader if any(str(value).strip() for value in row)]


def _read_xlsx(path: Path, sheet: str | None) -> list[dict[str, Any]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise OriginPlotError("E302_XLSX_READER_UNAVAILABLE", "openpyxl is required for XLSX input") from exc
    book = load_workbook(path, read_only=True, data_only=True)
    try:
        try:
            worksheet = book[sheet] if sheet else book.active
        except KeyError as exc:
            raise OriginPlotError("E309_XLSX_SHEET_MISSING", f"worksheet does not exist: {sheet}") from exc
        values = worksheet.iter_rows(values_only=True)
        headers = _normalize_headers(list(next(values, ())))
        return [dict(zip(headers, row)) for row in values if any(value not in (None, "") for value in row)]
    finally:
        book.close()


def _read_xls(path: Path, sheet: str | None) -> list[dict[str, Any]]:
    try:
        import xlrd
    except ImportError as exc:
        raise OriginPlotError("E310_XLS_READER_UNAVAILABLE", "xlrd is required for legacy XLS input") from exc
    book = xlrd.open_workbook(str(path), on_demand=True)
    try:
        try:
            worksheet = book.sheet_by_name(sheet) if sheet else book.sheet_by_index(0)
        except (IndexError, xlrd.biffh.XLRDError) as exc:
            raise OriginPlotError("E309_XLSX_SHEET_MISSING", f"worksheet does not exist: {sheet}") from exc
        if worksheet.nrows == 0:
            return []
        headers = _normalize_headers(worksheet.row_values(0))
        return [dict(zip(headers, worksheet.row_values(row))) for row in range(1, worksheet.nrows)]
    finally:
        book.release_resources()


def read_table(path: Path, sheet: str | None = None) -> list[dict[str, Any]]:
    path = path.resolve()
    if not path.is_file():
        raise OriginPlotError("E306_DATA_SOURCE_MISSING", f"data source does not exist: {path}")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_TABLE_SUFFIXES:
        raise OriginPlotError("E303_DATA_FORMAT_UNSUPPORTED", f"unsupported table format: {suffix}")
    if suffix in {".csv", ".tsv", ".txt"}:
        return _read_delimited(path)
    if suffix == ".xlsx":
        return _read_xlsx(path, sheet)
    return _read_xls(path, sheet)


def _ensure_object(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise OriginPlotError("E300_FIGURE_SPEC_INVALID", f"{name} must be an object")
    return dict(value)


def _mapped_columns(data: dict[str, Any], figure: dict[str, Any]) -> set[str]:
    columns: set[str] = set()
    plot_type = str(figure.get("type") or "").lower()
    if plot_type == "multi_panel":
        for panel in figure.get("panels") or []:
            if isinstance(panel, dict):
                columns.update(_mapped_columns(_ensure_object(panel.get("data"), "panel.data"), _ensure_object(panel.get("figure"), "panel.figure")))
        return columns
    for item in data.get("series") or []:
        if isinstance(item, dict):
            for key in ("x", "y", "x_error", "y_error", "category", "group", "label", "z"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    columns.add(value.strip())
    matrix = data.get("matrix")
    if isinstance(matrix, dict):
        for key in ("x", "y", "z"):
            value = matrix.get(key)
            if isinstance(value, str) and value.strip():
                columns.add(value.strip())
    return columns


def normalize_figure_spec(payload: dict[str, Any], base_dir: Path | None = None) -> FigureSpec:
    if not isinstance(payload, dict) or payload.get("schema") != FIGURE_SPEC_SCHEMA:
        raise OriginPlotError("E300_FIGURE_SPEC_INVALID", f"FigureSpec schema must be {FIGURE_SPEC_SCHEMA}")
    base_dir = (base_dir or Path.cwd()).resolve()
    source = _ensure_object(payload.get("source"), "source")
    raw_file = source.get("file")
    if not isinstance(raw_file, str) or not raw_file.strip():
        raise OriginPlotError("E306_DATA_SOURCE_MISSING", "FigureSpec source.file is required")
    source_path = Path(raw_file)
    if not source_path.is_absolute():
        source_path = base_dir / source_path
    source_path = source_path.resolve()
    if not source_path.is_file():
        raise OriginPlotError("E306_DATA_SOURCE_MISSING", f"data source does not exist: {source_path}")
    if source_path.suffix.lower() not in SUPPORTED_TABLE_SUFFIXES:
        raise OriginPlotError("E303_DATA_FORMAT_UNSUPPORTED", f"unsupported table format: {source_path.suffix}")

    actual_hash = file_sha256(source_path)
    expected_hash = str(source.get("hash") or "").strip().lower()
    if expected_hash and expected_hash != actual_hash:
        raise OriginPlotError("E311_SOURCE_HASH_MISMATCH", "FigureSpec source hash does not match the current data file")

    data = _ensure_object(payload.get("data"), "data")
    figure = _ensure_object(payload.get("figure"), "figure")
    style = _ensure_object(payload.get("style"), "style")
    layout = _ensure_object(payload.get("layout"), "layout")
    verification = _ensure_object(payload.get("verification"), "verification")
    plot_type = str(figure.get("type") or "").strip().lower()
    if not plot_type:
        raise OriginPlotError("E300_FIGURE_SPEC_INVALID", "figure.type is required")

    sheet = str(source.get("sheet") or "").strip() or None
    rows = read_table(source_path, sheet)
    if not rows:
        raise OriginPlotError("E308_DATA_TOO_SHORT", "source table contains no data rows")
    headers = set(rows[0])
    missing = sorted(_mapped_columns(data, figure) - headers)
    if missing:
        raise OriginPlotError("E307_DATA_COLUMNS_MISSING", "required columns not found: " + ", ".join(missing))

    page = layout.get("page")
    if isinstance(page, dict):
        for field in ("width_cm", "height_cm"):
            value = page.get(field)
            if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) <= 0):
                raise OriginPlotError("E300_FIGURE_SPEC_INVALID", f"layout.page.{field} must be a positive number")

    return FigureSpec(
        source_path=source_path,
        source_hash=actual_hash,
        sheet=sheet,
        data=data,
        figure=figure,
        style=style,
        layout=layout,
        verification=verification,
        raw=dict(payload),
    )


def load_figure_spec(path: Path) -> FigureSpec:
    path = path.resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OriginPlotError("E300_FIGURE_SPEC_INVALID", f"cannot read FigureSpec: {path}") from exc
    if not isinstance(payload, dict):
        raise OriginPlotError("E300_FIGURE_SPEC_INVALID", "FigureSpec root must be an object")
    return normalize_figure_spec(payload, path.parent)
