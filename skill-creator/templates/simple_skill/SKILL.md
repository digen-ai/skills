---
name: image-generation
display_name: Image Generation
description: Use when the user wants to generate, draw, or create an image (illustration, poster, avatar, scene, etc.)
allowed-tools:
  - list_models
  - generate_image
---

# Image Generation

Generate one image from the user's description. No structured project state; one conversation is enough.

## When to use

- The user explicitly asks to draw / generate an illustration, poster, avatar, or scene
- The user uploads a reference image and asks to "generate another in this style" (image-to-image)

## Steps

1. Rewrite the user's description into a clear English prompt, keeping the key subject, style, and composition.
2. If there is no reference image: call `generate_image(prompt=..., model='t2i', name=<short title>, entity_type='storyboard_images')`.
   If there is a reference image: call `generate_image(prompt=..., input_urls=[reference URL], model='i2i', ...)`.
3. Unless the user explicitly asks for landscape or square, omit `orientation` (use the platform default).
4. After success, reply in a sentence or two of natural language. Do not paste long URLs (outputs land on the canvas automatically).

## Notes

- If the tool returns `success=false`, report the failure honestly. Do not pretend it succeeded or invent image URLs.
- Politely refuse violent/sexual requests; do not call the generation tool.
- Do not invent pixel dimensions in the body. Size is only `orientation` (`landscape`/`portrait`/`square`) plus optional `resolution`.
