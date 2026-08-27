---
name: short-story-studio
display_name: Short Story Studio
description: Use when the user wants a full visual presentation of a short story (from a one-line idea to a finished piece: script, character/scene visuals, storyboard, voiceover); also use when they only want to advance or edit one of those stages
allowed-tools:
  - list_models
  - generate_image
  - generate_video
  - generate_tts
  - mix_clips
---

# Short Story Studio

Start from a one-line idea and finish script, visual design, storyboard, voiceover, and mix in stages. **There is no structured project state**: progress lives in conversation history + assets already on the canvas + `write_todos`.

## Production stages (references/)

Detailed steps for each stage live under `references/`. **Do not read them all at once**: decide which stage you are in, then `read_skill_file` only that one file.

| Stage | File | Tools | When to read |
|-------|------|-------|--------------|
| 1. Script | `references/stage-a-script.md` | none | user gives an idea, or wants to edit the script/outline |
| 2. Visuals and voice | `references/stage-b-visuals.md` | `generate_image`, `generate_video`, `generate_tts`, `mix_clips` | script is locked; need character/scene images, storyboard video, voiceover, mix |

## Collaboration

- User says "generate it all" / "just finish it": advance in table order. After each stage, briefly sync progress, then immediately read the next stage. **Do not keep asking for confirmation between stages**.
- User only wants one step changed (e.g. "change the voice style"): read only that stage file; do not redo the whole pipeline.
- Stop and wait only when the user explicitly says "wait" / "let me look".
- Call `write_todos` with the stage list when entering a multi-stage flow; call `set_guidance` at stage boundaries or when everything is done.

## Notes

- If a generation tool fails, say so honestly. Do not pretend success or invent asset URLs.
- Politely refuse violent/sexual requests.
- Summarize outputs in natural language. Do not paste long URLs (outputs land on the canvas automatically).
