# Skill Agent Authoring Guide

This document explains how to write Skills for the **`skill_agent` workflow** (`AgentHarness`).

> | | Skill Agent Harness (the only current path) |
> |---|---|
> | Orchestrator | `core.agent.harness.agent.AgentHarness` |
> | Config entry | **`SKILL.md` package** (+ an optional minimal `orchestrator_config.yaml`) |
> | State model | **No structured project state**; progress lives in the conversation + canvas assets + `write_todos` |
> | Capabilities | A single agent + **progressively disclosed Skill instructions** + platform cloud tools |
> | When to use | Composable, uploadable capability packs; user and official Skill marketplaces |

**Do not** write a Skill with the retired `data_schemas` / `operations` / Agent prompt YAML. A Skill is a **Markdown playbook** the model reads, not a data-contract config.

Reference implementations:

- Skill authoring tools (create and publish a user Skill in conversation): `examples/skill_creator/` + `packages/core/src/core/tools/skill_authoring.py`
- Orchestrator: `packages/core/src/core/agent/harness/agent.py`
- Parser: `packages/core/src/core/agent/skills/skill_loader.py`

---

## Contents

1. [How it works (progressive disclosure)](#1-how-it-works-progressive-disclosure)
2. [Skill directory layout](#2-skill-directory-layout)
3. [SKILL.md format](#3-skillmd-format)
4. [Writing the body](#4-writing-the-body)
5. [Multi-stage Skills and references/](#5-multi-stage-skills-and-references)
6. [Platform tool catalog and common parameters](#6-platform-tool-catalog-and-common-parameters)
7. [Always-available tools (`read_skill` / `write_todos` / `set_guidance`) and memory tools that must be declared (`memory_*`)](#7-always-available-tools)
8. [User Skill limits (ceiling)](#8-user-skill-limits-ceiling)
9. [Skill authoring tools (skill-creator, official Skills only)](#9-skill-authoring-tools-skill-creator-official-skills-only)
10. [orchestrator_config (optional)](#10-orchestrator_config-optional)
11. [Complete examples](#11-complete-examples)
12. [AI authoring checklist](#12-ai-authoring-checklist)

---

## 1. How it works (progressive disclosure)

The Skill Agent does **not** stuff every Skill's full text into the system prompt. Disclosure has three layers:

```
Layer 1 (system prompt)   → name + description only (an index, used to judge relevance)
        ↓ model calls read_skill(name)
Layer 2 (tool result)     → SKILL.md body + allowed_tools + reference_files paths + preset_assets list
        ↓ model calls read_skill_file(name, path) as needed
Layer 3 (tool result)     → the full text of one file under references/
```

Therefore:

- **`description` must be written well.** It is the model's only basis for deciding whether to `read_skill`. Too narrow and the Skill is missed; too broad and it fires by mistake.
- **The body must be executable.** After `read_skill`, the model should be able to finish the task step by step. Do not assume it still remembers some other config file.
- **Put details in `references/`.** Split long workflows, templates, and examples into reference files. Keep the body to an index table plus collaboration principles, so one read does not pull in a huge context.
- **Media goes through preset assets.** Do **not** put brand logos, character base images, reference voice clips, or other images/videos/audio into the zip. Use the public `preset_assets` list (`asset_id` + a stable `s3://` uri). See "Preset assets" below.

Always available (independent of `allowed-tools`): `read_skill`, `read_skill_file`, `write_todos`. If the workflow has `suggested_questions` enabled (on by default), `set_guidance` is available too. **Note:** `memory_whoami` / `memory_query` / `skill_kb_query` / `memory_store` / `memory_forget` are **not** always available. A Skill that needs long-term memory or a shared knowledge base must declare those tools explicitly in its own `allowed-tools` (see section 7.4).

Executable capability comes **only from platform cloud tools** (`generate_image`, `search_web`, `memory_*`, and so on). A `scripts/` directory inside a Skill package is **not** parsed or executed (the directory is skipped).

---

## 2. Skill directory layout

```
my-skill/
├── SKILL.md                 # required: frontmatter + body
└── references/              # optional: extra docs (progressive-disclosure layer 3)
    ├── stage_a.md
    └── templates/
        └── outline.md
```

Rules:

| Rule | Notes |
|---|---|
| `SKILL.md` is required | The filename casing is fixed |
| `name` should match the directory name | kebab-case (lowercase letters/digits + hyphens), e.g. `image-generation` |
| Reference files are plain text only | `.md` / `.yaml` / `.json` / `.txt`, and similar; binaries such as images, video, and zip are skipped |
| Skipped directories | `scripts/`, `__pycache__/`, and directories whose names start with `.` |
| Packaging for upload | The zip root may be `SKILL.md` directly, or a single top-level subdirectory |

### Preset assets (`preset_assets`)

Unlike `listing.required_assets` (a UI hint that tells the user "bring your own"), **preset assets** are reference images, videos, or audio that ship with the Skill. Media is stored as public `assets` rows (`is_public=true`). The Skill manifest stores both the reference and a stable `s3://` URI:

```json
[
  {
    "key": "brand_logo",
    "label": "Brand logo",
    "asset_id": "skpa_xxxx",
    "type": "image",
    "uri": "s3://bucket/path/logo.png",
    "providers": ["aws"]
  }
]
```

- The zip does **not** bundle binaries. Authors upload or bind them through the HTTP API, or call `bind_skill_preset_asset` on a user attachment inside a skill-creator conversation.
- Install does not copy the file. Installers resolve it by `asset_id` / `uri`. **Do not** write expiring https presigned URLs into the manifest.
- Limit: `skills.preset_assets.max_count` (default 10). Types are limited to image / video / audio.
- At runtime, `read_skill` returns `preset_assets` including `uri` and `providers`. Generation tools accept an **`uri` (`s3://`), `asset_id`, or preset `key`** in `input_urls` / `image_url`; the platform presigns it. skill_agent also injects preset assets of already-mounted Skills into context.

Example of importing a local directory:

```bash
source .venv/bin/activate
python -c "
from core.agent.skills.skill_loader import import_skills_from_directory
import asyncio
asyncio.run(import_skills_from_directory('examples/skill_demo/skills'))
"
```

---

## 3. SKILL.md format

```markdown
---
name: image-generation
description: Use when the user wants to generate, draw, or create an image (illustration, poster, avatar, scene, etc.)
display_name: Image Generation   # optional, name shown in the UI
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
|---|---|---|
| `name` | Yes | Unique Skill id. The system-prompt index and `read_skill(name)` use the same string. Prefer kebab-case (`[a-z0-9]+(-[a-z0-9]+)*`, e.g. `image-generation`). Do not use underscores or camelCase |
| `description` | Yes | **A one-sentence trigger condition** (see below). It appears only in the layer-1 index |
| `allowed-tools` | Strongly recommended | Allowlist of platform tools this Skill needs. `allowed_tools` or a comma-separated string also work |
| `canvas` | No | Output visibility: `model_control` / `hidden_tools` / `hidden_entity_types` (see section 6.2, "Hiding intermediate outputs") |
| `display_name` / `title` | No | Human-readable name. It does not affect LLM routing |
| Other fields | No | Kept as `metadata` (e.g. `version`, `license`). They do not participate in runtime logic |

`allowed-tools` may also be written as `allowed-tools: search_web, generate_image`.

### Writing a good description (most important)

`description` answers **under what user intent this Skill should activate**. It is not a feature slogan.

Good:

```yaml
description: Use when the user wants to generate, draw, or create an image (illustration, poster, avatar, scene, etc.)
```

```yaml
description: Use when the user wants to make a short drama (from a one-line idea to a finished cut: writing, character/location visuals, storyboard images/video, voiceover, and compositing); also use this skill when they only want to advance or revise one of those stages
```

Bad:

```yaml
description: A powerful image tool          # too vague; the model cannot tell when to read
description: Calls generate_image            # exposes implementation details, not user intent
description: Short drama                     # too short; misses boundaries such as "revising one stage also applies"
```

Tip: use the sentence pattern "Use when the user wants…". Put synonyms and sub-scenarios in parentheses. If a partial edit should also trigger the Skill, say so explicitly in the description.

---

## 4. Writing the body

The body is the model's only operating manual after `read_skill`. Recommended structure:

```markdown
# <Readable title>

One or two sentences on what this Skill does, and whether it has structured state (usually it does not).

## When to use
- Trigger scenarios (echo the description, but can be more specific)

## Steps
1. …
2. Call `tool_name`, with these parameter conventions: …
3. …

## Notes
- What to do on failure or refusal, do not invent URLs, content policy, and so on
```

### Body-writing principles (for the AI)

1. **Write only the behavior this Skill needs.** Do not restate system-level rules (function calling, do not output JSON, and so on). The orchestrator already injects those.
2. **Steps must be executable.** Spell out "do this first → call this tool → pass these key parameters → how to reply to the user on success".
3. **Put parameter conventions in the Skill.** Especially `name`, `entity_type`, `orientation`, **`model=<channel>`** for generation tools, and prompt language (Chinese/English). Tool schemas have defaults, but business conventions live in the Skill. For media generation, hardcode a channel. Do not write a physical model name (see section 6.3).
4. **Do not assume project state or operations.** There is no `characters` collection to write. Content that must survive across turns goes in the reply as Markdown, or is referenced by an asset URL already on the canvas.
5. **Outputs land on the canvas automatically.** Summarize the final reply in natural language. **Do not paste long blocks of URLs.**
6. **Report failures honestly.** When a tool returns `success=false`, do not pretend it succeeded or invent a resource link.
7. **Content policy.** Politely refuse requests for violence, sexual content, and similar material. Do not call generation tools.
8. **Keep it short.** A simple Skill should stay in the range of a few hundred to one or two thousand words. Split complex workflows into `references/`. User Skill bodies default to a cap of about `50000` characters (config `skills.user_authored.max_body_chars`). `read_skill` / `read_skill_file` results are also truncated to `orchestrator_config.tool_result_max_chars` (default `8000` characters) before they are fed back to the model. That cap is the global default shared by every tool, so a body written close to `50000` characters is truncated by default. The workflow that hosts the Skill can raise it per tool with `tool_result_max_chars_overrides: {read_skill: 50000, read_skill_file: 50000}` without changing the cap for other tools.

### Conventions for the final reply

- When you need to talk while working: the same turn can emit text plus tool calls (the text is shown immediately).
- When the task is done: emit the final text reply. If you want to recommend a next step, call `set_guidance` in **the same turn** (see section 7). Do not call any other tool.
- For multi-step tasks: call `write_todos` first to list the steps, and update the whole table's `status` as you advance.

---

## 5. Multi-stage Skills and references/

Do not pack every detail of a long workflow (for example a full short-drama pipeline) into the `SKILL.md` body. The right pattern:

**Body:** a stage index table + collaboration principles + when to read which file  
**`references/*.md`:** the detailed steps for each stage

Body skeleton (see `examples/drama_skills/SKILL.md`):

```markdown
## Production stages (references/)

Detailed steps for each stage live under `references/`. **Do not read them all at once.** Decide the current stage first, then use `read_skill_file` to read only that one file.

| Stage | File | Tools used | When to read |
|---|---|---|---|
| 1. Writing | `references/scriptwriting.md` | none | The user gives an idea or wants the script changed |
| 2. Visual design | `references/visual_design.md` | `generate_image` | Character or location reference images are needed |
| … | … | … | … |

## Collaboration principles

- If the user says "generate it in one go": advance through the table in order. Sync progress after each stage, then immediately read the next stage. **Do not ask for confirmation between stages.**
- If the user only wants one stage changed: read only that file. Do not redo the whole pipeline.
- Stop only when the user explicitly says "confirm first" or "let me look".
- Call `write_todos` when entering a multi-stage flow. Call `set_guidance` when you stop at a stage boundary or when the whole pipeline is done.
```

Inside a reference file, use the same "When to use / Steps / Notes" structure, and spell out this stage's tool parameters (for example `entity_type='characters'`).

Reference paths are relative to the Skill root (for example `references/visual_design.md`) and must match the `reference_files` list returned by `read_skill`. User Skills default to about `10` reference files at most.

---

## 6. Platform tool catalog and common parameters

A Skill can declare and use only tools the platform has registered. User-authored Skills are also constrained by the **tool ceiling** (section 8).

### 6.1 Common tools

| Tool | Purpose | Typical parameters |
|---|---|---|
| `list_models` | List available generation models / channels (a fallback check while drafting) | `model_type`: `image` / `video` / `tts` / `asr` / `music`, and similar. **Cannot replace** the channel catalog (see 6.3) |
| `search_library` | Search the asset library (public + personal) | `keyword`; optional `category`, `scope` (`all`/`personal`/`public`), `limit`, `offset`. Returns `uri`+`providers` (no presigned URL) |
| `get_library_item` | Get a library item's details (including media s3 references) | `item_id` (from `search_library`). Returns `media[].uri` / `providers` |
| `generate_image` | Text-to-image / image-to-image | `prompt`; optional `input_urls`, `orientation`, `resolution`, **`model` (a channel, e.g. `t2i` / `i2i.hd`)**, `name`, `entity_type` |
| `generate_video` | Text-to-video / image-to-video / reference-to-video, and similar | `prompt`; `input_urls` (at least 1 reference image in `ref2v` mode; may be empty for `t2v`); `orientation`, `resolution`, `duration`, **`model` (a channel such as `i2v` / `ref2v` / `t2v`; empty defaults to `ref2v`; concrete model names are rejected)**, `name`, `entity_type` |
| `generate_tts` | Voiceover | `text`; `voice_instruction` (required on the `tts.design` channel) or `reference_audio_url` (required on the `tts.clone` channel); optional **`model` (a channel such as `tts.design` / `tts.clone`; the mode is fully determined by the channel; if omitted, the default channel is chosen from whether `reference_audio_url` was passed)**, `name`, `entity_type` |
| `generate_music` | Text-to-music | `prompt`; optional `lyrics` (leave empty for instrumental music or model improvisation), **`model='music'`**, `model_type`, `output_format`, `name`, `entity_type` |
| `mix_clips` | Concatenate and mix multiple clips; optionally burn whole-sentence hard subtitles per clip | `clips[]` (`video`/`videos` + `audio`/`audios`, optional `subtitles`: exactly one of `url` (.srt/.vtt/.ass) or `items` (`text`/`start`/`end`, relative to that clip's output start), optional `style`); track `url` and `subtitles.url` accept asset_id / `s3://` / real https and are presigned automatically; `name`, `entity_type` (channel `clip-mixer`); optional `orientation` (canvas placeholder orientation; does not affect the mix and should match the source clips, e.g. pass `portrait` for a vertical short drama) |
| `caption_video` | Add TikTok / Reels-style word-by-word highlight captions to one finished video and return a new MP4 | `video_url` (required); optional `input_type` (`video` default / `audio`), `template` (default `hormozi`; prefer `mega-stroke` / `cloud-glow` / `sunset-panel` / `italic-heavy-stroke` / `ink-on-white`; interviews: `podcast-clean` or `soft-minimal`; news bars: `lower-third`; unknown IDs are rejected), `size` (`sm`/`md`/`lg`), `position` (`bottom`/`middle`/`top`), `language` (default `auto`), `dictionary`, `emoji_enabled`, `particles_enabled`, `custom_template` (allowlisted shallow overrides; `font_path` is forbidden), `orientation` (canvas placeholder orientation; does not affect burn-in and should match the source), `name`, `entity_type` (default `final_videos`). **Do not pass `model`. Do not pass `words`** (the service runs ASR itself). Does not return a transcript; use `transcribe_audio` for a transcript. This is not the whole-sentence subtitles of `mix_clips` |
| `split_image` | Cut an image grid into tiles | `input_urls`; optional `rows`, `cols`, `output_format`, `quality`, `border` |
| `extract_clip` | Cut a video by time range; each segment is one independent video (not concatenated; clip-mixer service, no channel) | `url`, `segments[]` (either `{start, duration}` or `{start, end}`, at least 1 segment); optional `accurate` (default `false` = stream copy, cut points snap to keyframes; `true` = re-encode for frame accuracy), `output_format` (`mp4`/`mov`/`mkv`), `name`, `entity_type` (default `video_clips`), `orientation` (canvas placeholder orientation). To concatenate or reorder these clips, pass the resulting `asset_id`s to `mix_clips` |
| `extract_frame` | Extract one or more jpg frames from a video (clip-mixer service, no channel) | `url`, `timestamps[]` (`0` = first frame; a positive number = seconds from the start; **a negative number = seconds before the end**, so `-1` is 1 second before the end, not the strict last frame; any positive timestamp past the duration fails the whole call); optional `width`, `name`, `entity_type` (default `extracted_frames`). Each timestamp produces 1 image asset |
| `extract_audio` | Extract a video audio track, or trim/convert audio (clip-mixer service, no channel) | `url` (video or audio); optional `segments[]` (each segment is one **independent** file, not concatenated; `duration`/`end` may be omitted to run to the end of the file; omitted = one file for the whole track), `format` (`m4a` default / `mp3` / `wav`), `name`, `entity_type` (default `extracted_audios`). Fails if the input has no audio track |
| `recognize_image` | Read an image / describe what is in it | `image_url` or `image_base64`; optional `prompt`, `media_type`, `model` |
| `recognize_video` | Understand / describe a video | `video_url`; optional `prompt`, `model` |
| `transcribe_audio` | Transcribe audio (including SRT) | `audio_url`; optional `cache`, **`model='asr'`** |
| `search_web` | Web search | `query`; optional `search_depth`, `max_results` |
| `fetch_video_info` | Social-video metadata | `url` (YouTube/TikTok/IG/FB/X/LinkedIn) |
| `download_video` | Temporary download link for a social video | `url`; optional `quality`, `format` (YouTube/TikTok/IG only) |
| `create_document` | Create a new document asset (same level as image/video/audio, added to the canvas; always creates a new document and never overwrites an existing one) | `content`; optional `name`, `filename`, `content_type` (default `text/markdown`), `entity_type` |
| `update_document` | Update an existing document asset in place (same asset_id; the canvas card refreshes in place and no new asset is created) | `asset_id`, `content` (full replacement); optional `name`, `content_type`, `entity_type` (if omitted, the original document's values are kept) |
| `get_document` | Read a document asset's body by asset_id | `asset_id` (from `create_document` or a document the user uploaded) |

Asset-producing and processing tools (`generate_*`, `split_image`, `mix_clips`, `caption_video`, `extract_clip`, `extract_frame`, `extract_audio`, `create_document`, `update_document`) add the asset to the canvas on success (when the workflow has `add_to_canvas: true`). `recognize_image` / `recognize_video` / `transcribe_audio` / `fetch_video_info` / `download_video` / `get_document` / `search_web` / `search_library` / `get_library_item` return interactive results and are not added to the canvas.

**Asset-library usage (`search_library` → `get_library_item` → a generation tool):** search the public or personal library with `search_library` by keyword, category, and scope (the result is a compact `uri`+`providers`, with no presigned URL). Then call `get_library_item(item_id=...)` to get `media[].uri` / `providers`, write them into project assets, or pass them as input to `generate_image(input_urls=[uri])`, `generate_video`, or `recognize_image` (pass `s3://`; the system presigns before execution).

### 6.2 Canvas asset conventions (strongly recommended in the Skill)

When calling asset-producing tools such as `generate_image` / `generate_video` / `generate_tts` / `generate_music` / `mix_clips` / `caption_video` / `extract_clip` / `extract_frame` / `extract_audio` / `create_document` / `update_document`:

- Pass a short **`name`** (character name, shot title, final-cut title, track title, document title, and so on) so the canvas can display it.
- Pass an agreed **`entity_type`** (defaults to `skill_generation` when omitted). Common values:
  - Images: `characters` / `locations` / `props` / `storyboard_images`
  - Video: `storyboard_videos` / `final_videos` (`caption_video` defaults to `final_videos` when omitted)
  - Audio: defined by the business (e.g. `voiceovers` / `music`)
  - Documents: defined by the business (e.g. `scripts` / `reports`)
- **Do not** have the model pass `group_id` / `index` (if the system auto-assigns them, the platform handles it).
- The `downloadUrl` returned by `download_video` **expires**. Use it within `expiresIn`.
- Document assets from `create_document` / `update_document` use the same storage model as user-uploaded documents: the original file is stored in S3, and `document_contents` stores plain text for `get_document` and context injection (S3 is not read back). Every `create_document` call creates a new asset_id and a new canvas card. `update_document` is PUT semantics: it refreshes the same card in place for the given existing `asset_id` and does not create a new card. Use `update_document` to edit an existing document and `create_document` to create one. Both `content` fields have a length cap (default `200000` characters; see `create_document.max_content_chars` / `update_document.max_content_chars` in `plugins/documents/config.yaml`). Over the cap, the tool returns `success: false`. Split larger content into multiple documents.

#### Hiding intermediate outputs (frontmatter `canvas:`)

Outputs are added to the canvas by default and appear as asset cards in the conversation. If the flow has intermediate outputs the user should not see (a grid image waiting to be cut, clips waiting to be mixed, and so on), declare a `canvas:` block in the frontmatter:

```yaml
---
name: my-skill
description: ...
canvas:
  model_control: true                       # let the model decide visibility per call
  hidden_tools: [split_image]               # outputs of this tool are never shown
  hidden_entity_types: [work_in_progress]   # outputs of this entity_type are never shown
---
```

- All three fields are optional. `hidden_*` alone is rule-based and invisible to the model. `model_control: true` alone leaves every call to the model, following the body's conventions. Both may be used together (when the model does not pass an explicit value, the `hidden_*` rules apply).
- When `model_control: true`, asset-producing tools gain an optional parameter **`add_to_canvas` (default true)**. The body must hardcode which step passes `false`, for example: "when generating the grid image that will be cut, call `generate_image` with `add_to_canvas=false`; show the cut results (tiles) normally".
- Hide semantics: do not emit canvas or conversation asset cards, and add the asset to canvas `hidden_ids`. **The output is still billed and still enters the asset library. Its URL can still be used as input to later tools.** Hiding only affects display.
- Rules apply as the **union of every Skill mounted for the current turn**: if one Skill hides an `entity_type`, outputs of that same `entity_type` from other Skills in the turn are hidden too. Choose `entity_type` names with that in mind.
- A workflow-level `add_to_canvas: false` (in `orchestrator_config`) is still the master switch and outranks everything above.

### 6.3 Choosing a generation channel (preferred)

The platform exposes stable **model channels** for image, video, voice, music, and similar generation. In the body, Skill authors should set a generation tool's `model=` to a **channel** (optionally with a variant suffix). **Do not** hardcode a physical model name (such as `rm3.1-G` or `qwen-image`). When a model is upgraded, operations switches the underlying model through the channel binding, and the Skill does not need to be republished.

> Authoritative catalog: `examples/skill_creator/skills/skill-creator/references/available-models.md` (skill-creator reads it at runtime with `read_skill_file`). Use that table while drafting. `list_models` is only a fallback check. It cannot replace the catalog, and it is not a license to invent a channel from memory.

**Concepts:**

- **channel:** a stable modality id, such as `t2i`, `i2v`, `ref2v`, `tts.design`. The Skill body writes the channel.
- **variant suffix:** selects a tagged binding, such as `t2i.hd` or `i2i.hd.lite` (suffixes can be combined; the longest prefix channel match wins).
- **bare channel** (such as `i2v`): uses the current **default** binding.
- **physical model name:** still resolves (for old Skills), but **new Skills must not write one**.

**Common channels** (full notes and constraints are in `available-models.md`):

| Channel / variant | Tool | Modality / when to use |
|---|---|---|
| `t2i` / `t2i.hd` / `t2i.hd.lite` | `generate_image` | Text-to-image. `.hd*` is higher quality and **does not support NSFW** |
| `i2i` / `i2i.hd` / `i2i.hd.lite` | `generate_image` | Image-to-image (a reference image is present). Prefer `.hd` / `.hd.lite` for grid storyboards. `.hd*` **does not support NSFW** |
| `i2v` | `generate_video` | Image-to-video (**video generation does not support NSFW/adult content, with no channel exception**) |
| `fl2v` | `generate_video` | First-and-last-frame to video (`input_urls` is the first frame plus the last frame) |
| `ai2v` | `generate_video` | Image + audio-driven video |
| `t2v` | `generate_video` | General text-to-video / image-to-video. When `model='t2v'` is passed explicitly, `input_urls` may be empty (pure text-to-video) |
| `ref2v` | `generate_video` | Reference-to-video (keeps character consistency). The modality is decided by the channel directly; **do not** also pass `gen_mode`. At least 1 reference image. Optional `audio_url` and `orientation`. **The default channel when `model` is omitted** |
| `clip-mixer` | `mix_clips` | Concatenate and mix multiple clips, optionally burning whole-sentence hard subtitles per clip (a compositing channel, not a generation model) |
| `caption` | `caption_video` | Word-by-word highlight captions. **Skills must not pass `model`:** the tool has no such parameter; the platform uses channel `caption` internally. See 6.4 for how to write the call |
| `tts.design` / `tts.clone` | `generate_tts` | The modality is decided by the channel directly; **do not** also pass `mode`. `tts.design` is voice design (needs `voice_instruction`); `tts.clone` is voice clone (needs `reference_audio_url`) |
| `music` | `generate_music` | Text-to-music |
| `asr` | `transcribe_audio` | Speech transcription |

**Selection rules (when writing them into a Skill body):**

1. Decide the modality from the user's intent (text-to-image / image-to-image / image-to-video / first-and-last-frame / audio-driven / reference-to-video / Director / voiceover / music / concatenation / word-by-word highlight captions).
2. After choosing the tool, **hardcode** `model=<channel>` in the step, plus the required input conventions (`input_urls`, `mode`, `audio_url`, `voice_instruction`, and so on). Use a suffix when a tagged binding is needed (for example `model='t2i.hd'`).
3. Image-to-video: always use `i2v`. Video generation does not support NSFW/adult content, and there is no tagged variant for it.
4. Reference-to-video: pass `model='ref2v'` (the modality is fully determined by the channel; **do not** also pass `gen_mode`). At least 1 reference image. If audio drive is also needed, pass `audio_url` separately (optional `audio_start_time`). Do not put the audio URL in `input_urls`.
5. **Do not** write a physical model name in a new Skill. `generate_video` rejects concrete model names outright (the error tells you to use a channel). Do not rely on a downstream `list_models` call to guess the channel.

Body examples:

```markdown
- Text-to-image: `generate_image(prompt=..., model='t2i', name=..., entity_type='storyboard_images')`
- Image-to-video (standard): `generate_video(prompt=..., input_urls=[still], model='i2v', ...)`
- Reference-to-video: `generate_video(..., model='ref2v', orientation='portrait')`
```

> The channel here (`model='i2v'` and similar) is a parameter of the **generation tool**. It has nothing to do with which model the conversation LLM itself uses. Skills can no longer declare a conversation LLM tier.

### 6.4 Parameter-writing tips

In the Skill body or in references, state business defaults as "required / optional / default". For example:

```markdown
- Short dramas default to `orientation='portrait'` unless the user explicitly asks for landscape. Omit `resolution` when there is no special requirement (the default `720P` is used).
- Write image and video prompts in English. Keep dialogue in the user's language.
- Image-to-video: put the storyboard still URL in `input_urls` (the first image is the first frame). `model='i2v'` (video generation does not support NSFW/adult content).
- For `mix_clips`, prefer an asset_id of an asset already generated in this conversation for `clips[].video(s)/audio(s).url` and `clips[].subtitles.url` (`s3://` and real https also work). Do not invent a reference that does not exist. Subtitles are whole-sentence hard subtitles burned into the picture. Use exactly one of `subtitles.url` and `subtitles.items`. Timestamps are relative to that clip's output start. For Chinese, use `style.font_name='Noto Sans CJK SC'`.
- Word-by-word highlight (the TikTok / Reels style where each word changes color) uses `caption_video`. Do not use `mix_clips` `subtitles`, and do not stuff an SRT from `transcribe_audio` into `words`. Do not pass `model` or `words`. Hardcode a known `template` in the body (default `hormozi`; prefer the top 5: `mega-stroke`, `cloud-glow`, `sunset-panel`, `italic-heavy-stroke`, `ink-on-white`). Success returns only the new MP4, not word-level timing. This step can take from the teens of minutes up to more than twenty. Do not write the body as if it finishes instantly, and do not have the model poll.
```

Do not copy an entire tool JSON Schema into the Skill. Write only the fields and value conventions this business cares about. The model can still see the tool's function-calling schema.

> **Size parameters: `orientation` + `resolution` (the only two exposed size parameters).** `generate_image` / `generate_video` accept only these two size-related enums. They do not accept free-form pixel `width` / `height`:
> - `orientation`: `landscape` (16:9) / `portrait` (9:16) / `square` (1:1; supported only by `generate_image` and some video models; unsupported models fall back to landscape)
> - `resolution`: `480P` / `720P` (default) / `1080P` / `2K` / `4K`. A given model's real ceiling may be lower; a value above it is dropped to the highest tier that model supports
>
> The Skill body only needs to set `orientation` for the business (and `resolution` when needed). Do not invent pixel sizes in the body, and do not use the old three-tier `'1K'` / `'2K'` / `'4K'` spelling (images now use the five tiers above). `resolution_model` (an aspect-ratio string such as `'9:16'`) is a legacy advanced override. Only a few `generate_video` channels, such as `ref2v`, still pass it through. New Skills should express direction with `orientation`.
>
> **Exact-ratio override: `aspect_ratio` (uncommon; pass it only when the user explicitly asks).** `orientation` covers only the three main ratios (16:9 / 9:16 / 1:1). If the user explicitly asks for a nonstandard ratio such as `3:4` or `4:3`, you may pass `aspect_ratio='3:4'` (it overrides `orientation`; everything else still aligns the short side to the `resolution` tier). This is an advanced escape hatch. Most cases do not need it. Do not hardcode it as a default parameter in the Skill body.

> **Parameter bounds (platform clamping).** `resolution` and `duration` have platform ceilings (`max_resolution` is an area ceiling, `max_duration` is a duration ceiling; per-model/channel cloud config plus a global fallback). `batch_size` is locked to 1 (generating multiple images in one call is not available). The Skill body **must not** hardcode an over-long duration or a batch size greater than 1. Out-of-range parameters (including a `resolution` beyond the model's capability) are clamped or stepped down automatically before the tool runs, and the tool result explains that in `param_adjustments`. When `orientation` / `resolution` are omitted, the cloud channel config or the platform default tier is used (`landscape` + `720P`).

---

## 7. Always-available tools

`read_skill` / `read_skill_file` / `write_todos` / `set_guidance` do **not** need to be listed in `allowed-tools` (listing them is harmless). The orchestrator always injects them (`set_guidance` depends on `suggested_questions`). **Exception:** the `memory_*` / `skill_kb_query` tools in section 7.4 are not in this set. A Skill must declare them explicitly in `allowed-tools` before they can be used. See that section.

### 7.1 `read_skill` / `read_skill_file`

- When a Skill is relevant, call `read_skill(name)` first, then follow the body.
- When the body mentions `reference_files` and you need the detail, then call `read_skill_file(name, path)`.
- **Do not** guess a Skill's steps before reading it.

### 7.2 `write_todos` (multi-step progress)

Replaces the whole table (it is not a merge). It follows the TodoWrite contract:

```json
{
  "todos": [
    {"id": "script", "content": "Write the script", "status": "in_progress"},
    {"id": "visual", "content": "Visual design", "status": "pending"},
    {"id": "storyboard", "content": "Storyboard images", "status": "pending"}
  ]
}
```

Rules:

- Each item: `content` is required; `status` is `pending` | `in_progress` | `completed`; `id` is optional.
- **At most one item may be `in_progress` at a time.**
- When advancing, call again and pass the **full list**.
- Simple Q&A does not need a call. An empty array clears the progress bar.
- At most 20 items.

In a multi-stage Skill's "collaboration principles", explicitly require the model to use this tool.

### 7.3 `set_guidance` (recommended-action buttons)

Call it in the **same turn as the final reply text**, and offer the next actions:

```json
{
  "suggested_questions": [
    {"text": "Start designing character and location visuals"},
    {"text": "Revise this scene"}
  ]
}
```

A bare string is also valid (equivalent to `{"text": "..."}`). **There is no product-level rule for how many items to return.** The tool only applies an engineering safety truncation so a runaway output cannot blow up the client render. That truncation is not a product cap. Return a sensible count for the current situation. Do not pad the list or force it up to some number, and avoid near-duplicate options.

A full object may include the following (the client already supports every field):

| Field | Type | Required | Notes |
|---|---|---|---|
| `text` | string | Yes | Button label. Emoji is fine |
| `id` | string | No | Stable id for client analytics and dedup. Must not repeat within the same session |
| `icon` | string | No | Icon key. When omitted or null, the client uses the default icon |
| `action` | object | No | When omitted, equivalent to `{"type": "send_message"}` |

`action` expands by `type`:

| `action.type` | Behavior | Extra fields |
|---|---|---|
| `send_message` (default) | Send text directly in the **current conversation** | `content` (optional; defaults to the outer `text`) |
| `fill_input` | Fill the **current conversation** input box without sending | `content` (required, the text placed in the input); `replace` (optional boolean, default `true`; `true` replaces the current contents, `false` appends) |
| `new_conversation` | Open a **new conversation**, optionally carrying content | `content` (optional; omit it to open a blank new conversation); `mode` (optional `send`\|`prefill`, default `prefill`; `send` sends immediately after entering the new conversation, `prefill` only fills the new conversation's input); `template_id` (optional template or route id; the client picks a template or navigates from it) |

Writing requirements:

- Recommended actions must relate to the **current stage or output**. Avoid generic "anything else I can help with".
- You may skip the call when you are advancing continuously and have not stopped at a stage boundary.
- The turn that calls this tool must not call any other tool.
- For fuller writing examples (a concrete use of each `action.type`), see `examples/skill_creator/skills/skill-creator/references/guidance-rules.md`.

### 7.4 Long-term memory (`memory_*` / `skill_kb_query`; must be declared in `allowed-tools`)

**Unlike the rest of this section, these 5 tools are not always available.** The model can call them only when a Skill that declares the corresponding tool name in `allowed-tools` is mounted on the session. Official Skills are not limited by the user tool ceiling. User-authored Skills need the ceiling to allow these tool names (allowed by default; see section 8).

There are two data sources, **searched by two separate tools and never merged**: user-level long-term memory (preferences, facts, project background, and relationships kept across sessions) and a skill-level shared knowledge base (product docs and FAQs uploaded by the business or operator). There is deliberately no design that "merges both into one call". The LLM distinguishes the source by **which tool it calls**, not by reading a flag inside the result. That avoids treating knowledge-base content as something the user said, or the reverse. The orchestrator injects the general convention into the system prompt. When you need a **domain-specific read/write policy** (what small talk should remember, which knowledge base customer support should query), add it in the Skill body. See `examples/skill_demo/skills/chat_memory/` and `examples/customer_service/skills/customer-service/`.

| Tool | Purpose | Parameters |
|---|---|---|
| `memory_whoami` | Read the identity summary (a cheap baseline at the start of a session) | none |
| `memory_query` | Semantically search **the user's own** personal memories. Includes no skill shared-knowledge-base content | `query` (required); optional `kind`, `limit` |
| `skill_kb_query` | Semantically search the shared knowledge base of **skills mounted on the current session**. Includes no personal user memory. Returns an empty result when no mounted skill provides a knowledge base | `query` (required); optional `kind`, `limit` |
| `memory_store` | Write a fact or preference that is valuable across sessions (writes personal user memory only; cannot write the shared knowledge base) | `content` (required); optional `kind`, `tags`, `namespace`, `sensitivity` |
| `memory_forget` | Soft-delete one personal user memory | `memory_id` (the `id` returned by `memory_query`) |

**Three layers of data:**

| | Identity summary (whoami) | Personal user memory (query / store / forget) | Skill shared knowledge base (`skill_kb_query`) |
|---|---|---|---|
| Storage | One `summary` row per user | Many structured entries, plus an optional embedding | Many structured entries (often document chunks) |
| Agent | **Read-only** via `memory_whoami` | Read/write via `memory_query` / `store` / `forget` | **Read-only** via `skill_kb_query` |
| Writes | REST `PUT /memories/identity`. When the summary is empty, recording facts with `memory_store` is enough | Agent-side `memory_store`, or REST `/api/v1/memories` | Skill owner only, via document upload or REST `/api/v1/skills/{skill_id}/kb` |

`kind` values: `fact` / `preference` / `project` / `person` / `episode`.  
`sensitivity`: `normal` (default) / `private`.  
`namespace` (settable only on `memory_store`) defaults to `default` and can isolate data by business. `memory_query` and `skill_kb_query` neither accept nor need `namespace`; each tool's search scope is fixed by the tool itself.

**Recommended usage (write this into the steps of a Skill that depends on memory):**

1. **Opening:** at the start of a new conversation, or when the other person's background is unclear, call `memory_whoami` first. If a summary exists, fold it naturally into tone and how you address them. Do not recite it mechanically.
2. **Retrieve before answering:** when the question involves user preferences, projects, people, or past decisions, call `memory_query` first. When it involves a product knowledge base, FAQ, or document content, use `skill_kb_query` instead. Pick one of the two from the question type. Do not mix them or guess. Rely only on the returned `items`. If nothing hits, say so plainly. Do not invent.
3. **Write:** as soon as the user reveals or confirms information that is **still valuable across sessions**, call `memory_store`. One clear declarative sentence is enough. Highly similar content may be merged automatically (`deduped=true`).
4. **Forget or correct:** for "forget…" or something you find outdated, call `memory_query` to get the `id`, then `memory_forget`. Treat what the user says in the moment as the source of truth. This applies only to personal user memory. The skill owner adds and removes shared knowledge-base entries through REST.

**What to remember / what not to remember** (`memory_store` only, i.e. personal user memory):

- **Remember:** how they want to be addressed and tone preferences, stable interests or style, long-running project settings, important relationships, and decisions the user explicitly asked you to remember.
- **Do not remember:** one-off task progress, temporary drafts, intermediate tool results, sensitive credentials such as passwords, keys, and verification codes, unconfirmed guesses, and encyclopedia facts that are not about the user.

**Notes when writing a Skill:**

- Memory tools are **not** always available. Declare each one you need in `allowed-tools` (if you only need personal memory, you do not need to declare `skill_kb_query`).
- Do not assume in the body that "the system will remember automatically". Reads and writes must go through the tools.
- After a recall, refer to it in natural language ("Last time you said you preferred…" / "According to the knowledge base…"). Do not paste raw JSON or a memory id to the user.
- `memory_store` / `memory_query` / `skill_kb_query` call an embedding model internally. If embedding fails, they fall back to keyword search. The Skill should still treat "no result" as "do not invent".

**REST admin APIs are grouped strictly by data ownership and do not share one set of routes** (the same split as the two independent agent-side tools above):

| Data ownership | REST prefix | Purpose |
|---|---|---|
| Personal user memory | `/api/v1/memories` (`GET`/`POST` list and create, `DELETE` clear all, `GET`/`PUT`/`DELETE /{memory_id}`, `POST /query` semantic search, `GET`/`PUT /identity`) | The user views, edits, and deletes their own memory entries |
| Skill shared-knowledge-base chunks | `/api/v1/skills/{skill_id}/kb` (`GET`/`POST /entries`, `PUT`/`DELETE /entries/{memory_id}`, `POST /query`) | The skill owner manually adds, revises, or searches knowledge-base chunks outside document import (`kb-documents`) |

Both groups require `X-User-Id`. The skill KB group also checks that the current user is that skill's owner, and on update or delete it checks that the target chunk really belongs to that `skill_id`'s namespace. One system user holds the shared knowledge base of every skill, so filtering by owner alone is not enough to prevent cross-skill access.

---

## 8. User Skill limits (ceiling)

Official Skills may declare a wider tool set. The `allowed-tools` of a **user-authored Skill** is intersected with the server ceiling. The default ceiling (`config/config.yaml` → `skills.user_authored.allowed_tools`) is:

- `search_web`
- `generate_image`
- `generate_video`
- `generate_tts`
- `generate_music`
- `mix_clips`
- `caption_video`
- `list_models`
- `search_library`
- `get_library_item`
- `split_image`
- `extract_clip`
- `extract_frame`
- `extract_audio`
- `recognize_image`
- `recognize_video`
- `transcribe_audio`
- `fetch_video_info`
- `download_video`
- `create_document`
- `update_document`
- `get_document`
- `memory_whoami`
- `memory_query`
- `skill_kb_query`
- `memory_store`
- `memory_forget`

The Skill authoring tools `list_my_skills` / `read_my_skill` / `read_my_skill_file` / `write_skill_draft` / `write_skill_reference_file` / `publish_skill` / `bind_skill_preset_asset` / `unbind_skill_preset_asset` are **outside the ceiling and will never be added to it**. A user Skill cannot declare them. Only an official Skill (such as `skill-creator`) can use them (see section 9).

There are also count limits (configurable):

- `max_body_chars` (default 50000)
- `max_reference_files` (default 15)
- `max_per_user` (default 50)
- `skills.preset_assets.max_count` (default 10)

When writing a Skill for users or the marketplace, **do not** declare tools outside the ceiling. They are filtered out and are unavailable to the model.

---

## 9. Skill authoring tools (skill-creator, official Skills only)

The Skill Agent can help a user create, edit, and publish their own Skill inside a conversation, through dedicated authoring tools. **These tools are outside the `skills.user_authored.allowed_tools` ceiling. Only an official Skill can declare them in `allowed-tools`.** Otherwise a user Skill could create further Skills and bypass every quota and permission control. The full reference implementation is `examples/skill_creator/` (`skills/skill-creator/SKILL.md` + `references/skill-writing-guide.md` + `references/available-models.md`).

| Tool | Role |
|---|---|
| `list_my_skills` | List every Skill the current user authored (including unpublished drafts). Returns `skill_id` / `name` / `display_name` / `description` / `enabled` / `has_draft` / `allowed_tools` |
| `read_my_skill` | Read the full content of one user-authored Skill by `skill_id` (the draft is preferred when one exists). Restored as full SKILL.md text (`skill_md`) + a **name list** of reference files (not their full text) + `preset_assets` |
| `read_my_skill_file` | Read the full text of one reference file in the draft (or the live version if there is no draft) by `skill_id` + `path`. Same family as `read_skill_file`, but it reads the edit view |
| `write_skill_draft` | Save a complete SKILL.md text (plus optional `reference_files`) as a draft. An empty `skill_id` creates a new Skill; a non-empty one overwrites that Skill's draft. **Writes the draft only and does not affect the live version.** Does not overwrite existing `preset_assets`. This is the only write path for the body and frontmatter |
| `write_skill_reference_file` | Add, overwrite, or delete a single reference file in the draft (omit `content` or pass `null` to delete). Does not affect the body or the other reference files. Complements the full-table replace of `write_skill_draft`, and fits single-file add/delete |
| `publish_skill` | Publish the draft as the live version (`enabled=true`) into the user's Skill space (including `preset_assets` from the draft) |
| `bind_skill_preset_asset` | Bind a `asset_id` from a user attachment in this turn onto the skill draft's preset list (`key` / `label`). The asset is referenced publicly |
| `unbind_skill_preset_asset` | Remove one item from the draft preset list (does not delete the underlying assets row) |

### 9.1 Prerequisites

- The workflow that hosts the Skill must be **`skill_agent`** (see section 10). These authoring tools check ownership with `_user_id`, which the orchestrator injects hidden (invisible to the LLM, and the model does not pass it; same injection mechanism as `_scope` on `read_skill`). If `user_id` is missing, the call is rejected with a structured error.
- Only an official Skill (`owner_user_id IS NULL`) can declare these tools. Even if a user-authored Skill writes them into `allowed-tools`, the server ceiling filters them out.

### 9.2 Two-phase draft and publish

This reuses the same `skills.draft` JSONB semantics as official Skill draft/publish:

```
write_skill_draft(skill_md, reference_files?, skill_id?)
        ↓ writes the draft only; does not affect the live version; may be called repeatedly until the user is satisfied
The user explicitly confirms (the body must require: do not call publish_skill without confirmation)
        ↓
publish_skill(skill_id)
        ↓ the draft is written to the main columns + enabled=true, and enters the user space (available starting with the next conversation turn)
```

`write_skill_draft` returns `{skill_id, name, warnings[], preview}`. Read the name, description, and tool allowlist in `preview` back to the user for confirmation. `warnings` lists tools that were stripped because they exceeded the user ceiling (section 8). The body must require those warnings to be reported honestly; do not swallow them. Quota checks (body too long, too many reference files, or over the per-user Skill count) return a structured `error` on failure. Fix according to the message and retry.

To add, change, or delete a single reference file, you do not need a full `write_skill_draft`. Use `write_skill_reference_file(skill_id, path, content?)` (this also writes the draft only). Omitting `content` or passing `null` deletes that file. `path` cannot be `SKILL.md` (the body and frontmatter can go through `write_skill_draft` only). It returns `{skill_id, path, deleted, existed, reference_files}`. Deleting a path that does not exist returns `existed=false` and is not an error, but it also changes nothing.

### 9.3 kebab-case constraint on `name`

The `name` in SKILL.md frontmatter generated by the model must be kebab-case (`xx-xx`; see section 3). The server normalizes it: any non-ASCII letter or digit (including Chinese, underscores, and spaces) is collapsed into a hyphen. If the model lazily writes Chinese or a romanization, normalization can collapse it into a string of meaningless hyphens, or even fall back to `skill`. A skill-creator-style Skill's body and reference files must therefore require explicitly: **compose `name` from English words joined by hyphens**, and put the human-readable name (including non-English text) in `display_name`. Before creating one, call `list_my_skills()` and check that it does not collide with an existing Skill.

### 9.4 Known limits

- The mounted Skill set is resolved once at the start of each conversation turn. After `publish_skill` succeeds, it **does not take effect in the current turn**. The body must tell the user that the new Skill is available starting with the next conversation turn.
- User Skills do not write `skill_revisions` (revision history is archived for official Skills only). After publish there is no historical version to roll back to. The only path is to edit the draft again and overwrite.
- `read_my_skill` / `read_my_skill_file` / `write_skill_draft` / `write_skill_reference_file` / `publish_skill` all check ownership by `(skill_id, owner_user_id)`. The model cannot read, modify, or publish a Skill that does not belong to the current user. An unauthorized call returns a structured `{"success": false, "error": ...}`, not an exception.
- Both `write_skill_reference_file` and `write_skill_draft` do "read draft → merge in memory → overwrite the whole `draft` JSONB". Two concurrent calls overwrite each other (the later writer is based on a stale snapshot). There is no optimistic lock. The chance is low in the current single-session interaction, and that is acceptable.

---

## 10. orchestrator_config (optional)

The orchestrator config for a `skill_agent` workflow is light, and it is **not** part of the Skill body. Skills are always resolved dynamically by `user_id` (built-in + mine + installed + `/` forced mounts). `skills` and `skill_scope`, if present, are ignored. See `examples/assistant/orchestrator_config.yaml` and `examples/skill_demo/orchestrator_config.yaml`:

```yaml
orchestrator_name: skill_demo
role_description: "You are an assistant that can call platform tools to complete the user's task."

tools:                    # core tools that can be called directly, without depending on any skill
  - list_models
  - search_library
  - get_library_item

max_iterations: 20
add_to_canvas: true
suggested_questions: true # default true; if off, the model cannot use set_guidance
timezone: UTC             # optional IANA timezone name; default UTC+0 (global users); sets the timezone of the current time injected to the model
```

> **Current time:** each user message (the tail of the HumanMessage) automatically gets one line with the current time (timezone and UTC offset). The model can tell what time it is without calling a tool. Time is per-turn volatile data, so under the prefix-cache constraint it does **not** appear in the system prompt. When the Skill body needs to judge by time (such as "today" or "this week"), refer to that line directly.

When writing a **single Skill package**, you usually only care about `SKILL.md` + `references/`. Change the YAML above only when creating or adjusting a whole `skill_agent` workflow.

---

## 11. Complete examples

### 11.1 Single-capability Skill (simple)

See `examples/skill_demo/skills/image_generation/SKILL.md`:

- `description` states the user intent (drawing, poster, avatar)
- `allowed-tools`: `list_models`, `generate_image`
- Body: rewrite the prompt → hardcode `model=<channel>` for the modality (e.g. `t2i` / `i2i`) → call the tool → short reply
- No `references/`

Similar: `examples/skill_demo/skills/web_research/SKILL.md`.

Chat / cross-session memory: `examples/skill_demo/skills/chat_memory/SKILL.md` (section 7.4):

- `description` covers "remember / recall / forget" and preferences or identity across an ongoing conversation
- `allowed-tools` must declare the `memory_*` tool names that are used (they are no longer always available; undeclared tools cannot be called)
- Body: whoami → query → store → forget, plus what to remember and what not to remember

### 11.2 Multi-stage Skill (complex)

See `examples/drama_skills/`:

- Root `SKILL.md`: trigger description, tool allowlist, stage table, collaboration principles (continuous advance / partial edit / todos / guidance)
- `references/*.md`: writing, visuals, storyboard images, storyboard video, voiceover, and compositing, with `entity_type` conventions for each stage

When adding a new long-workflow Skill, copy that directory's **information architecture** first, then replace the domain content.

### 11.3 Skill authoring tools (skill-creator)

See `examples/skill_creator/` (section 9):

- `skills/skill-creator/SKILL.md`: `allowed-tools` declares only `list_my_skills` / `read_my_skill` / `write_skill_draft` / `publish_skill`. The body separates the three flows "create", "edit an existing one", and "view", and stresses that the user must confirm before publish. When media generation is involved, it requires reading `available-models.md` first and hardcoding a **channel**
- `references/skill-writing-guide.md`: authoring rules for "a Skill that helps the user write Skills", including the kebab-case naming constraint, the in-ceiling tool list, **channel selection**, and a pre-output checklist
- `references/available-models.md`: the platform channel catalog (authoritative). Hardcode channels while drafting. Physical model names are forbidden
- `orchestrator_config.yaml`: illustrative config, showing how it hangs off a `skill_agent` workflow with dynamic mounting

When writing "a Skill that can create Skills" (a meta Skill), copy that directory structure first and replace it with your own business spec.

---

## 12. AI authoring checklist

After writing or editing a Skill, confirm each item:

- [ ] Valid YAML frontmatter; `name` and `description` are non-empty
- [ ] `description` is a "user-intent trigger condition", not a feature ad or an implementation detail
- [ ] `allowed-tools` contains only tools this Skill actually needs, and they are inside the user ceiling (if the Skill is for users)
- [ ] The body has "When to use / Steps / Notes" (or a multi-stage index plus collaboration principles)
- [ ] Tool names in the steps match `allowed-tools`. Key parameters (`name`, `entity_type`, `orientation`, **`model=<channel>`** on generation steps, and so on) have conventions
- [ ] When media generation is involved: the correct **channel** is bound per section 6.3 (checked against `available-models.md`; no physical model name; video generation does not support NSFW/adult content)
- [ ] Word-by-word highlight captions use `caption_video` (do not pass `model`, do not pass `words`, `template` is a known id) and are listed in `allowed-tools`. Do not substitute `mix_clips` subtitles or an SRT from `transcribe_audio`
- [ ] No `data_schemas` / `operations` / fake JSON state protocol
- [ ] Does not depend on `scripts/` inside the Skill package (it is not parsed or executed)
- [ ] Long content is split into `references/`, and the body says "call `read_skill_file` as needed; do not read everything at once"
- [ ] Multi-step flows require `write_todos`. Stage boundaries and completion require `set_guidance` (when applicable)
- [ ] When the Skill depends on cross-session memory: `allowed-tools` declares the `memory_whoami` / `memory_query` / `memory_store` / `memory_forget` tools that are used (no longer always available), and the steps spell out when to call them and what to remember or not remember. When it depends on a skill shared knowledge base, declare and use `skill_kb_query`, and do not mix it with `memory_query` (see 7.4)
- [ ] Failures must be reported honestly, inventing URLs is forbidden, and prohibited content is refused
- [ ] When there are intermediate outputs, the frontmatter `canvas:` declares hide rules (`hidden_entity_types` / `hidden_tools`), or `model_control` is on and the body hardcodes which steps pass `add_to_canvas=false`
- [ ] For adult or sensitive content: bind an image generation channel as needed (bare `t2i` / `i2i`, not a `.hd*` variant; see 6.3). Video generation does not support NSFW/adult content. Skills can no longer declare a conversation LLM tier
- [ ] The final reply is required to be a natural-language summary, without pasting long URLs
- [ ] The directory can be parsed by `load_skill_from_directory` or a zip upload (`SKILL.md` exists, reference paths are correct)

---

## Appendix: Common mistakes

| Mistake | Correct approach |
|---|---|
| Writing `agents_config.yaml` in the old drama-config style | The Skill Agent uses only a `SKILL.md` package |
| Stuffing the whole workflow into the body | Put stage details in `references/`. Leave only an index in the body |
| Writing `description` as "helps the user create" | State the concrete intent and the boundary cases |
| Requiring in the Skill that "output must be JSON" | Tools use native function calling. Talk to the user in natural language |
| Assuming there is a `characters` collection to update | Write the setting in Markdown, and reference already-generated assets by canvas URL |
| Forgetting to declare `generate_image` while calling it in a step | Keep `allowed-tools` consistent with the steps in the body |
| Hardcoding a physical model name in a generation step (`rm3.1-G`, `qwen-image`, …) | Write a stable **channel** (`i2v`, `t2i`, …). Check `available-models.md` (see 6.3) |
| Using `mix_clips` subtitles or an SRT from `transcribe_audio` for word-by-word highlight | Use `caption_video`: do not pass `model`, do not pass `words`, and hardcode a known `template`. Transcripts still go through `transcribe_audio`. Use `mix_clips` only to concatenate or to burn whole-sentence hard subtitles |
| Using `list_models` on the spot to guess a model instead of the channel catalog | While drafting, `available-models.md` is the source of truth. `list_models` is only a fallback |
| Asking "continue?" between every stage | Advance continuously by default. Stop only when the user asks for confirmation |
| Declaring authoring tools such as `write_skill_draft` / `publish_skill` in a user Skill | Only official Skills may declare them. They are outside the user ceiling (see section 9). Otherwise a user Skill could reproduce itself |
| Assuming the system automatically remembers user preferences | You must use `memory_store` / `memory_query`. The identity summary comes from whoami (see 7.4) |
| Expecting `memory_query` to find skill knowledge-base content | Personal memory and the shared knowledge base are two separate tools. `memory_query` searches personal memory only. Knowledge-base content uses `skill_kb_query` (see 7.4) |
| Using `memory_*` / `skill_kb_query` without listing them in `allowed-tools` | These 5 tools are no longer always available. They must be declared explicitly before they can be mounted and called (see 7.4) |
| Expecting a new Skill to be usable in the current turn after `publish_skill` succeeds | The mounted Skill set is resolved once at the start of each turn. The new Skill takes effect starting with the next conversation turn (see 9.4) |
| Allowing Chinese or underscores in `name` inside a skill-creator-style Skill | `name` must be kebab-case. Non-ASCII characters are normalized and collapsed. The body must require English words plus hyphens (see 9.3) |
