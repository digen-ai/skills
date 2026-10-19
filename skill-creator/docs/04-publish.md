# Upload and publish

## Flow

```
local workspace → digen skill push (zip upload, private) → digen skill publish (request public)
                                                          ↓
                                               security scan + review gate
                                    approved → listed immediately (status=published)
                                    pending  → human review (status=in_review)
```

## Upload (create new or overwrite)

```bash
digen skill push                        # current directory; validates, then packs and uploads
digen skill push ./my-skill-xxx
digen skill push . --id 123             # overwrite an existing skill (takes effect immediately)
digen skill push . --skip-validate      # skip local validation (not recommended)
digen skill push . -m "tweak description"  # custom local git commit message
```

Behavior:

- **No** `.digen-skill-id` in the directory and no `--id`: `POST /import-zip` **creates** a skill (default `private`) and writes `.digen-skill-id` on success.
- **Has** `.digen-skill-id` or `--id` is passed: `PUT /{id}/import-zip` **overwrites the live content** — there is no draft stage, so the change takes effect for you immediately. It does **not** change the marketplace-listed version and does **not** trigger review: if the skill is listed, installers keep seeing the last approved snapshot until you re-request the listing (`digen skill publish <id>`) and it is approved.

A newly created skill is always private. Listing is requested separately.

## Request a marketplace listing

```bash
digen skill publish <skill_id>                         # request public visibility
digen skill publish <skill_id> --file listing.json     # update listing first, then request public
digen skill listing <skill_id> --file listing.json     # listing/category/slug/locales only
digen skill cover <skill_id> ./cover.jpg --kind card   # upload a cover and merge it into listing
digen skill clip <skill_id> ./sample.mp4 --label Demo  # upload a sample clip
```

The web UI (default `https://agent.digen.ai`, or the Login URL from `digen config show`) remains the most convenient way to fill rich listing fields, but the CLI can apply the same JSON via `--file`.

`publish` sets `visibility: public`:

- First request: auto-approved → listed immediately (`status=published`); needs human review → `status=in_review`.
- After it is already listed, `push` again and re-request listing with `digen skill publish <id>` (content update): the marketplace keeps showing the last approved version until the new version is approved or rejected.

```bash
digen skill info <skill_id>     # inspect status / review_status
```

## Withdraw / unpublish

```bash
digen skill cancel-review <skill_id>    # withdraw an in-review request; this is not unpublish
digen skill unpublish <skill_id>        # unlist and make private; takes effect immediately
```

`cancel-review` depends on history:

- Never successfully listed (first request still in review): withdrawing is equivalent to making it private.
- Previously listed (this is a content-update review): only this update is withdrawn; the marketplace keeps showing the old version and `visibility` is unchanged.

## Download / delete / toggle

```bash
digen skill export <skill_id> -o my-skill.zip   # download the zip
digen skill delete <skill_id>                    # delete (irreversible; asks for confirmation)
digen skill enable <skill_id> / disable <skill_id>             # personal enable/disable (not uninstall/unpublish)
```
