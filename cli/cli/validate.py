"""Local validation for user skill workspaces (SKILL.md + references).

Ceilings mirror the server-side defaults (``skills.user_authored.*`` in
vid-agent's ``config/config.yaml``) so failures surface locally before a
wasted round-trip to the API.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

from .workspace import SKILL_FILENAME, collect_reference_files, parse_skill_md

# Server-side defaults (packages/core/src/core/config/settings.py: UserAuthoredSkillConfig)
MAX_BODY_CHARS = 50000
MAX_REFERENCE_FILES = 15

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Default user-authored tool ceiling (docs/SKILL_GUIDE.md §8). The server is
# authoritative and may differ per deployment; unknown tools only produce a
# warning, not a hard error.
KNOWN_TOOLS = {
    "search_web",
    "generate_image",
    "generate_video",
    "generate_tts",
    "generate_music",
    "mix_clips",
    "list_models",
    "search_library",
    "get_library_item",
    "upscale_image",
    "split_image",
    "recognize_image",
    "recognize_video",
    "transcribe_audio",
    "fetch_video_info",
    "download_video",
    "create_document",
    "update_document",
    "get_document",
    "memory_whoami",
    "memory_query",
    "skill_kb_query",
    "memory_store",
    "memory_forget",
    # always-available (ok if declared)
    "read_skill",
    "read_skill_file",
    "write_todos",
    "set_guidance",
    "switch_model",
}

# Tools that only official skills may declare; a user skill declaring these
# is a hard error (server would silently strip them, but the model would
# then think it has capabilities it doesn't).
FORBIDDEN_TOOLS = {
    "list_my_skills",
    "read_my_skill",
    "read_my_skill_file",
    "write_skill_draft",
    "write_skill_reference_file",
    "publish_skill",
    "bind_skill_preset_asset",
    "unbind_skill_preset_asset",
}


def validate_workspace(path: Path) -> Tuple[List[str], List[str]]:
    """Return (errors, warnings). Non-empty errors => invalid."""
    errors: List[str] = []
    warnings: List[str] = []

    skill_md = path / SKILL_FILENAME
    if not skill_md.is_file():
        return [f"missing {SKILL_FILENAME}"], warnings

    try:
        text = skill_md.read_text(encoding="utf-8")
        fields = parse_skill_md(text)
    except Exception as e:
        return [f"failed to parse {SKILL_FILENAME}: {e}"], warnings

    name = fields.get("name") or ""
    description = fields.get("description") or ""
    body = fields.get("body") or ""
    allowed_tools = fields.get("allowed_tools") or []

    if not name:
        errors.append("frontmatter.name must not be empty")
    elif not NAME_RE.match(name):
        warnings.append(
            f"name '{name}' should be kebab-case (lowercase letters/digits plus hyphens, e.g. image-generation); "
            "the server normalizes illegal characters to hyphens, which can collapse into a meaningless name"
        )

    if not description.strip():
        errors.append("frontmatter.description must not be empty (trigger condition)")
    elif len(description) < 10:
        warnings.append("description is too short; write 'Use when the user wants to…' and cover nearby scenarios")

    forbidden = [t for t in allowed_tools if t in FORBIDDEN_TOOLS]
    if forbidden:
        errors.append(
            f"allowed-tools includes authoring tools reserved for official skills: {forbidden} "
            "(user skills cannot declare these; the server will strip them)"
        )

    if not allowed_tools:
        warnings.append("allowed-tools is not declared; add an allowlist if the steps call platform tools")
    else:
        unknown = [t for t in allowed_tools if t not in KNOWN_TOOLS and t not in FORBIDDEN_TOOLS]
        if unknown:
            warnings.append(
                f"allowed-tools includes tools not on the usual list: {unknown} "
                "(they may be filtered by the server ceiling)"
            )

    if not body.strip():
        errors.append("SKILL.md body is empty")
    elif len(body) > MAX_BODY_CHARS:
        errors.append(f"body is {len(body)} characters, over the server limit of {MAX_BODY_CHARS}")
    elif len(body) > MAX_BODY_CHARS * 0.8:
        warnings.append(
            f"body is about {len(body)} characters, approaching the server limit of {MAX_BODY_CHARS}; "
            "consider splitting into references/"
        )

    lower = body.lower()
    # Accept both English and Chinese section titles (existing user skills may use either).
    if "何时使用" not in body and "when to use" not in lower:
        warnings.append("body should include a 'When to use' section")
    if "步骤" not in body and "steps" not in lower and "制作阶段" not in body and "production stages" not in lower:
        warnings.append("body should include a 'Steps' or 'Production stages' section")

    refs = collect_reference_files(path)
    if len(refs) > MAX_REFERENCE_FILES:
        errors.append(f"{len(refs)} reference files, over the server limit of {MAX_REFERENCE_FILES}")

    for rel in refs:
        if "/" not in rel:
            warnings.append(
                f"reference file '{rel}' should live in a subdirectory (e.g. references/{rel}); "
                "bare filenames are harder to organize"
            )

    mentioned = re.findall(r"`(references/[^`]+)`", body)
    for rel in mentioned:
        if rel not in refs and not (path / rel).is_file():
            errors.append(f"body references a missing file: {rel}")

    for tool in allowed_tools:
        if tool in body or f"`{tool}`" in body:
            continue
        in_refs = any(tool in content for content in refs.values())
        if not in_refs and tool not in ("list_models",):
            warnings.append(f"allowed-tools includes '{tool}', but the body/references never mention it")

    return errors, warnings
