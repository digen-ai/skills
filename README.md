# skills

A skill-authoring kit for **regular users** of the Digen platform: a command-line tool (for creating, editing, uploading, and marketplace actions) plus an agent skill pack that helps you create and modify skills. Marketplace listing is done on the web UI.

## Layout

```
skills/
├── cli/                # digenskill CLI (Python package digen-skill-cli)
└── skill-creator/      # user-side skill-authoring agent pack (SKILL.md)
```

## Quick start

### 1. Install the CLI

```bash
skill-creator/scripts/install.sh
```

Or install manually (requires [uv](https://docs.astral.sh/uv/)):

```bash
uv tool install --force --editable cli/
```

### 2. Log in

```bash
digenskill config set-api https://api.digen.ai   # default; usually no change needed
digenskill login                                  # Google (the only supported method)
# or digenskill login --token <token>     (SSH / paste fallback)
```

### 3. Create your first skill

```bash
digenskill init my-first-skill -d "Use when the user wants to..."
cd ~/.digen/skills/my-first-skill-<timestamp>
# edit SKILL.md ...
digenskill validate .
digenskill push .
# then publish from the web UI
```

Full command docs live in `skill-creator/docs/`. Mount `skill-creator` for the AI and you can create skills conversationally (the AI will run `digenskill` for you).

## Command cheat sheet

| Command | Description |
|---------|-------------|
| `digenskill login` / `config *` | Log in and configure |
| `digenskill list` / `market` / `info <id>` | Browse my space / marketplace / details |
| `digenskill init <name>` / `checkout <id>` | Create a local template / check out an existing skill |
| `digenskill validate [path]` | Validate SKILL.md locally |
| `digenskill push [path]` | Pack and upload (create new or write a draft) |
| `digenskill unpublish <id>` | Make a listed skill private |
| `digenskill install <id>` / `uninstall <id>` | Install / uninstall a marketplace skill |
| `digenskill delete <id>` / `toggle <id> on\|off` | Delete / enable or disable |

See `digenskill --help` for details.
