"""Rich console display helpers."""

from typing import Any, Dict, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def print_error(msg: str):
    console.print(f"[bold red]Error:[/bold red] {msg}")


def print_success(msg: str):
    console.print(f"[bold green]{msg}[/bold green]")


def print_warning(msg: str):
    console.print(f"[bold yellow]Warning:[/bold yellow] {msg}")


# ==================== My space ====================

def print_skill_row_table(title: str, skills: List[Dict[str, Any]]):
    table = Table(title=f"{title} ({len(skills)})")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Display")
    table.add_column("Status")
    table.add_column("Enabled", justify="center")
    table.add_column("Draft", justify="center")
    for s in skills:
        enabled = "[green]Yes[/green]" if s.get("enabled", True) else "[red]No[/red]"
        draft = "[yellow]Y[/yellow]" if s.get("has_draft") else "[dim]-[/dim]"
        table.add_row(
            str(s.get("id", "?")),
            s.get("name", "?"),
            s.get("display_name") or "",
            s.get("status") or "",
            enabled,
            draft,
        )
    console.print(table)


def print_my_skills(data: Dict[str, Any]):
    builtin = data.get("builtin") or []
    space = data.get("space") or []
    if builtin:
        print_skill_row_table("Built-in Skills", builtin)
    print_skill_row_table("My Space", space)
    console.print(
        f"[dim]Space capacity: {data.get('space_total', len(space))} / "
        f"mount limit {data.get('max_mounted', '?')}[/dim]"
    )


def print_market_list(data: Dict[str, Any]):
    skills = data.get("skills") or []
    table = Table(title=f"Market · {data.get('tab', 'discover')} ({data.get('total', len(skills))})")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Title")
    table.add_column("Category")
    table.add_column("Author")
    table.add_column("Installs", justify="right")
    table.add_column("Favorites", justify="right")
    for s in skills:
        author = (s.get("author") or {}).get("handle") or ""
        table.add_row(
            str(s.get("id", "?")),
            s.get("name", "?"),
            s.get("title") or "",
            s.get("primary_category") or "",
            author,
            str(s.get("installs", 0)),
            str(s.get("favorites", 0)),
        )
    console.print(table)


def print_skill_info(skill: Dict[str, Any]):
    title = f"#{skill.get('id')}  {skill.get('name')}  {skill.get('display_name') or ''}".strip()
    console.print(Panel(f"[bold]{title}[/bold]", title="Skill"))
    console.print(f"[bold]Description:[/bold] {skill.get('description') or ''}")
    console.print(
        f"[bold]Visibility:[/bold] {skill.get('visibility')}  "
        f"[bold]Status:[/bold] {skill.get('status')}  "
        f"[bold]Review:[/bold] {skill.get('review_status') or '-'}  "
        f"[bold]Enabled:[/bold] {skill.get('enabled')}"
    )
    if skill.get("has_draft"):
        console.print("[yellow]Has an unpublished draft[/yellow]")
    tools = skill.get("allowed_tools") or []
    console.print(f"[bold]Allowed tools:[/bold] {', '.join(tools) if tools else '(none)'}")
    refs = skill.get("reference_files") or {}
    if refs:
        console.print(f"[bold]Reference files ({len(refs)}):[/bold]")
        for path in sorted(refs.keys()):
            console.print(f"  - {path}")
    body = skill.get("body") or ""
    preview = body if len(body) <= 800 else body[:800] + "\n…"
    if preview:
        console.print(Panel(preview, title="Body preview", expand=False))
