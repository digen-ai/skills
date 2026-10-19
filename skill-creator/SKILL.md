---
name: skill-creator
description: Use this skill when the user wants to create, edit, validate, or publish their own Digen skill (personal skill space / marketplace listing). Trigger examples include: "help me write a skill", "digen skill", "publish to the marketplace", "skill validation failed", "allowed-tools error", "my skill space", "install/uninstall a marketplace skill", "skill-creator", or mentions of user-side SKILL.md authoring, `~/.digen/skills`, or personal skill listing review.
version: 1.0.0
---

# Digen user skill authoring kit

Helps **regular users** (not Digen platform operators) create, edit, validate, and upload their own skills: local SKILL.md → validate → pack and upload → publish a marketplace listing from the CLI or web UI.

> **SKILL_DIR**: directory where this skill is installed (e.g. `~/.digen-skills-repo/skill-creator` or the corresponding path in a plugin cache)
>
> This is a **completely different** system from official `skill-dev` (for Digen operators, editing admin-side builtin/official skills). This skill only talks to the user-facing API (`/api/v1/skills`) and manages **the current user's own** skills (including installing others' skills). Marketplace listing can be requested from the CLI or the web UI. Do not use this skill's CLI to edit builtin/official skills, and do not confuse the `skill` command (admin CLI) with `digen skill` (this CLI).

---

## Install

```bash
${SKILL_DIR}/scripts/install.sh
digen config set-api https://api.digen.ai   # default; usually no change needed
digen login                                  # Google only (default); --token for SSH / paste fallback
```

See `${SKILL_DIR}/docs/01-setup.md`.

---

## Authoring flow

> ⚠️ **Hard constraint**: the recommended way to edit a user skill is `digen skill checkout` (pull an existing skill in full) or `digen skill init` (new template) → local edit → `digen skill validate` → `digen skill push` (zip upload, create new or overwrite an existing skill — takes effect immediately, there is no draft stage) → `digen skill publish` (or the web UI for rich listing fields). Do not invent REST endpoints or hand-assemble JSON requests.

### Step 1: Init / Checkout

```bash
digen skill list                                  # my space (builtin + self-authored + installed)
digen skill init my-skill -d "Use when the user wants to…"     # local template (not uploaded yet)
digen skill checkout <skill_id>                   # check out an existing skill (pulls the current live content)
digen skill checkout <skill_id> --as fix-desc      # custom directory suffix
```

Workspace: `~/.digen/skills/<name>-<suffix>/`, with automatic `git init` + baseline commit.

See `${SKILL_DIR}/docs/02-create.md`.

### Step 2: Edit

> 🔴 **Read `${SKILL_DIR}/SKILL_GUIDE.md` before you start**: progressive disclosure, how to write `description`, the user `allowed-tools` ceiling, kebab-case `name` rules, and how to organize `references/` are all there.

You can edit:

- `SKILL.md` — frontmatter (`name` / `description` / `display_name` / `allowed-tools` / `model`) + body
- `references/**` — multi-stage details (the model reads them on demand via `read_skill_file`)

**Do not** declare authoring tools reserved for official skills (`write_skill` / `write_skill_reference_file`, etc.; see `SKILL_GUIDE.md` section 8), and **do not** depend on `scripts/` (they are not parsed or executed).

See `${SKILL_DIR}/docs/03-edit.md`.

### Step 3: Validate

```bash
digen skill validate [path]
```

Local checks for frontmatter, `description` trigger wording, body structure, reference paths, and out-of-ceiling tools. Passing validation does not mean the server will accept the skill (the server still runs a security scan + ceiling intersection), but it catches most low-level mistakes early.

See `${SKILL_DIR}/docs/03-edit.md`.

### Step 4: Upload

```bash
digen skill push [path]                # first time: POST /import-zip to create (private); if .digen-skill-id exists: PUT to overwrite the live content
digen skill push [path] --id <skill_id>  # overwrite an existing skill (takes effect immediately)
```

Uploads to an existing skill **overwrite the live content immediately** — there is no draft stage, so only push when the changes are meant to go live for you. (If the skill is listed on the marketplace, installers keep seeing the last approved version until you re-request the listing and it is approved.) Newly created skills default to `private` and are not listed on the marketplace automatically.

See `${SKILL_DIR}/docs/04-publish.md`.

### Step 5: Request a marketplace listing

After `push`, request public visibility. The CLI also supports listing JSON, covers, and sample clips; the web UI remains convenient for filling rich listing fields.

```bash
digen skill publish <skill_id>                         # request public visibility
digen skill publish <skill_id> --file listing.json     # update listing first
digen skill listing <skill_id> --file listing.json     # listing/category/slug/locales only
digen skill cover <skill_id> ./cover.jpg --kind card   # upload + merge cover
digen skill clip <skill_id> ./sample.mp4 --label Demo  # upload + append sample
digen skill info <skill_id>                            # inspect status / review_status
digen skill unpublish <skill_id>                       # revoke public listing; make private (immediate)
digen skill cancel-review <skill_id>                   # withdraw an in-review request (not the same as unpublish)
```

First request: auto-approved → listed immediately (`status=published`); needs human review → `status=in_review`. After it is listed, submitting a content update keeps the previous approved version on the marketplace until the new version is approved.

See `${SKILL_DIR}/docs/04-publish.md`.

### Step 6 (optional): Browse the marketplace / install others' skills

```bash
digen skill market --tab discover           # browse the marketplace
digen skill categories               # list category enums
digen skill install <skill_id>              # install someone else's public skill (reference; body is not copied)
digen skill fork <skill_id>                 # fork into your own private copy (then edit and publish)
digen skill favorite <skill_id>             # favorite
```

See `${SKILL_DIR}/docs/05-market.md`.

---

## Command cheat sheet

| Command | Description |
|---------|-------------|
| `digen login` / `logout` / `whoami` / `config *` | Auth and config |
| `digen skill list` / `info <id>` / `export <id>` | My space / details / download zip |
| `digen skill init <name>` / `checkout <id>` | New template / check out locally |
| `digen skill validate [path]` | Local validation |
| `digen skill push [path] [--id]` | Pack and upload (create new or overwrite live content) |
| `digen skill publish <id>` / `unpublish <id>` / `cancel-review <id>` | Request public listing / make private / withdraw review |
| `digen skill delete <id>` / `digen skill enable <id>` / `digen skill disable <id>` | Delete / personal enable-disable |
| `digen skill market [--tab --category --q --sort]` / `categories` | Browse the marketplace |
| `digen skill install <id>` / `uninstall <id>` / `fork <id>` / `favorite <id>` | Install / uninstall / fork / favorite |

---

## Troubleshooting

See `${SKILL_DIR}/docs/06-troubleshooting.md`.

Common cases: API returns 401 → run `digen login` again (or `digen config set-user <id>` to fill in user_id); `digen skill validate` errors → use the checklist at the end of `SKILL_GUIDE.md`; `allowed-tools` stripped after `push` → you declared tools outside the user ceiling, see `SKILL_GUIDE.md` section 8.
