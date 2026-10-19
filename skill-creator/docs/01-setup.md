# Install and log in

## Install the CLI

```bash
${SKILL_DIR}/scripts/install.sh
```

Equivalent to:

```bash
npm install -g digen-cli
```

Requires Node.js >=20. The script also supports `DIGEN_CLI_DIR=/path/to/digen-cli` for local development installs.

## Configure the API URL

```bash
digen config set-api https://api.digen.ai   # default; usually no change needed
digen config show
```

## Log in

Only **Google** login is supported. Email/password and Apple are not available. `digen login` (with or without `--google`) opens the Google web login page.

```bash
digen login                                    # Google (default)
digen login --google                           # same as above
digen login --token <existing_token>           # paste an existing token
```

The Google flow opens `{login_url}/cli/login` (default `https://agent.digen.ai/cli/login`). After you sign in on that page, it POSTs the Digen token to a local `http://127.0.0.1:<port>/callback`. The CLI does **not** exchange a Google `code` itself.

On SSH or a machine without a local browser, use `--manual` (or wait for the timeout) and paste the token shown on the page:

```bash
digen login --manual
# token> <paste the Digen token from the page>
# same as: digen login --token <token>
```

Override the login page base if needed:

```bash
digen config set-login-url https://agent.digen.ai
digen config show
```

## Login state

```bash
digen whoami     # locally cached identity; no network request
digen logout     # clear local credentials
```

Config and credentials are stored in `~/.digen/cli.yaml`. Local workspaces default to `~/.digen/skills/`. If you previously used the Python `digenskill` CLI, the first `digen` command migrates `~/.digen/skill.yaml` into `cli.yaml` and keeps the old file as `skill.yaml.bak`.

## Common issues

- Login response has no `id` (some OAuth cases): the CLI will prompt you; run `digen config set-user <id>` to fill it in. The CLI sends the composed `digen-token` header.
- Token is invalid after changing the API URL: run `digen login` again.
