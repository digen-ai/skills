# Edit and validate

## What you can edit

- `SKILL.md` — YAML frontmatter (`name` / `description` / `display_name` / `allowed-tools` / `model`) + Markdown body
- `references/**` — extra docs, read on demand via `read_skill_file`

**Do not**:

- Introduce structured state protocols such as `data_schemas` / `operations` (skill_agent does not support them)
- Depend on executable scripts under `scripts/` (they are not parsed or executed)
- Declare authoring tools that only official skills may use (`write_skill_draft`, `publish_skill`, etc.)

See `${SKILL_DIR}/SKILL_GUIDE.md` for writing rules (**required reading before you start**).

## Local validation

```bash
digenskill validate                # current directory by default
digenskill validate ./my-skill-xxx
```

What it checks:

| Category | Checks |
|----------|--------|
| frontmatter | `name` is non-empty kebab-case; `description` is non-empty and not too short |
| tool allowlist | authoring tools reserved for official skills are a hard error; tools not on the usual ceiling list get a warning |
| body | non-empty, under the server character limit (~50000); should include When to use / Steps structure |
| reference files | count under the limit (~15); `references/xxx.md` paths mentioned in the body actually exist |

`validate` is local static checking only. The server still runs a security scan and a stricter ceiling intersection. Passing local validation does not guarantee a successful listing.

## Inspect changes

Workspaces are git repos by default (`init` / `checkout` create them). At any time:

```bash
git -C <workspace> diff
git -C <workspace> log --oneline
```

A successful `digenskill push` auto-commits local changes. The default commit message is `push: <name> #<id>` (override with `-m`).

## After editing

```bash
digenskill validate . && digenskill push .
```

See `04-publish.md`.
