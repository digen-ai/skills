# Stage 2: Visuals and voice

After the script is locked, produce character/scene visuals, storyboard, voiceover, and mix in order. You may do only one of these steps if the user asks.

## When to use

- The script is confirmed and the user asks to "start making images", "generate a storyboard", "add a voiceover", or "mix it"

## Steps

### 1. Character / scene visuals

- Generate one reference image per main character / key location: `generate_image(prompt=<English description>, model='t2i', name=<character or location name>, entity_type='characters'|'locations')`.
- Keep the prompt in English and preserve key appearance details so later storyboard frames stay consistent.

### 2. Storyboard

- Pick 1–2 key shots per scene and generate stills from the matching character/location reference: `generate_image(prompt=..., input_urls=[reference image], model='i2i', name=<shot title>, entity_type='storyboard_images')`.
- If storyboard video is needed: `generate_video(prompt=..., input_urls=[still], model='i2v', name=..., entity_type='storyboard_videos')`.

### 3. Voiceover

- Generate voiceover from scene dialogue: `generate_tts(text=<dialogue>, mode='design', voice_instruction=<voice description>, name=<character name>, entity_type='voiceovers')`.
- Reuse a consistent `voice_instruction` for the same character across scenes. Do not call `mode='clone'` unless voice cloning is requested.

### 4. Mix

- Once assets are ready, stitch storyboard video with voiceover via `mix_clips`: `mix_clips(clips=[{video: ..., audio: ...}, ...], name=<final title>, entity_type='final_videos', orientation='portrait')`.
- `mix_clips` may only use real URLs generated in this conversation or provided by the user. Never invent them.

## Notes

- Before each generation, briefly say what you are about to do. After it finishes, confirm the result in one sentence. Do not write long essays.
- If the user asks to tweak one step (style / voice), redo only that step, not the whole pipeline.
- When everything is done, call `set_guidance` with next-step suggestions such as "export / tweak one stage".
