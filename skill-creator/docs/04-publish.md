# Upload and publish

## Flow

```
local workspace → digenskill push (zip upload, private draft) → publish from the web UI (request public)
                                                          ↓
                                               security scan + review gate
                                    approved → listed immediately (status=published)
                                    pending  → human review (status=in_review)
```

## Upload (create new or write a draft)

```bash
digenskill push                        # current directory; validates, then packs and uploads
digenskill push ./my-skill-xxx
digenskill push . --id 123             # write a draft for an existing skill id
digenskill push . --skip-validate      # skip local validation (not recommended)
digenskill push . -m "tweak description"  # custom local git commit message
```

Behavior:

- **No** `.digen-skill-id` in the directory and no `--id`: `POST /import-zip` **creates** a skill (default `private`) and writes `.digen-skill-id` on success.
- **Has** `.digen-skill-id` or `--id` is passed: `PUT /{id}/import-zip` **overwrites the draft** (draft only; does not affect the live running version and does not trigger review).

A newly created skill is always private. Listing is requested separately on the web.

## Request a marketplace listing (web)

There is no `digenskill publish`. After `push`, open the Digen web UI (default `https://agent.digen.ai`, or the Login URL from `digenskill config show`) and request a listing there. Cover, category, and sample video are part of that web form.

This sets `visibility: public`:

- First request: auto-approved → listed immediately (`status=published`); needs human review → `status=in_review`.
- After it is already listed, `push` again and re-request listing on the web (content update): the marketplace keeps showing the last approved version until the new version is approved or rejected.

```bash
digenskill info <skill_id>     # inspect status / review_status / has_draft
```

## Withdraw / unpublish

```bash
digenskill cancel-review <skill_id>    # withdraw an in-review request; this is not unpublish
digenskill unpublish <skill_id>        # unlist and make private; takes effect immediately
```

`cancel-review` depends on history:

- Never successfully listed (first request still in review): withdrawing is equivalent to making it private.
- Previously listed (this is a content-update review): only this update is withdrawn; the marketplace keeps showing the old version and `visibility` is unchanged.

## Download / delete / toggle

```bash
digenskill export <skill_id> -o my-skill.zip   # download the zip
digenskill delete <skill_id>                    # delete (irreversible; asks for confirmation)
digenskill toggle <skill_id> on|off             # personal enable/disable (not uninstall/unpublish)
```
