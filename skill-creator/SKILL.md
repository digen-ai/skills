---
name: skill-creator
description: Use this skill when the user wants to create, edit, validate, or publish their own Digen skill (personal skill space / marketplace listing). Trigger examples include: "help me write a skill", "digenskill", "publish to the marketplace", "skill validation failed", "allowed-tools error", "my skill space", "install/uninstall a marketplace skill", "skill-creator", or mentions of user-side SKILL.md authoring, `~/.digen/skills`, or personal skill listing review.
version: 1.0.0
---

# Digen user skill authoring kit

Helps **regular users** (not Digen platform operators) create, edit, validate, and upload their own skills: local SKILL.md → validate → pack and upload → publish a marketplace listing from the web UI.

> **SKILL_DIR**: directory where this skill is installed (e.g. `~/.digen-skills-repo/skill-creator` or the corresponding path in a plugin cache)
>
> This is a **completely different** system from official `skill-dev` (for Digen operators, editing admin-side builtin/official skills). This skill only talks to the user-facing API (`/api/v1/skills`) and manages **the current user's own** skills (including installing others' skills). Marketplace listing is done on the web UI. Do not use this skill's CLI to edit builtin/official skills, and do not confuse the `skill` command (admin CLI) with `digenskill` (this CLI).

---

## Install

```bash
${SKILL_DIR}/scripts/install.sh
digenskill config set-api https://api.digen.ai   # default; usually no change needed
digenskill login                                  # Google only (default); --token for SSH / paste fallback
```

See `${SKILL_DIR}/docs/01-setup.md`.

---

## Authoring flow

> ⚠️ **Hard constraint**: the recommended way to edit a user skill is `digenskill checkout` (pull an existing skill in full) or `digenskill init` (new template) → local edit → `digenskill validate` → `digenskill push` (zip upload, create or write a draft) → publish from the web UI (request a marketplace listing). Do not invent REST endpoints or hand-assemble JSON requests. There is no `digenskill publish`.

### Step 1: Init / Checkout

```bash
digenskill list                                  # my space (builtin + self-authored + installed)
digenskill init my-skill -d "Use when the user wants to…"     # local template (not uploaded yet)
digenskill checkout <skill_id>                   # check out an existing skill (draft layered on automatically)
digenskill checkout <skill_id> --as fix-desc      # custom directory suffix
```

Workspace: `~/.digen/skills/<name>-<suffix>/`, with automatic `git init` + baseline commit.

See `${SKILL_DIR}/docs/02-create.md`.

### Step 2: Edit

> 🔴 **Read `${SKILL_DIR}/SKILL_GUIDE.md` before you start**: progressive disclosure, how to write `description`, the user `allowed-tools` ceiling, kebab-case `name` rules, and how to organize `references/` are all there.

You can edit:

- `SKILL.md` — frontmatter (`name` / `description` / `display_name` / `allowed-tools` / `model`) + body
- `references/**` — multi-stage details (the model reads them on demand via `read_skill_file`)

**Do not** declare authoring tools reserved for official skills (`write_skill_draft` / `publish_skill`, etc.; see `SKILL_GUIDE.md` section 8), and **do not** depend on `scripts/` (they are not parsed or executed).

See `${SKILL_DIR}/docs/03-edit.md`.

### Step 3: Validate

```bash
digenskill validate [path]
```

Local checks for frontmatter, `description` trigger wording, body structure, reference paths, and out-of-ceiling tools. Passing validation does not mean the server will accept the skill (the server still runs a security scan + ceiling intersection), but it catches most low-level mistakes early.

See `${SKILL_DIR}/docs/03-edit.md`.

### Step 4: Upload (draft)

```bash
digenskill push [path]                # first time: POST /import-zip to create (private); if .digen-skill-id exists: PUT to overwrite draft
digenskill push [path] --id <skill_id>  # write a draft for an existing skill
```

Newly created skills default to `private` and are not listed on the marketplace automatically.

See `${SKILL_DIR}/docs/04-publish.md`.

### Step 5: Request a marketplace listing (web)

Publishing is **not** a CLI command. After `push`, open the Digen web UI (`https://agent.digen.ai` by default, or the URL from `digenskill config show`) and request a listing there (cover / category / sample video live on the web form).

```bash
digenskill info <skill_id>             # inspect status / review_status
digenskill unpublish <skill_id>        # revoke public listing; make private (immediate)
digenskill cancel-review <skill_id>    # withdraw an in-review request (not the same as unpublish)
```

First request: auto-approved → listed immediately (`status=published`); needs human review → `status=in_review`. After it is listed, submitting a content update keeps the previous approved version on the marketplace until the new version is approved.

See `${SKILL_DIR}/docs/04-publish.md`.

### Step 6 (optional): Browse the marketplace / install others' skills

```bash
digenskill market --tab discover           # browse the marketplace
digenskill market-categories               # list category enums
digenskill install <skill_id>              # install someone else's public skill (reference; body is not copied)
digenskill fork <skill_id>                 # fork into your own private copy (then edit and publish on the web)
digenskill favorite <skill_id>             # favorite
```

See `${SKILL_DIR}/docs/05-market.md`.

---

## Command cheat sheet

| Command | Description |
|---------|-------------|
| `digenskill login` / `logout` / `whoami` / `config *` | Auth and config |
| `digenskill list` / `info <id>` / `export <id>` | My space / details / download zip |
| `digenskill init <name>` / `checkout <id>` | New template / check out locally |
| `digenskill validate [path]` | Local validation |
| `digenskill push [path] [--id]` | Pack and upload (create or write a draft) |
| `digenskill unpublish <id>` / `cancel-review <id>` | Make private / withdraw review (listing is requested on the web) |
| `digenskill delete <id>` / `toggle <id> on\|off` | Delete / personal enable-disable |
| `digenskill market [--tab --category --q --sort]` / `market-categories` | Browse the marketplace |
| `digenskill install <id>` / `uninstall <id>` / `fork <id>` / `favorite <id>` | Install / uninstall / fork / favorite |

---

## Troubleshooting

See `${SKILL_DIR}/docs/06-troubleshooting.md`.

Common cases: API returns 401 → run `digenskill login` again (or `config set-user <id>` to fill in user_id); `digenskill validate` errors → use the checklist at the end of `SKILL_GUIDE.md`; `allowed-tools` stripped after `push` → you declared tools outside the user ceiling, see `SKILL_GUIDE.md` section 8.
