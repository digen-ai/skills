"""Local skill workspace helpers: SKILL.md <-> API fields, zip pack/unpack.

Mirrors the parsing rules of the server-side loader
(``core.agent.skills.skill_loader``) closely enough that anything packed
here will round-trip through the user skills API unchanged.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

SKILL_FILENAME = "SKILL.md"
_SKIP_DIR_NAMES = {".git", "__pycache__", "scripts", ".venv"}
_SKIP_EXTENSIONS = {
    ".pyc", ".so", ".dylib", ".dll", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mp3", ".zip", ".tar", ".gz",
}


def build_skill_md(skill: Dict[str, Any]) -> str:
    """Serialize API skill fields into a SKILL.md document."""
    name = skill.get("name") or ""
    description = skill.get("description") or ""
    display_name = skill.get("display_name")
    allowed_tools = skill.get("allowed_tools") or []
    metadata = skill.get("metadata") or {}
    body = (skill.get("body") or "").strip()

    fm: Dict[str, Any] = {"name": name}
    if display_name:
        fm["display_name"] = display_name
    fm["description"] = description
    if allowed_tools:
        fm["allowed-tools"] = list(allowed_tools)
    for k, v in metadata.items():
        if k in ("name", "description", "display_name", "title", "allowed-tools", "allowed_tools"):
            continue
        fm[k] = v

    fm_text = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False).strip()
    return f"---\n{fm_text}\n---\n\n{body}\n"


def parse_skill_md(text: str, *, default_name: Optional[str] = None) -> Dict[str, Any]:
    """Parse SKILL.md into API-shaped fields (no reference_files)."""
    frontmatter, body = _split_frontmatter(text)
    name = frontmatter.pop("name", None) or default_name
    if not name:
        raise ValueError("SKILL.md is missing name (neither frontmatter nor directory name provided)")

    description = frontmatter.pop("description", "") or ""
    display_name = frontmatter.pop("display_name", None) or frontmatter.pop("title", None)
    allowed_tools = (
        frontmatter.pop("allowed-tools", None)
        or frontmatter.pop("allowed_tools", None)
        or []
    )
    if isinstance(allowed_tools, str):
        allowed_tools = [t.strip() for t in allowed_tools.split(",") if t.strip()]

    return {
        "name": str(name),
        "description": str(description),
        "display_name": display_name,
        "allowed_tools": list(allowed_tools),
        "body": body.strip(),
        "metadata": dict(frontmatter),
    }


def write_workspace(target: Path, skill: Dict[str, Any]) -> None:
    """Write SKILL.md + references/ from an API skill payload."""
    target.mkdir(parents=True, exist_ok=True)
    (target / SKILL_FILENAME).write_text(build_skill_md(skill), encoding="utf-8")

    refs: Dict[str, str] = skill.get("reference_files") or {}
    for rel, content in refs.items():
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise ValueError(f"illegal reference path: {rel}")
        out = target / rel_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content if isinstance(content, str) else str(content), encoding="utf-8")


def read_workspace(path: Path) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Read local workspace into (skill_fields, reference_files)."""
    skill_md = path / SKILL_FILENAME
    if not skill_md.is_file():
        raise FileNotFoundError(f"Missing {SKILL_FILENAME} in {path}")

    fields = parse_skill_md(skill_md.read_text(encoding="utf-8"), default_name=path.name)
    refs = collect_reference_files(path)
    return fields, refs


def _should_skip_rel(rel_parts: Tuple[str, ...]) -> bool:
    if not rel_parts:
        return True
    for p in rel_parts[:-1]:
        if p in _SKIP_DIR_NAMES or p.startswith("."):
            return True
    name = rel_parts[-1]
    if name.startswith(".") and name != SKILL_FILENAME:
        return True
    suffix = Path(name).suffix.lower()
    if suffix in _SKIP_EXTENSIONS:
        return True
    return False


def collect_reference_files(path: Path) -> Dict[str, str]:
    """Collect text files under workspace except SKILL.md / skipped dirs."""
    refs: Dict[str, str] = {}
    for item in sorted(path.rglob("*")):
        if not item.is_file():
            continue
        rel_parts = item.relative_to(path).parts
        if rel_parts == (SKILL_FILENAME,):
            continue
        if _should_skip_rel(rel_parts):
            continue
        rel = item.relative_to(path).as_posix()
        try:
            refs[rel] = item.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
    return refs


def pack_workspace(path: Path) -> bytes:
    """Pack workspace into a zip with SKILL.md at the root.

    Uses the same skip rules as ``collect_reference_files`` so CLI metadata
    (``.digen-skill-id``), ``.git``, ``scripts/``, and binaries never go into
    the zip. The server treats every non-SKILL.md entry as a reference file.
    """
    skill_md = path / SKILL_FILENAME
    if not skill_md.is_file():
        raise FileNotFoundError(f"Missing required file: {SKILL_FILENAME}")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in path.rglob("*"):
            if not item.is_file():
                continue
            rel_parts = item.relative_to(path).parts
            if rel_parts != (SKILL_FILENAME,) and _should_skip_rel(rel_parts):
                continue
            arc = item.relative_to(path).as_posix()
            zf.write(item, arc)
    return buf.getvalue()


def infer_skill_name(path: Path) -> str:
    """Prefer frontmatter name; fall back to dirname prefix before last '-' segment."""
    skill_md = path / SKILL_FILENAME
    if skill_md.is_file():
        fields = parse_skill_md(skill_md.read_text(encoding="utf-8"), default_name=None)
        return fields["name"]
    dirname = path.name
    if "-" in dirname:
        return dirname.rsplit("-", 1)[0]
    return dirname


def _split_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text
    raw_fm, body = match.group(1), match.group(2)
    try:
        data = yaml.safe_load(raw_fm) or {}
        if not isinstance(data, dict):
            raise ValueError("frontmatter must be a YAML mapping")
        return data, body
    except yaml.YAMLError as e:
        raise ValueError(f"failed to parse SKILL.md frontmatter YAML: {e}") from e
