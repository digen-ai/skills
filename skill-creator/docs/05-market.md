# Marketplace: browse / install / fork

## Browse

```bash
digenskill market                                  # discover tab by default
digenskill market --tab favorites                  # my favorites
digenskill market --tab mine                       # my own skills (including drafts)
digenskill market --category ShortDrama --q image
digenskill market --sort popular --limit 20
digenskill market-categories                       # list valid category enums
```

`--sort` supports `featured` (default, operator pins first) / `popular` / `recent`. `favorites` and `mine` ignore `--sort`.

## View details

```bash
digenskill info <skill_id>
digenskill info <slug>          # also works by slug
```

Whether the body is visible depends on the author's `content_visibility`: `open` (default) means anyone who can see the detail page can read the body; `closed` means only the author can (the skill is still discoverable, installable, and runnable — the source is just hidden).

## Install / uninstall

```bash
digenskill install <skill_id>       # install (reference semantics; body is not copied; appears in my space)
digenskill uninstall <skill_id>
```

Install is a **reference**: author updates do not affect you immediately (install-snapshot semantics). After the author ships a new approved version, your next conversation switches automatically.

## Fork

```bash
digenskill fork <skill_id>
```

Fork **copies** the body, reference files, and tool permissions into a new private skill owned by you. You can then edit it like a self-authored skill and request a listing on the web. Compared with install:

| | install | fork |
|---|---|---|
| Semantics | reference; body is not copied | copies the body into an independent copy |
| Editable | cannot edit someone else's content | yes; it is your skill |
| Content updates | follows the author after approval (next conversation) | does not follow; you maintain it |
| Use when | you want to use a published capability as-is | you want to build on someone else's skill |

Only official skills or publicly listed, approved skills can be forked. Skills with `content_visibility=closed` cannot be forked.

## Favorites

```bash
digenskill favorite <skill_id>
digenskill favorite <skill_id> --remove
```
