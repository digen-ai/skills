# skills

A skill-authoring kit for **regular users** of the Digen platform: the `digen` CLI (for creating, editing, uploading, publishing, and marketplace actions) plus an agent skill pack that helps you create and modify skills.

## Layout

```
skills/
└── skill-creator/      # user-side skill-authoring agent pack (SKILL.md + docs)
```

The skill commands are part of the `digen-cli` npm package. There is no separate
Python `digenskill` CLI anymore.

## Quick start

### 1. Install the CLI

```bash
skill-creator/scripts/install.sh
```

Or install manually (requires Node.js >=20):

```bash
npm install -g digen-cli
```

### 2. Log in

```bash
digen config set-api https://api.digen.ai   # default; usually no change needed
digen login                                  # Google (the only supported method)
# or digen login --token <token>     (SSH / paste fallback)
```

### 3. Create your first skill

```bash
digen skill init my-first-skill -d "Use when the user wants to..."
cd ~/.digen/skills/my-first-skill-<timestamp>
# edit SKILL.md ...
digen skill validate .
digen skill push .
digen skill publish <skill_id>       # or use the web UI for rich listing fields
```

Full command docs live in `skill-creator/docs/`. Mount `skill-creator` for the AI and you can create skills conversationally (the AI will run `digen skill` for you).

## Command cheat sheet

| Command | Description |
|---------|-------------|
| `digen login` / `digen config *` | Log in and configure |
| `digen skill list` / `market` / `info <id>` | Browse my space / marketplace / details |
| `digen skill init <name>` / `checkout <id>` | Create a local template / check out an existing skill |
| `digen skill validate [path]` | Validate SKILL.md locally |
| `digen skill push [path]` | Pack and upload (create new or overwrite live content) |
| `digen skill publish <id>` / `unpublish <id>` | Request public listing / make private |
| `digen skill install <id>` / `uninstall <id>` | Install / uninstall a marketplace skill |
| `digen skill delete <id>` / `digen skill enable <id>` / `digen skill disable <id>` | Delete / enable / disable |

See `digen skill --help` for details.
