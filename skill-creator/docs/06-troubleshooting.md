# Troubleshooting

## 401 / 403

- Run `digenskill whoami` to confirm you are logged in locally.
- Run `digenskill login` again. If the response has no `id`, also run `digenskill config set-user <id>`.
- 403 is common when accessing a skill you do not own, that is not listed, or whose author set `content_visibility=closed` (body is hidden, but the marketplace card is still visible).

## `digenskill validate` errors

Work through the checklist at the end of `${SKILL_DIR}/SKILL_GUIDE.md`. Common causes:

| Error | Cause | Fix |
|-------|-------|-----|
| `frontmatter.name must not be empty` | missing `name` | add `name: my-skill` |
| `name should be kebab-case` | underscores / non-ASCII / camelCase | use `[a-z0-9]+(-[a-z0-9]+)*` |
| `allowed-tools includes authoring tools reserved for official skills` | declared `write_skill_draft` etc. | remove them; user skills cannot declare these |
| `body is N characters, over the server limit` | body too long | move details into `references/*.md` |
| `body references a missing file` | body mentions `` `references/xxx.md` `` but the file is missing | add the file or fix the path |
| `N reference files, over the server limit` | too many references | merge or drop unused files |

## Tools stripped after `push` / a tool cannot be called at runtime

The server intersects your `allowed-tools` with the user ceiling. Out-of-ceiling tools **do not error**; they are simply unavailable to the model. Check the ceiling list in `SKILL_GUIDE.md` section 8 for spelling and whether the tool is allowed.

## `push` reports "empty file" / "invalid zip archive"

The workspace must contain `SKILL.md` (case-sensitive). Run the command from the correct directory (`digenskill push .`, not the parent).

## Google login cannot complete

- Only Google login is supported. Email/password and Apple are not available; `digenskill login` always opens the Google web page.
- Automatic callback only works when the browser and the CLI run on the **same machine**. Over SSH, use `--manual` or copy the token from the page and run `digenskill login --token <token>`.
- Google login opens `{login_url}/cli/login` (default `https://agent.digen.ai`). Change it with `digenskill config set-login-url`.
- Do not paste a Google `code` into the CLI. Only the Digen token from the login page (or `--token`) is accepted.
- `--code` / `--client-id` / `--redirect-url` are no longer used.

## Create/upload quota exceeded (429)

`each user can create at most N skills` — you have hit the per-user skill cap (default ~50). `digenskill delete <id>` unused ones, or ask the platform to raise the quota.

## Want to change marketplace listing (cover / category / sample video)

Listing fields and the publish request live on the web UI, not in the CLI. Open the Digen site (default `https://agent.digen.ai`, or the Login URL from `digenskill config show`) and edit the listing there. Do not invent REST calls.
