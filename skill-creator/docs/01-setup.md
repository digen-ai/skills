# Install and log in

## Install the CLI

```bash
${SKILL_DIR}/scripts/install.sh
```

Equivalent to:

```bash
uv tool install --force --editable <repo>/cli
```

Requires [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`).

## Configure the API URL

```bash
digenskill config set-api https://api.digen.ai   # default; usually no change needed
digenskill config show
```

## Log in

Only **Google** login is supported. Email/password and Apple are not available. `digenskill login` (with or without `--google`) opens the Google web login page.

```bash
digenskill login                                    # Google (default)
digenskill login --google                           # same as above
digenskill login --token <existing_token>           # paste an existing token
```

The Google flow opens `{login_url}/cli/login` (default `https://agent.digen.ai/cli/login`). After you sign in on that page, it POSTs the Digen token to a local `http://127.0.0.1:<port>/callback`. The CLI does **not** exchange a Google `code` itself.

On SSH or a machine without a local browser, use `--manual` (or wait for the timeout) and paste the token shown on the page:

```bash
digenskill login --manual
# token> <paste the Digen token from the page>
# same as: digenskill login --token <token>
```

Override the login page base if needed:

```bash
digenskill config set-login-url https://agent.digen.ai
digenskill config show
```

## Login state

```bash
digenskill whoami     # locally cached identity; no network request
digenskill logout     # clear local credentials
```

Config and credentials are stored in `~/.digen/skill.yaml`. Local workspaces default to `~/.digen/skills/`.

## Common issues

- Login response has no `id` (some OAuth cases): the CLI will prompt you; run `digenskill config set-user <id>` to fill it in. Later requests send both `Authorization: Bearer <token>` and `X-User-Id`.
- Token is invalid after changing the API URL: run `digenskill login` again.
