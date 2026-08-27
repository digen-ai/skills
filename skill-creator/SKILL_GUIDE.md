# User skill writing guide

This document explains how to write **user-authored skills** for **Digen skill_agent** (capability packs mounted in a conversation). Unlike official skills, user skills are constrained by a server-side **ceiling** (tool allowlist, body length, reference-file count, skills per user). Listing on the marketplace also requires a security scan plus review.

Reference implementations: `skill-creator/templates/` (`simple_skill/` for a single capability, `multi_stage/` for a multi-stage example).

---

## Contents

1. [How it works (progressive disclosure)](#1-how-it-works-progressive-disclosure)
2. [Skill directory structure](#2-skill-directory-structure)
3. [SKILL.md format](#3-skillmd-format)
4. [Writing the body](#4-writing-the-body)
5. [Multi-stage skills and references/](#5-multi-stage-skills-and-references)
6. [Platform tools (inside the user ceiling)](#6-platform-tools-inside-the-user-ceiling)
7. [Always-available tools](#7-always-available-tools)
8. [User skill limits (ceiling)](#8-user-skill-limits-ceiling)
9. [Publishing and the marketplace](#9-publishing-and-the-marketplace)
10. [AI authoring checklist](#10-ai-authoring-checklist)

---

## 1. How it works (progressive disclosure)

Skill Agent **does not** dump every skill's full text into the system prompt. Disclosure has three layers:

```
Layer 1 (system prompt)  → name + description only (index, used to decide relevance)
        ↓ model calls read_skill(name)
Layer 2 (tool result)    → SKILL.md body + allowed_tools + reference_files path list
        ↓ model calls read_skill_file(name, path) as needed
Layer 3 (tool result)    → full contents of one text file under references/
```

Therefore:

- **`description` must be good**: it is the only signal the model uses to decide whether to `read_skill`. Too narrow misses triggers; too broad false-triggers.
- **The body must be executable**: after `read_skill`, the model should be able to complete the task from the steps. Do not assume it still remembers other config files.
- **Put details in `references/`**: long flows, templates, and examples go into reference files. The body only needs an index table plus collaboration rules.

Always available (no `allowed-tools` needed): `read_skill`, `read_skill_file`, `write_todos`, `set_guidance`, `switch_model`. Executable capability **only comes from platform cloud tools**. `scripts/` inside a skill pack is **not** parsed or executed.

---

## 2. Skill directory structure

```
my-skill/
├── SKILL.md                 # required: frontmatter + body
└── references/              # optional: extra docs (progressive-disclosure layer 3)
    ├── stage_a.md
    └── templates/
        └── outline.md
```

| Rule | Notes |
|------|-------|
| Must have `SKILL.md` | filename case is fixed |
| `name` must be kebab-case | `[a-z0-9]+(-[a-z0-9]+)*`, e.g. `image-generation`. The server normalizes illegal characters (non-ASCII / underscores / spaces) to hyphens, so a bad name can collapse into something meaningless |
| Reference files are text-only | `.md` / `.yaml` / `.json` / `.txt`, etc. Images / video / zip and other binaries are skipped |
| Skipped directories | `scripts/`, `__pycache__/`, directories starting with `.` |
| Pack and upload | `digenskill push` packs automatically with `SKILL.md` at the zip root; hand-packing also works |

`digenskill init <name>` generates a minimal template that matches this structure. Edit that.

---

## 3. SKILL.md format

```markdown
---
name: image-generation
description: Use when the user wants to generate, draw, or create an image (illustration, poster, avatar, scene, etc.)
display_name: Image Generation   # optional, UI display name
allowed-tools:
  - list_models
  - generate_image
---

# Image Generation

## When to use
...

## Steps
...

## Notes
...
```

### Frontmatter fields

| Field | Required | Notes |
|-------|----------|-------|
| `name` | yes | unique skill id, **kebab-case** |
| `description` | yes | **one-sentence trigger condition** (see below). Only appears in the layer-1 index |
| `allowed-tools` | strongly recommended | allowlist of platform tools this skill needs, constrained by the section 8 ceiling. Also accepts `allowed_tools` or a comma-separated string |
| `display_name` / `title` | no | human-readable name; does not affect LLM routing |
| `model` | no | LLM tier: `standard` (default) / `uncensored` (adult/sensitive content). User skills may declare this; see section 6.3 |
| other fields | no | kept if they are in the `metadata` allowlist: `license`, `homepage`, `compatibility`, `version`, `tags`, `author`. Other fields are dropped by the server |

### Write a good description (most important)

`description` answers: **under what user intent should this skill be enabled**, not a feature slogan.

Good:

```yaml
description: Use when the user wants to generate, draw, or create an image (illustration, poster, avatar, scene, etc.)
```

Bad:

```yaml
description: a powerful image tool          # too vague; the model cannot tell when to read
description: calls generate_image           # implementation detail, not user intent
```

Tip: use the "Use when the user wants to…" pattern; put synonyms and sub-scenarios in parentheses; if a partial edit should also trigger, say so explicitly in the description.

---

## 4. Writing the body

The body is the model's only operating manual after `read_skill`. Recommended structure:

```markdown
# <readable title>

A sentence or two on what this skill does.

## When to use
- Trigger scenarios (echo the description, can be more specific)

## Steps
1. …
2. Call `tool_name`, parameter conventions: …
3. …

## Notes
- Failure/refusal policy, do not invent URLs, content policy, etc.
```

Writing principles:

1. **Only write behavior this skill needs**: do not restate system-level rules the orchestrator already injects.
2. **Steps must be executable**: be explicit about "do this first → call which tool → pass which key parameters → how to reply after success".
3. **Put parameter conventions in the body**: especially `name`, `entity_type`, `orientation`, and generation-tool `model=<channel>` (see section 6.2).
4. **Do not assume structured project state**: content reused across turns should be Markdown in the reply, or URLs of assets already on the canvas.
5. **Outputs land on the canvas automatically**: summarize in natural language; do not paste long URLs.
6. **Report failures honestly**: if a tool returns `success=false`, do not pretend it succeeded.
7. **Content policy**: politely refuse violent/sexual requests and do not call generation tools (unless you explicitly declare `model: uncensored` and the product allows it).
8. **Watch length**: default body cap is about `50000` characters (`digenskill validate` checks this). Split complex flows into `references/`.

---

## 5. Multi-stage skills and references/

Do not cram a long flow into the `SKILL.md` body:

**Body**: stage index table + collaboration rules + when to read which file
**references/\*.md**: detailed steps for each stage

```markdown
## Production stages (references/)

| Stage | File | Tools | When to read |
|-------|------|-------|--------------|
| 1. Script | `references/scriptwriting.md` | none | user gives an idea / wants to edit the script |
| 2. Visual design | `references/visual-design.md` | `generate_image` | need character/scene reference images |

## Collaboration

- User says "generate it all": advance in table order; do not ask for confirmation between stages.
- User only wants one step changed: read only that file; do not redo the whole pipeline.
- Call `write_todos` when entering a multi-stage flow; call `set_guidance` at stage boundaries / when done.
```

Reference paths are relative to the skill root (e.g. `references/visual-design.md`) and must match paths mentioned in the body (`digenskill validate` checks this). User skills default to at most about **15** reference files. See `templates/multi_stage/` for a full example.

---

## 6. Platform tools (inside the user ceiling)

### 6.1 Common tools

| Tool | Purpose | Typical parameters |
|------|---------|-------------------|
| `list_models` | list available models | `model_type`: `image`/`video`/`tts`/`asr`/`music` |
| `search_library` | search the asset library (public + personal) | `keyword`; optional `category`, `scope`, `limit`, `offset` |
| `get_library_item` | get a library item | `item_id` (from `search_library`) |
| `generate_image` | text-to-image / image-to-image | `prompt`; optional `input_urls`, `orientation`, `resolution`, `model` (channel), `name`, `entity_type` |
| `generate_video` | text-to-video / image-to-video | `prompt`; `input_urls`; `orientation`, `resolution`, `duration`, `model` (channel) |
| `generate_tts` | voiceover | `text`; `mode`: `design`/`clone` |
| `generate_music` | text-to-music | `prompt`; optional `model='music'` |
| `mix_clips` | stitch clips and mix audio | `clips[]` (`video`/`videos` + `audio`/`audios`) |
| `upscale_image` | image upscale | `input_url`; optional `scale` |
| `split_image` | grid-split an image | `input_urls`; optional `rows`, `cols` |
| `recognize_image` / `recognize_video` | image / video understanding | `image_url`/`video_url`; optional `prompt` |
| `transcribe_audio` | audio transcription | `audio_url` |
| `search_web` | web search | `query` |
| `fetch_video_info` / `download_video` | social-video metadata / temp download URL | `url` |
| `create_document` / `update_document` / `get_document` | create / in-place update / read a document asset | `content`; `update_document` needs `asset_id` |
| `memory_whoami` / `memory_query` / `memory_store` / `memory_forget` | cross-session personal memory | see section 6.4; **not** always-available; must be declared |
| `skill_kb_query` | query the skill shared knowledge base | same as above, **not** always-available |

Full parameter constraints come from the runtime tool schema. The skill body only needs business defaults (see the 6.2 examples).

### 6.2 Generation channel selection

For image / video / TTS / music tools, write `model=` as a **stable channel** (e.g. `t2i`, `i2v`, `ref2v`, `tts.design`). **Do not** write physical model names — ops can rebind models without changing the skill. Common channels:

| Channel | Tool | Purpose |
|---------|------|---------|
| `t2i` / `t2i.hd` | `generate_image` | text-to-image (`.hd` is higher quality, no NSFW) |
| `i2i` / `i2i.hd` | `generate_image` | image-to-image (has a reference image) |
| `i2v` / `i2v.nsfw` | `generate_video` | image-to-video (use `.nsfw` for adult content) |
| `ref2v` | `generate_video` | reference-to-video (character consistency); also pass `gen_mode='reference_to_video'` |
| `tts.design` / `tts.clone` | `generate_tts` | voice design / clone |
| `music` | `generate_music` | text-to-music |
| `asr` | `transcribe_audio` | speech-to-text |

Size is only `orientation` (`landscape`/`portrait`/`square`) + `resolution` (`480P`–`4K`). Do not invent pixel dimensions.

### 6.3 Model tier (frontmatter `model:`)

For adult/sensitive content, declare in frontmatter:

```yaml
---
name: nsfw-image
description: ...
model: uncensored
---
```

When this skill is mounted, later LLM calls automatically switch to the uncensored tier (upgrade-only, lasts for the rest of the session). You can also write "when adult content is detected, call `switch_model(tier='uncensored', reason=...)`" so the model decides (`switch_model` is always available). This is not the same as a generation-tool `model='i2v.nsfw'` (channel).

### 6.4 Long-term memory (`memory_*` / `skill_kb_query`)

These 5 tools are **not** always-available. They must be declared in `allowed-tools` (they are inside the default user ceiling, so you may declare them):

| Tool | Purpose |
|------|---------|
| `memory_whoami` | read a user-identity summary (use at session start) |
| `memory_query` | search the user's personal memory |
| `memory_store` | write cross-session facts/preferences worth keeping |
| `memory_forget` | soft-delete one personal memory |
| `skill_kb_query` | search the **currently mounted skills'** shared knowledge base (a different store from personal memory; do not mix them) |

Recommended usage: `memory_whoami` at start; `memory_query` before acting on preferences/project background; `memory_store` when the user shares something worth keeping across sessions; on "forget …", `memory_query` first to get `id`, then `memory_forget`. Do not store: one-off task progress, passwords/secrets, or unconfirmed guesses.

---

## 7. Always-available tools

`read_skill` / `read_skill_file` / `write_todos` / `set_guidance` / `switch_model` do not need to be in `allowed-tools`.

### 7.1 `write_todos` (multi-step progress)

```json
{"todos": [{"id": "script", "content": "Write the script", "status": "in_progress"}]}
```

Replaces the whole list. `status` is `pending`/`in_progress`/`completed`. At most one `in_progress` at a time. Max 20 items.

### 7.2 `set_guidance` (suggested-action buttons)

Call in the **same turn** as the final reply text:

```json
{"suggested_questions": [{"text": "Start designing character/scene visuals"}]}
```

There is no hard count; give a sensible number for the situation. Do not call other tools in the same turn as this one.

---

## 8. User skill limits (ceiling)

Default tool ceiling (`allowed-tools` is intersected with this; out-of-ceiling tools are silently filtered by the server — **no error, but unavailable to the model**, so check carefully):

`search_web`, `generate_image`, `generate_video`, `generate_tts`, `generate_music`, `mix_clips`, `list_models`, `search_library`, `get_library_item`, `upscale_image`, `split_image`, `recognize_image`, `recognize_video`, `transcribe_audio`, `fetch_video_info`, `download_video`, `create_document`, `update_document`, `get_document`, `memory_whoami`, `memory_query`, `skill_kb_query`, `memory_store`, `memory_forget`

By default this **does not include** `sandbox_*` (sandbox toolset) or `generate_video_director`.

**Never declare** (regardless of ceiling config): `list_my_skills` / `read_my_skill` / `read_my_skill_file` / `write_skill_draft` / `write_skill_reference_file` / `publish_skill` / `bind_skill_preset_asset` / `unbind_skill_preset_asset` — these are authoring tools only official skills may use (e.g. Digen's builtin conversational skill-authoring skill). User skills that declare them are filtered; `digenskill validate` errors immediately.

Quantity limits (`digenskill validate` checks most of these locally; the server is authoritative):

- Body `max_body_chars`: about 50000 characters
- Reference files `max_reference_files`: about 15
- Skills per user `max_per_user`: about 50

---

## 9. Publishing and the marketplace

```
local SKILL.md → digenskill push (private draft) → publish from the web UI (request public)
                                                    ↓
                                          security scan + review
                                          approved → listed immediately (status=published)
                                          pending  → human review (status=in_review)
```

- After listing, submitting a content update: the marketplace keeps showing the last approved version until the new version is approved (`review_status` briefly becomes `pending`, but `status` stays `published`).
- There is no `digenskill publish`. Cover, category, sample video, and the listing request are done on the web UI.
- `digenskill cancel-review <id>`: withdraw an in-review request. If it was never listed, this is equivalent to making it private. If it was already listed, only this update is withdrawn and the marketplace keeps the old version.
- `digenskill unpublish <id>`: unlist immediately and make private.
- Closed-source content protection (`content-visibility`) can also be set on the web. Do not invent REST calls for listing.

---

## 10. AI authoring checklist

After writing or editing a user skill, confirm each item (`digenskill validate` covers items marked ✅):

- [ ] ✅ Valid YAML frontmatter; `name` and `description` are non-empty
- [ ] ✅ `name` is kebab-case
- [ ] `description` is a **user-intent trigger**, not a feature ad or implementation detail
- [ ] ✅ `allowed-tools` does not include authoring tools reserved for official skills (section 8)
- [ ] `allowed-tools` only includes tools this skill actually needs and that are inside the user ceiling
- [ ] ✅ Body is non-empty and under the server character limit
- [ ] Body includes When to use / Steps / Notes (or a multi-stage index + collaboration rules)
- [ ] Tool names in the steps match `allowed-tools`; key parameters (`name`, `entity_type`, `orientation`, generation `model=<channel>`) have conventions
- [ ] Media generation uses the correct channel from section 6.2, with no physical model names
- [ ] ✅ Long content is split into `references/`, and paths mentioned in the body exist
- [ ] Multi-step flows require `write_todos`; stage boundaries / completion require `set_guidance`
- [ ] If cross-session memory is used, `allowed-tools` declares the `memory_*` / `skill_kb_query` tools needed
- [ ] Adult/sensitive content declares `model: uncensored` or documents when to call `switch_model`
- [ ] Requires honest failure reporting, no invented URLs, and refusal of disallowed content
- [ ] `digenskill validate` has no errors (handle warnings as needed)
