# Create / check out

## View my space

```bash
digenskill list
```

Returns two groups: **Built-in Skills** (`builtin`, mounted by the platform by default, does not count against space quota) and **My Space** (`space`, self-authored plus installed marketplace skills).

## Create a local template

```bash
digenskill init my-skill -d "Use when the user wants to…"
digenskill init my-skill --display-name "My Skill" -d "..." --as demo   # custom directory suffix
```

Creates `~/.digen/skills/my-skill-<suffix>/` with a minimal `SKILL.md` (frontmatter plus a When to use / Steps / Notes skeleton) and runs `git init` plus a baseline commit. Nothing is uploaded yet.

## Check out an existing skill

```bash
digenskill checkout <skill_id>
digenskill checkout <skill_id> --as fix-desc     # custom directory suffix
digenskill checkout <skill_id> --force           # overwrite if the directory already exists
```

- This pulls the **edit view**: if the skill has an unpublished draft, the draft is layered on automatically (it may differ from the live version).
- The workspace writes a `.digen-skill-id` marker so later `digenskill push` in that directory does not need `--id`.
- Also runs `git init` plus a baseline commit so you can `git diff` later.

## Directory layout

```
my-skill-20240101-120000/
├── SKILL.md              # frontmatter + body
├── .digen-skill-id       # (from checkout) associated server skill id
├── .git/
└── references/           # optional, multi-stage details
    └── stage_a.md
```

## Next step

Read `${SKILL_DIR}/SKILL_GUIDE.md` before editing `SKILL.md` (writing rules, tool ceiling, `name` constraints). After editing, see `03-edit.md` and `04-publish.md`.
