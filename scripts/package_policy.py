from __future__ import annotations

from pathlib import PurePosixPath


EXCLUDED_DIRECTORY_NAMES = frozenset(
    {
        "__pycache__",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "comparison_boards",
        "data",
        "htmlcov",
        "local_python",
        "outputs",
        "private",
        "raw_data",
        "runs",
        "site-packages",
        "tmp_v5_validation",
        "venv",
    }
)

FORBIDDEN_ARTIFACT_SUFFIXES = frozenset(
    {
        ".csv",
        ".env",
        ".jpeg",
        ".jpg",
        ".lck",
        ".log",
        ".oggu",
        ".ogwu",
        ".opj",
        ".opju",
        ".pdf",
        ".png",
        ".pyo",
        ".pyc",
        ".rar",
        ".xls",
        ".xlsx",
        ".zip",
    }
)

EXCLUDED_FILE_NAMES = frozenset({".coverage"})


def normalized_parts(path: str | PurePosixPath) -> tuple[str, ...]:
    value = str(path).replace("\\", "/")
    return tuple(part.casefold() for part in PurePosixPath(value).parts)


def is_excluded_directory_name(name: str) -> bool:
    normalized = name.casefold()
    return normalized in EXCLUDED_DIRECTORY_NAMES or normalized.startswith("tmp_")


def contains_local_environment_path(path: str | PurePosixPath) -> bool:
    return any(is_excluded_directory_name(part) for part in normalized_parts(path))


def is_local_interpreter_binary(path: str | PurePosixPath) -> bool:
    name = PurePosixPath(str(path).replace("\\", "/")).name.casefold()
    stem = PurePosixPath(name).stem
    suffix = PurePosixPath(name).suffix
    return stem.startswith("python") and suffix in {".dll", ".exe", ".pyd"}
