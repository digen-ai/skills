"""digenskill — command-line tool for managing your own Digen skills.

Scriptable CLI on top of the user-facing API (/api/v1/skills) for local
authoring (init / checkout / validate / push). Marketplace listing
(publish) is done on the web UI.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from . import auth as auth_helpers
from .api_client import APIError, DigenAPIClient, SKILLS_API_PREFIX, parse_digen_token
from .config import (
    DEFAULT_API_URL,
    DEFAULT_LOGIN_URL,
    SKILL_WORKSPACE_DIR,
    clear_login,
    ensure_session_id,
    get_api_url,
    get_language,
    get_login_url,
    get_token,
    get_token_expires_at,
    get_user_id,
    load_config,
    save_config,
    save_login,
)
from .display import (
    console,
    print_error,
    print_market_list,
    print_my_skills,
    print_skill_info,
    print_success,
    print_warning,
)
from .validate import validate_workspace
from .workspace import SKILL_FILENAME, infer_skill_name, pack_workspace, write_workspace

app = typer.Typer(name="digenskill", help="Digen user-side skill CLI", no_args_is_help=True)
config_app = typer.Typer(name="config", help="CLI config (API URL / user identity)")
app.add_typer(config_app, name="config")


def _run(coro):
    return asyncio.run(coro)


def _get_client() -> DigenAPIClient:
    return DigenAPIClient(
        get_api_url(),
        get_token(),
        get_user_id(),
        session_id=ensure_session_id(),
        language=get_language(),
        token_expires_at=get_token_expires_at(),
        referer=get_login_url(),
    )


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _require_login():
    if not get_token() and get_user_id() is None:
        print_error("Not logged in. Run: digenskill login")
        raise typer.Exit(1)


def _print_web_publish_hint() -> None:
    web = get_login_url().rstrip("/")
    console.print(f"[dim]To list on the marketplace, publish from the web UI: {web}[/dim]")


# ==================== Config ====================

@config_app.command("set-api")
def config_set_api(url: str = typer.Argument(..., help="API base URL")):
    """Set the API URL (default https://api.digen.ai)."""
    cfg = load_config()
    cfg["api_url"] = url
    save_config(cfg)
    print_success(f"API URL set to {url}")


@config_app.command("set-user")
def config_set_user(user_id: int = typer.Argument(..., help="Digen user id")):
    """Manually set user_id (when the token response has no id). Used in ``digen-token``."""
    cfg = load_config()
    cfg["user_id"] = user_id
    save_config(cfg)
    print_success(f"user_id set to {user_id}")


@config_app.command("set-login-url")
def config_set_login_url(url: str = typer.Argument(..., help="Web login page base URL")):
    """Set the CLI login page base URL (default https://agent.digen.ai). Used by Google login."""
    cfg = load_config()
    cfg["login_url"] = url
    save_config(cfg)
    print_success(f"Login URL set to {url}")


@config_app.command("show")
def config_show():
    """Show the current config."""
    cfg = load_config()
    api_url = cfg.get("api_url", DEFAULT_API_URL).rstrip("/")
    console.print(f"API URL:  [cyan]{api_url}[/cyan]")
    console.print(f"Login URL: [cyan]{cfg.get('login_url', DEFAULT_LOGIN_URL)}[/cyan]")
    console.print(f"Skills API: [cyan]{api_url}{SKILLS_API_PREFIX}[/cyan]")
    token = cfg.get("token", "")
    masked = token[:8] + "..." if token and len(token) > 8 else token or "(not set)"
    console.print(f"Token:    [dim]{masked}[/dim]")
    sid = cfg.get("session_id") or "(not set)"
    if isinstance(sid, str) and len(sid) > 8:
        sid = sid[:8] + "..."
    console.print(f"Session:  [dim]{sid}[/dim]")
    console.print(f"User ID:  [dim]{cfg.get('user_id', '(not set)')}[/dim]")
    console.print(f"Language: [dim]{cfg.get('language', 'en')}[/dim]")
    console.print(f"Name:     [dim]{cfg.get('name', '(not set)')}[/dim]")
    console.print(f"Email:    [dim]{cfg.get('email', '(not set)')}[/dim]")
    console.print(f"Skills:   [dim]{SKILL_WORKSPACE_DIR}[/dim]")


# ==================== Auth ====================

def _parse_user_id(value) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _save_login_result(data: dict) -> None:
    token = data.get("token")
    if not token:
        print_error("Login response did not include a token")
        raise typer.Exit(1)
    raw, token_uid, token_exp = parse_digen_token(token)
    token = raw
    user_id = data.get("id")
    if not isinstance(user_id, int):
        user_id = _parse_user_id(user_id)
    if user_id is None:
        user_id = token_uid
    expires_at = _parse_user_id(data.get("expire") or data.get("expires_at") or data.get("token_expires_at"))
    if expires_at is None:
        expires_at = token_exp
    save_login(
        token=token,
        user_id=user_id,
        name=data.get("name") or None,
        email=data.get("email") or None,
        language=data.get("language") or None,
        session_id=data.get("sessionid") or data.get("session_id") or None,
        token_expires_at=expires_at,
    )
    who = data.get("name") or data.get("email") or "user"
    print_success(f"Logged in as {who}")
    if user_id is None:
        print_warning(
            "Login response did not include a user id. If later API calls return 401, run: "
            "digenskill config set-user <id>"
        )
    if data.get("welcomeURL"):
        console.print(f"[dim]{data['welcomeURL']}[/dim]")


def _save_pasted_token(token: str) -> None:
    if not token:
        print_error("No token provided")
        raise typer.Exit(1)
    raw, user_id, expires_at = parse_digen_token(token)
    save_login(token=raw, user_id=user_id, token_expires_at=expires_at)
    print_success("Token saved")
    console.print("[dim]If the API returns 401, also run: digenskill config set-user <id>[/dim]")


def _browser_login(*, hint: str, manual: bool) -> None:
    """Open the dedicated web login page and receive a Digen token via loopback POST or paste."""
    login_base = get_login_url()
    server = None
    url_printed = False

    if not manual:
        try:
            server = auth_helpers.loopback_callback_server()
        except OSError:
            print_warning("Could not bind a local callback port; paste the token from the page")
            server = None

    if server is not None:
        state = auth_helpers.generate_state()
        callback = f"http://127.0.0.1:{server.port}/callback"
        url = auth_helpers.build_cli_login_url(
            login_base,
            hint=hint,
            callback=callback,
            state=state,
        )
        console.print("[bold]Open this URL if the browser does not open:[/bold]")
        print(url, flush=True)
        console.print("[dim]Waiting for authorization…[/dim]")
        url_printed = True
        auth_helpers.open_browser(url)
        result = server.wait_for_result(timeout=auth_helpers.LOOPBACK_TIMEOUT)
        if result and result.get("token"):
            if result.get("state") != state:
                print_error("Login callback state mismatch")
                raise typer.Exit(1)
            _save_login_result(
                {
                    "token": result["token"],
                    "name": result.get("name"),
                    "email": result.get("email"),
                    "id": result.get("id"),
                    "sessionid": result.get("sessionid"),
                }
            )
            return
        print_warning("Did not receive a local callback; paste the token from the page")

    url = auth_helpers.build_cli_login_url(login_base, hint=hint)
    if url_printed:
        console.print(
            "[dim]Copy the token from the page and paste it here "
            "(same as: digenskill login --token)[/dim]"
        )
        token = console.input("[bold yellow]token> [/bold yellow]").strip()
    else:
        token = auth_helpers.prompt_for_token(url, console)
    _save_pasted_token(token)


@app.command("login")
def login(
    email: Optional[str] = typer.Option(
        None, "--email", "-e", help="Not supported; only Google login is available"
    ),
    password: Optional[str] = typer.Option(
        None, "--password", "-p", help="Not supported; only Google login is available"
    ),
    google: bool = typer.Option(
        False, "--google", help="Open the web login page with Google (default)"
    ),
    apple: bool = typer.Option(
        False, "--apple", help="Not supported; only Google login is available"
    ),
    token: Optional[str] = typer.Option(
        None, "--token", help="Log in with an existing token (SSH / paste fallback)"
    ),
    manual: bool = typer.Option(
        False, "--manual", help="Do not start a local callback server; paste the token from the page"
    ),
):
    """Log in via Google and save credentials to ~/.digen/skill.yaml.

    Only Google login is supported (this is the default). Email/password and
    Apple are not available. --token pastes an existing token.
    """
    if email or password or apple:
        print_error(
            "Only Google login is supported. Email/password and Apple login are not available. "
            "Run: digenskill login"
        )
        raise typer.Exit(1)

    if token:
        _save_pasted_token(token)
        return

    # --google is an explicit alias of the default Google web login.
    _ = google
    _browser_login(hint="google", manual=manual)


@app.command("logout")
def logout():
    """Clear locally saved login credentials."""
    clear_login()
    print_success("Logged out")


@app.command("whoami")
def whoami():
    """Show the current login identity (local cache; no network request)."""
    cfg = load_config()
    if not cfg.get("token") and cfg.get("user_id") is None:
        print_warning("Not logged in")
        raise typer.Exit(1)
    console.print(f"[bold]Name:[/bold]  {cfg.get('name', '(unknown)')}")
    console.print(f"[bold]Email:[/bold] {cfg.get('email', '(unknown)')}")
    console.print(f"[bold]User ID:[/bold] {cfg.get('user_id', '(unknown)')}")


# ==================== My space / market ====================

@app.command("list")
def list_skills():
    """List my skill space (builtin + self-authored + installed)."""
    _require_login()

    async def _do():
        client = _get_client()
        try:
            data = await client.list_my_skills()
            print_my_skills(data)
        except APIError as e:
            print_error(e.detail)
            raise typer.Exit(1)
        finally:
            await client.close()
    _run(_do())


@app.command("market-categories")
def market_categories():
    """List marketplace primary-category enums (for `market --category`)."""
    _require_login()

    async def _do():
        client = _get_client()
        try:
            data = await client.list_market_categories()
            for c in data.get("categories") or []:
                console.print(f"  - {c}")
        except APIError as e:
            print_error(e.detail)
            raise typer.Exit(1)
        finally:
            await client.close()
    _run(_do())


@app.command("market")
def market(
    tab: str = typer.Option("discover", "--tab", help="discover | favorites | mine"),
    category: Optional[str] = typer.Option(None, "--category"),
    q: Optional[str] = typer.Option(None, "--q", help="Search query"),
    sort: str = typer.Option("featured", "--sort", help="featured | popular | recent"),
    limit: int = typer.Option(50, "--limit"),
    offset: int = typer.Option(0, "--offset"),
):
    """Browse the skill marketplace."""
    _require_login()

    async def _do():
        client = _get_client()
        try:
            data = await client.list_market(
                tab=tab, category=category, q=q, sort=sort, limit=limit, offset=offset
            )
            print_market_list(data)
        except APIError as e:
            print_error(e.detail)
            raise typer.Exit(1)
        finally:
            await client.close()
    _run(_do())


@app.command("info")
def info(id_or_slug: str = typer.Argument(..., help="Skill ID or slug")):
    """Show skill details."""
    _require_login()

    async def _do():
        client = _get_client()
        try:
            if id_or_slug.isdigit():
                skill = await client.get_skill(int(id_or_slug))
            else:
                skill = await client.get_skill_by_slug(id_or_slug)
            print_skill_info(skill)
        except APIError as e:
            print_error(e.detail)
            raise typer.Exit(1)
        finally:
            await client.close()
    _run(_do())


@app.command("export")
def export_skill(
    skill_id: int = typer.Argument(..., help="Skill ID"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output zip path (default <name>.zip)"),
):
    """Download a skill zip."""
    _require_login()

    async def _do():
        client = _get_client()
        try:
            zip_bytes = await client.export_skill_zip(skill_id)
            out = output or Path(f"skill-{skill_id}.zip")
            out.write_bytes(zip_bytes)
            print_success(f"Saved to {out}")
        except APIError as e:
            print_error(e.detail)
            raise typer.Exit(1)
        finally:
            await client.close()
    _run(_do())


# ==================== Workspace: init / checkout / validate / push ====================

@app.command("init")
def init_skill(
    name: str = typer.Argument(..., help="New skill name (kebab-case, e.g. image-generation)"),
    as_name: Optional[str] = typer.Option(None, "--as", help="Workspace directory suffix (default: timestamp)"),
    display_name: Optional[str] = typer.Option(None, "--display-name"),
    description: str = typer.Option("", "--description", "-d", help="Trigger condition (Use when the user wants to…)"),
    force: bool = typer.Option(False, "--force", "-f"),
):
    """Create a local skill template workspace (does not upload)."""
    suffix = as_name or datetime.now().strftime("%Y%m%d-%H%M%S")
    target = SKILL_WORKSPACE_DIR / f"{name}-{suffix}"
    if target.exists():
        if not force:
            print_error(f"Target already exists: {target}")
            raise typer.Exit(1)
        shutil.rmtree(target)

    desc = description or f"Use when the user wants to use the {name} capability"
    skill = {
        "name": name,
        "display_name": display_name or name,
        "description": desc,
        "allowed_tools": ["list_models"],
        "body": (
            f"# {display_name or name}\n\n"
            "A short description of what this skill does.\n\n"
            "## When to use\n\n"
            "- Trigger scenarios that match the description\n\n"
            "## Steps\n\n"
            "1. …\n"
            "2. Call tools; parameter conventions: …\n"
            "3. Reply to the user briefly in natural language\n\n"
            "## Notes\n\n"
            "- Report failures honestly; never invent URLs\n"
            "- Politely refuse disallowed content\n"
        ),
        "reference_files": {},
        "metadata": {},
    }
    write_workspace(target, skill)
    try:
        _git(target, "init", "-q")
        _git(target, "add", ".")
        _git(
            target, "-c", "user.email=digenskill@local", "-c", "user.name=digenskill",
            "commit", "-q", "-m", f"init: {name}",
        )
    except subprocess.CalledProcessError as e:
        print_warning(f"git init failed: {e.stderr.decode() if e.stderr else e}")

    print_success(f"Initialized workspace at {target}")
    console.print(f"[dim]cd {target}[/dim]")
    console.print("[dim]Edit SKILL.md, then: digenskill validate . && digenskill push .[/dim]")


@app.command("checkout")
def checkout(
    skill_id: int = typer.Argument(..., help="Skill ID"),
    as_name: Optional[str] = typer.Option(None, "--as", help="Workspace directory suffix (default: timestamp)"),
    force: bool = typer.Option(False, "--force", "-f"),
):
    """Download an existing skill as a local git workspace (draft layered on automatically)."""
    _require_login()

    async def _do():
        client = _get_client()
        try:
            return await client.get_skill(skill_id)
        except APIError as e:
            print_error(e.detail)
            raise typer.Exit(1)
        finally:
            await client.close()

    skill = _run(_do())
    name = skill.get("name") or f"skill-{skill_id}"
    suffix = as_name or datetime.now().strftime("%Y%m%d-%H%M%S")
    target = SKILL_WORKSPACE_DIR / f"{name}-{suffix}"
    if target.exists():
        if not force:
            print_error(f"Target already exists: {target}\nUse --force to overwrite, or --as <name> for a different suffix")
            raise typer.Exit(1)
        shutil.rmtree(target)

    write_workspace(target, skill)
    (target / ".digen-skill-id").write_text(str(skill_id))
    try:
        _git(target, "init", "-q")
        _git(target, "add", ".")
        _git(
            target, "-c", "user.email=digenskill@local", "-c", "user.name=digenskill",
            "commit", "-q", "-m", f"baseline: {name}",
        )
    except subprocess.CalledProcessError as e:
        print_warning(f"git init failed: {e.stderr.decode() if e.stderr else e}")

    draft_note = " (includes unpublished draft)" if skill.get("has_draft") else ""
    print_success(f"Checked out #{skill_id} {name}{draft_note} -> {target}")
    console.print(f"[dim]cd {target}[/dim]")
    console.print(f"[dim]# After editing: digenskill push {target}[/dim]")


@app.command("validate")
def validate(path: Path = typer.Argument(Path("."), help="Workspace directory (default: current directory)")):
    """Validate SKILL.md + references locally."""
    path = path.resolve()
    if not path.is_dir():
        print_error(f"Not a directory: {path}")
        raise typer.Exit(1)

    errors, warnings = validate_workspace(path)
    for w in warnings:
        print_warning(w)
    for e in errors:
        print_error(e)

    if errors:
        console.print(f"[bold red]FAIL[/bold red]  {len(errors)} error(s), {len(warnings)} warning(s)")
        raise typer.Exit(1)

    print_success(f"OK  ({len(warnings)} warning(s))" if warnings else "OK")


@app.command("push")
def push(
    path: Path = typer.Argument(Path("."), help="Workspace directory (default: current directory)"),
    skill_id: Optional[int] = typer.Option(None, "--id", help="Existing skill ID (overwrite draft); omit and if the directory has no recorded ID, create new"),
    skip_validate: bool = typer.Option(False, "--skip-validate"),
    message: Optional[str] = typer.Option(None, "-m", "--message", help="Local git commit message"),
):
    """Pack and upload: create a skill or write a draft for an existing one (does not list on the marketplace)."""
    _require_login()
    path = path.resolve()
    if not path.is_dir():
        print_error(f"Not a directory: {path}")
        raise typer.Exit(1)
    if not (path / SKILL_FILENAME).is_file():
        print_error(f"Missing {SKILL_FILENAME}")
        raise typer.Exit(1)

    if not skip_validate:
        errors, warnings = validate_workspace(path)
        for w in warnings:
            print_warning(w)
        if errors:
            for e in errors:
                print_error(e)
            print_error("Validation failed; fix and retry, or pass --skip-validate to force")
            raise typer.Exit(1)

    id_file = path / ".digen-skill-id"
    resolved_id = skill_id
    if resolved_id is None and id_file.is_file():
        try:
            resolved_id = int(id_file.read_text().strip())
        except ValueError:
            resolved_id = None

    try:
        skill_name = infer_skill_name(path)
        zip_bytes = pack_workspace(path)
    except (FileNotFoundError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(1)

    async def _do():
        client = _get_client()
        try:
            if resolved_id is not None:
                await client.update_skill_zip(resolved_id, zip_bytes)
                print_success(f"Saved draft: #{resolved_id} ({skill_name})")
                _print_web_publish_hint()
                return resolved_id
            else:
                result = await client.import_skill_zip(zip_bytes)
                new_id = result.get("id")
                print_success(f"Created skill #{new_id} ({skill_name})")
                id_file.write_text(str(new_id))
                _print_web_publish_hint()
                return new_id
        except APIError as e:
            print_error(e.detail)
            return None
        finally:
            await client.close()

    result_id = _run(_do())
    if result_id is None:
        raise typer.Exit(1)

    if (path / ".git").exists():
        try:
            status = subprocess.run(
                ["git", "status", "--porcelain"], cwd=path, capture_output=True, text=True
            )
            if status.stdout.strip():
                commit_msg = message or f"push: {skill_name} #{result_id}"
                _git(path, "add", ".")
                _git(
                    path, "-c", "user.email=digenskill@local", "-c", "user.name=digenskill",
                    "commit", "-q", "-m", commit_msg,
                )
                console.print(f"[dim]Committed local changes: {commit_msg}[/dim]")
        except subprocess.CalledProcessError as e:
            print_warning(f"git commit failed: {e.stderr.decode() if e.stderr else e}")


# ==================== Lifecycle ====================

@app.command("unpublish")
def unpublish(skill_id: int = typer.Argument(..., help="Skill ID")):
    """Make a skill private (revoke public listing; takes effect immediately)."""
    _require_login()

    async def _do():
        client = _get_client()
        try:
            await client.set_visibility(skill_id, "private")
            print_success(f"#{skill_id} is now private")
        except APIError as e:
            print_error(e.detail)
            raise typer.Exit(1)
        finally:
            await client.close()
    _run(_do())


@app.command("cancel-review")
def cancel_review(skill_id: int = typer.Argument(..., help="Skill ID")):
    """Withdraw an in-review listing/update request (not the same as unpublish)."""
    _require_login()

    async def _do():
        client = _get_client()
        try:
            skill = await client.cancel_review(skill_id)
            print_skill_info(skill)
        except APIError as e:
            print_error(e.detail)
            raise typer.Exit(1)
        finally:
            await client.close()
    _run(_do())


@app.command("delete")
def delete(skill_id: int = typer.Argument(..., help="Skill ID")):
    """Delete your skill (irreversible)."""
    _require_login()
    if not typer.confirm(f"Delete skill #{skill_id}? This cannot be undone"):
        raise typer.Exit(0)

    async def _do():
        client = _get_client()
        try:
            await client.delete_skill(skill_id)
            print_success(f"Deleted #{skill_id}")
        except APIError as e:
            print_error(e.detail)
            raise typer.Exit(1)
        finally:
            await client.close()
    _run(_do())


@app.command("toggle")
def toggle(
    skill_id: int = typer.Argument(..., help="Skill ID"),
    state: str = typer.Argument(..., help="on | off"),
):
    """Enable / disable a skill (not the same as uninstall)."""
    _require_login()
    if state not in ("on", "off"):
        print_error("state must be on or off")
        raise typer.Exit(1)

    async def _do():
        client = _get_client()
        try:
            await client.toggle_skill(skill_id, state == "on")
            print_success(f"#{skill_id} enabled={state == 'on'}")
        except APIError as e:
            print_error(e.detail)
            raise typer.Exit(1)
        finally:
            await client.close()
    _run(_do())


# ==================== Market: install / uninstall ====================

@app.command("install")
def install(skill_id: int = typer.Argument(..., help="Skill ID")):
    """Install a public skill from the marketplace."""
    _require_login()

    async def _do():
        client = _get_client()
        try:
            await client.install_skill(skill_id)
            print_success(f"Installed #{skill_id}")
        except APIError as e:
            print_error(e.detail)
            raise typer.Exit(1)
        finally:
            await client.close()
    _run(_do())


@app.command("uninstall")
def uninstall(skill_id: int = typer.Argument(..., help="Skill ID")):
    """Uninstall an installed skill."""
    _require_login()

    async def _do():
        client = _get_client()
        try:
            await client.uninstall_skill(skill_id)
            print_success(f"Uninstalled #{skill_id}")
        except APIError as e:
            print_error(e.detail)
            raise typer.Exit(1)
        finally:
            await client.close()
    _run(_do())


@app.command("fork")
def fork(skill_id: int = typer.Argument(..., help="Skill ID")):
    """Fork an official or someone else's public skill into your own private copy."""
    _require_login()

    async def _do():
        client = _get_client()
        try:
            skill = await client.fork_skill(skill_id)
            print_skill_info(skill)
        except APIError as e:
            print_error(e.detail)
            raise typer.Exit(1)
        finally:
            await client.close()
    _run(_do())


@app.command("favorite")
def favorite(
    skill_id: int = typer.Argument(..., help="Skill ID"),
    remove: bool = typer.Option(False, "--remove", help="Remove from favorites"),
):
    """Favorite / unfavorite a skill."""
    _require_login()

    async def _do():
        client = _get_client()
        try:
            if remove:
                await client.unfavorite_skill(skill_id)
                print_success(f"Unfavorited #{skill_id}")
            else:
                await client.favorite_skill(skill_id)
                print_success(f"Favorited #{skill_id}")
        except APIError as e:
            print_error(e.detail)
            raise typer.Exit(1)
        finally:
            await client.close()
    _run(_do())


if __name__ == "__main__":
    app()
